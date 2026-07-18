#!/bin/bash
# tiny-market 보안/기능 테스트 (보고서용)
#
# 사전 준비:
#   flask --app app init-db
#   flask --app app create-admin admin   # 비밀번호: Admin1234
#   PORT=5001 python app.py              # 서버 실행 (별도 터미널)
#
# 실행:  bash tests/security_test.sh
#
# 특징: 매 실행마다 고유한 계정/상품명을 사용하므로 DB를 초기화하지 않아도
#       반복 실행이 가능하다. (새 사용자는 가입 시 기본 잔액 100,000원)

BASE="${BASE:-http://127.0.0.1:5001}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PW="${ADMIN_PW:-Admin1234}"
RUN=$$_$(date +%s)          # 이번 실행 고유 접미사
UA="ua_$RUN"; UB="ub_$RUN"; UC="uc_$RUN"
TITLE="테스트상품_$RUN"
DIR=$(mktemp -d)
trap 'rm -rf "$DIR"' EXIT
JA="$DIR/a"; JB="$DIR/b"; JC="$DIR/c"; JADM="$DIR/adm"

PASS=0; FAIL=0
ok()  { echo "  ✅ PASS  $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ FAIL  $1  (got: $2)"; FAIL=$((FAIL+1)); }

csrf() { curl -s -b "$1" -c "$1" "$2" | grep -o 'name="csrf_token" value="[^"]*"' | head -1 | sed 's/.*value="//;s/"//'; }
reg()  { local T; T=$(csrf "$1" "$BASE/auth/register"); curl -s -o /dev/null -w "%{http_code}" -b "$1" -c "$1" -X POST "$BASE/auth/register" -d "csrf_token=$T&username=$2&password=Testpass1&password2=Testpass1"; }
login(){ local T; T=$(csrf "$1" "$BASE/auth/login"); curl -s -o /dev/null -w "%{http_code}" -b "$1" -c "$1" -X POST "$BASE/auth/login" -d "csrf_token=$T&username=$2&password=$3"; }
bal()  { curl -s -b "$1" "$BASE/wallet/" | grep -o "잔액: [0-9,]*" | head -1; }

# 서버 접속 확인
if ! curl -s -o /dev/null "$BASE/"; then
  echo "서버에 접속할 수 없습니다: $BASE  (먼저 'PORT=5001 python app.py'로 서버를 실행하세요)"
  exit 1
fi

echo "== 기능 테스트 =="
R=$(reg "$JA" "$UA");  [ "$R" = 302 ] && ok "회원가입($UA)" || bad "회원가입" "$R"
reg "$JB" "$UB" >/dev/null; reg "$JC" "$UC" >/dev/null
R=$(login "$JA" "$UA" Testpass1); [ "$R" = 302 ] && ok "정상 로그인" || bad "정상 로그인" "$R"
login "$JB" "$UB" Testpass1 >/dev/null; login "$JC" "$UC" Testpass1 >/dev/null
R=$(login "$JADM" "$ADMIN_USER" "$ADMIN_PW"); [ "$R" = 302 ] || echo "  (주의) 관리자 로그인 실패($R): create-admin 을 먼저 실행했는지 확인"

# 상품 등록 → 생성된 상품 ID를 Location 헤더에서 추출
T=$(csrf "$JA" "$BASE/products/new")
LOC=$(curl -s -D - -o /dev/null -b "$JA" -X POST "$BASE/products/new" \
  --form-string "csrf_token=$T" --form-string "title=$TITLE" --form-string "price=1200000" \
  --form-string "description=정상 상품 설명입니다." | grep -i "^location:" | tr -d '\r' | awk '{print $2}')
PID=$(echo "$LOC" | grep -o '[0-9]*$')
[ -n "$PID" ] && ok "상품 등록 (id=$PID)" || bad "상품 등록" "$LOC"

Q=$(python3 -c "import urllib.parse;print(urllib.parse.quote('$TITLE'))" 2>/dev/null)
FOUND=$(curl -s "$BASE/?q=$Q" | grep -c "$TITLE")
[ "$FOUND" -ge 1 ] && ok "상품 검색(한글)" || bad "상품 검색" "$FOUND"

echo ""
echo "== 보안 테스트 =="

# 1. SQL Injection
R=$(login "$DIR/inj" "admin' OR '1'='1' --" anything123)
[ "$R" = 200 ] && ok "SQL Injection 로그인 우회 차단 (재렌더 200, 세션 없음)" || bad "SQLi" "$R"

# 2. XSS (상품 설명에 스크립트 주입 → 이스케이프 확인)
T=$(csrf "$JA" "$BASE/products/$PID/edit")
curl -s -o /dev/null -b "$JA" -X POST "$BASE/products/$PID/edit" \
  --form-string "csrf_token=$T" --form-string "title=$TITLE" --form-string "price=1200000" \
  --form-string "description=<script>alert('xss')</script>"
PAGE=$(curl -s -b "$JA" "$BASE/products/$PID")
ESC=$(echo "$PAGE" | grep -c "&lt;script&gt;"); RAW=$(echo "$PAGE" | grep -c "<script>alert")
[ "$ESC" -ge 1 ] && [ "$RAW" = 0 ] && ok "XSS 페이로드 이스케이프 (escaped=$ESC, raw=$RAW)" || bad "XSS" "esc=$ESC raw=$RAW"

# 3. CSRF
R=$(curl -s -o /dev/null -w "%{http_code}" -b "$JA" -X POST "$BASE/products/new" --form-string "title=x" --form-string "price=1000" --form-string "description=y")
[ "$R" = 400 ] && ok "CSRF 토큰 없는 요청 차단 (400)" || bad "CSRF" "$R"

# 4. IDOR ($UB가 $UA의 상품 수정 페이지 접근)
R=$(curl -s -o /dev/null -w "%{http_code}" -b "$JB" "$BASE/products/$PID/edit")
[ "$R" = 403 ] && ok "IDOR 타인 상품 수정 차단 (403)" || bad "IDOR" "$R"

# 5. 인가
A1=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/admin/")
A2=$(curl -s -o /dev/null -w "%{http_code}" -b "$JA" "$BASE/admin/")
A3=$(curl -s -o /dev/null -w "%{http_code}" -b "$JADM" "$BASE/admin/")
[ "$A1" = 302 ] && [ "$A2" = 403 ] && [ "$A3" = 200 ] && ok "관리자 인가 (미인증=302, 일반=403, 관리자=200)" || bad "인가" "$A1/$A2/$A3"

# 6. 입력 검증 (음수/초과/자기송금 → 거부, 잔액 불변). 새 사용자 UA 초기 잔액 100,000
B0=$(bal "$JA")
T=$(csrf "$JA" "$BASE/wallet/")
curl -s -o /dev/null -b "$JA" -X POST "$BASE/wallet/transfer" -d "csrf_token=$T&receiver=$UB&amount=-500&memo="
curl -s -o /dev/null -b "$JA" -X POST "$BASE/wallet/transfer" -d "csrf_token=$T&receiver=$UB&amount=999999999&memo="
curl -s -o /dev/null -b "$JA" -X POST "$BASE/wallet/transfer" -d "csrf_token=$T&receiver=$UA&amount=100&memo="
B1=$(bal "$JA")
[ "$B0" = "잔액: 100,000" ] && [ "$B1" = "$B0" ] && ok "잘못된 송금(음수/초과/자기송금) 거부 ($B1 유지)" || bad "송금 검증" "before=$B0 after=$B1"

# 7. 정상 송금 원자성 (UA -> UB 30,000). 두 사용자 모두 이번 실행에서 새로 생성됨
T=$(csrf "$JA" "$BASE/wallet/")
curl -s -o /dev/null -b "$JA" -X POST "$BASE/wallet/transfer" -d "csrf_token=$T&receiver=$UB&amount=30000&memo=test"
SA=$(bal "$JA"); SB=$(bal "$JB")
[ "$SA" = "잔액: 70,000" ] && [ "$SB" = "잔액: 130,000" ] && ok "정상 송금 원자적 반영 (보낸이 $SA / 받은이 $SB)" || bad "송금" "$SA / $SB"

# 8. 신고 3회 누적 → 자동 차단 (이번 실행에서 만든 상품 PID를 3명이 신고)
for J in "$JB" "$JC" "$JADM"; do
  T=$(csrf "$J" "$BASE/reports/new?target_type=product&target_id=$PID")
  curl -s -o /dev/null -b "$J" -X POST "$BASE/reports/new" \
    -d "csrf_token=$T&target_type=product&target_id=$PID" --data-urlencode "reason=불량 상품입니다. 신고 사유 열 자 이상 작성."
done
BLOCK=$(curl -s -o /dev/null -w "%{http_code}" -b "$JB" "$BASE/products/$PID")
# 목록에서 해당 상품 카드 링크(/products/PID)가 사라졌는지 확인 (검색창 입력 echo 오탐 방지)
LIST=$(curl -s "$BASE/" | grep -c "\"/products/$PID\"")
[ "$BLOCK" = 404 ] && [ "$LIST" = 0 ] && ok "신고 3회 누적 → 상품 자동 차단 (타인 접근 404, 목록 비노출)" || bad "자동 차단" "$BLOCK/$LIST"

# 9. 중복 신고 차단 (UB가 같은 상품 재신고)
T=$(csrf "$JB" "$BASE/reports/new?target_type=product&target_id=$PID")
DUP=$(curl -s -b "$JB" -X POST "$BASE/reports/new" -d "csrf_token=$T&target_type=product&target_id=$PID" --data-urlencode "reason=같은 대상 중복 신고 시도입니다." | grep -c "이미 신고")
[ "$DUP" -ge 1 ] && ok "동일 대상 중복 신고 차단" || bad "중복 신고" "$DUP"

# 10. 무차별 대입 잠금 (UC 5회 실패 후 정답도 잠금)
for i in 1 2 3 4 5; do login "$DIR/lock" "$UC" WrongPass9 >/dev/null; done
T=$(csrf "$DIR/lock" "$BASE/auth/login")
LOCK=$(curl -s -b "$DIR/lock" -X POST "$BASE/auth/login" -d "csrf_token=$T&username=$UC&password=Testpass1" | grep -c "잠겼습니다")
[ "$LOCK" -ge 1 ] && ok "로그인 5회 실패 시 계정 잠금 (무차별 대입 방어)" || bad "계정 잠금" "$LOCK"

# 11. 보안 헤더
HDR=$(curl -s -D - -o /dev/null "$BASE/")
echo "$HDR" | grep -qi "content-security-policy" && echo "$HDR" | grep -qi "x-frame-options: DENY" && ok "보안 헤더(CSP, X-Frame-Options 등) 적용" || bad "보안 헤더" "missing"

# 12. 경로 탈출
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/uploads/..%2f..%2fmarket.sqlite")
{ [ "$R" = 404 ] || [ "$R" = 400 ]; } && ok "업로드 경로 탈출(../) 차단 ($R)" || bad "경로 탈출" "$R"

echo ""
echo "== 결과: $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
