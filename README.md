# Tiny Second-hand Shopping Platform

시큐어 코딩 과제로 개발한 중고거래 플랫폼입니다.
Flask + Socket.IO + SQLite 기반이며, 개발 전 과정에서 보안 약점을 제거하는 것을 목표로 했습니다.

## 주요 기능

- 회원가입 / 로그인 / 마이페이지 (소개글·비밀번호 변경)
- 상품 등록 / 조회 / 검색 / 수정 / 삭제 (이미지 업로드 지원)
- 실시간 전체 채팅, 1:1 채팅 (Socket.IO)
- 사용자·상품 신고, 누적 신고 시 자동 차단/휴면 처리
- 포인트 송금 (가상 잔액, 트랜잭션 보장)
- 관리자 대시보드 (사용자/상품/신고 관리)

## 환경 설정

Ubuntu(WSL/VM) + miniconda 기준:

```bash
# 1. 저장소 클론
git clone <repository-url>
cd tiny-market

# 2. 가상환경 생성
conda create -n tiny-market python=3.11 -y
conda activate tiny-market

# 3. 의존성 설치
pip install -r requirements.txt
```

## 실행 방법

```bash
# 1. 데이터베이스 초기화
flask --app app init-db

# 2. 관리자 계정 생성 (비밀번호는 프롬프트로 입력)
flask --app app create-admin admin

# 3. 서버 실행
python app.py
```

브라우저에서 http://127.0.0.1:5000 접속.

외부 공개가 필요하면:

```bash
ngrok http 5000
```

> HTTPS(ngrok 등) 환경에서는 `COOKIE_SECURE=1` 환경변수를 설정하면 세션 쿠키에 Secure 플래그가 적용됩니다.

## 적용한 보안 조치 (요약)

| 영역 | 조치 |
|---|---|
| SQL Injection | 모든 쿼리 파라미터 바인딩(`?`), LIKE 와일드카드 이스케이프 |
| XSS | Jinja2 autoescape, 채팅 메시지 `textContent` 렌더링, CSP 헤더 |
| CSRF | 모든 POST 폼에 Flask-WTF CSRF 토큰 |
| 비밀번호 | bcrypt 해싱(salt 포함), 8~72자 + 영문/숫자 정책 |
| 세션 | HttpOnly/SameSite 쿠키, 로그인 시 세션 재발급(고정 방지), 1시간 만료 |
| 인증/인가 | login_required / admin_required, 소유자 검증(IDOR 방지), 채팅방 참여 권한 서버 검증 |
| 무차별 대입 | 로그인 5회 실패 시 5분 잠금, 계정 열거 방지(동일 오류 메시지 + 더미 해시) |
| 파일 업로드 | 확장자 화이트리스트, 서버 생성 무작위 파일명, 2MB 용량 제한 |
| 송금 | 정수·범위 검증, 잔액 확인·차감 단일 트랜잭션(BEGIN IMMEDIATE), 자기송금 금지 |
| 도배/남용 | 채팅·신고 Rate limiting, 동일 대상 중복 신고 금지 |
| 기타 | 오류 페이지에서 내부 정보 미노출, 보안 응답 헤더, 비밀키 파일 분리 관리 |
