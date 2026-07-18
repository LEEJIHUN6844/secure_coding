# 보안 체크리스트

슬라이드 31p 예시 체크리스트를 기반으로 작성. 테스트 후 확인 열에 결과 기입.

| # | 구역 | 항목 | 내용 | 구현 위치 | 확인 |
|---|---|---|---|---|---|
| 1 | 회원가입/프로필 | 서버측 입력 검증 | 아이디/비밀번호 화이트리스트·길이·형식 검증 | security.py `valid_username`, `valid_password` | ☐ |
| 2 | | CSRF 보호 | 모든 POST 폼에 CSRF 토큰 | Flask-WTF CSRFProtect, 각 템플릿 | ☐ |
| 3 | | 비밀번호 보안 | bcrypt(salt 자동) 해싱 저장 | auth.py, db.py | ☐ |
| 4 | | 세션 쿠키 설정 | HttpOnly, SameSite=Lax, (HTTPS 시 Secure) | config.py | ☐ |
| 5 | | 세션 만료/재발급 | 1시간 만료, 로그인 시 session.clear() 후 재발급 | config.py, auth.py login | ☐ |
| 6 | | 실패 로그인 방어 | 5회 실패 시 5분 잠금, 계정 열거 방지 | auth.py login | ☐ |
| 7 | | 오류 메시지 | 내부 정보(스택트레이스 등) 미노출 | __init__.py errorhandler | ☐ |
| 8 | 상품 등록/관리 | 폼 입력 검증 | 제목/설명/가격 서버측 검증, 가격 정수·범위 | products.py `_validate_form` | ☐ |
| 9 | | XSS 방어 | Jinja2 autoescape (템플릿 출력 시 이스케이프) | 전 템플릿 | ☐ |
| 10 | | 인증된 사용자만 등록 | login_required 적용 | products.py | ☐ |
| 11 | | 소유자 확인 (IDOR) | 수정/삭제 시 소유자 또는 관리자 검증 | products.py `_require_owner_or_admin` | ☐ |
| 12 | | 데이터 무결성 | DB CHECK 제약(가격>0, 상태 값 등) | schema.sql | ☐ |
| 13 | | 파일 업로드 | 확장자 화이트리스트, 무작위 파일명, 2MB 제한 | products.py `_save_image`, config.py | ☐ |
| 14 | 채팅/메시징 | 메시지 내용 검증 | 길이 제한(500자) 서버측 검증 | chat.py on_send | ☐ |
| 15 | | 사용자 인증 | 소켓 연결·이벤트마다 세션 인증 확인 | chat.py `_current_user`, on_connect | ☐ |
| 16 | | 방 참여 권한 검증 | dm 방은 당사자만 join/send 가능 | chat.py `_authorized_room` | ☐ |
| 17 | | Rate Limiting | 10초당 5회 제한(도배 방지) | chat.py message_limiter | ☐ |
| 18 | | 출력 안전성 | 클라이언트 textContent 렌더링(DOM XSS 방지) | static/js/chat.js | ☐ |
| 19 | 신고 | 폼 입력 검증 | target 검증, 사유 10~500자 | reports.py | ☐ |
| 20 | | 인증된 사용자만 | login_required | reports.py | ☐ |
| 21 | | 신고 남용 방지 | 중복 신고 UNIQUE 제약, 시간당 10건 제한 | schema.sql, reports.py | ☐ |
| 22 | | 자동 조치 | 3회 누적 시 상품 차단/유저 휴면(관리자 제외) | reports.py `_apply_auto_action` | ☐ |
| 23 | 송금 | 금액 검증 | 정수, 1~1억, 자기송금 금지 | wallet.py | ☐ |
| 24 | | 원자성 | BEGIN IMMEDIATE 트랜잭션으로 잔액 확인+차감 | wallet.py transfer | ☐ |
| 25 | | 무결성 | balance >= 0 CHECK 제약 (이중 방어) | schema.sql | ☐ |
| 26 | 관리자 | 권한 분리 | admin_required, role 기반 접근 제어 | admin.py, security.py | ☐ |
| 27 | 공통 | SQL Injection 방지 | 전 쿼리 파라미터 바인딩 | 전 모듈 | ☐ |
| 28 | | 보안 응답 헤더 | CSP, X-Frame-Options, nosniff 등 | __init__.py after_request | ☐ |
| 29 | | 비밀키 관리 | 하드코딩 없이 instance/secret.key(0600) | __init__.py | ☐ |

## 기능 체크리스트

| # | 요구사항 | 확인 |
|---|---|---|
| 1 | 회원가입/로그인/로그아웃 | ☐ |
| 2 | 마이페이지: 소개글·비밀번호 수정 | ☐ |
| 3 | 다른 사용자 프로필 조회 | ☐ |
| 4 | 상품 등록(사진 포함)/수정/삭제 | ☐ |
| 5 | 상품 목록(이름·가격) + 상세 페이지 | ☐ |
| 6 | 상품 검색 | ☐ |
| 7 | 실시간 전체 채팅 | ☐ |
| 8 | 1:1 채팅 | ☐ |
| 9 | 사용자/상품 신고 + 사유 작성 | ☐ |
| 10 | 신고 누적 시 상품 차단/유저 휴면 | ☐ |
| 11 | 포인트 송금 + 거래 내역 | ☐ |
| 12 | 관리자: 유저/상품/신고 관리 | ☐ |
