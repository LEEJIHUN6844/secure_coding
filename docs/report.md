# Tiny Second-hand Shopping Platform 개발 보고서

> **과목**: Secure Coding (WhiteHat School)
> **제출 파일명 예시**: `[WHS][secure-coding][XX반]이름(1234).pdf`
> **GitHub**: (여기에 public repository 링크 삽입)
> **작성일**: 2026-07-__

---

## 목차

1. 개요 및 목표
2. 요구사항 분석
3. 시스템 설계
4. 시스템 구현
5. 보안 약점 분석 및 조치 (핵심)
6. 체크리스트 작성 및 테스팅
7. 유지보수
8. 결론 및 AI 도구 활용
9. 부록

---

## 1. 개요 및 목표

### 1.1 프로젝트 개요

본 프로젝트는 사용자가 중고 물품을 사고팔 수 있는 **중고거래 플랫폼(Tiny Second-hand
Shopping Platform)**을 소프트웨어 개발 생명주기(SDLC) 전 과정에 따라 개발한 것이다.
단순히 기능을 구현하는 데 그치지 않고, **요구사항 분석 → 설계 → 구현 → 테스팅 → 유지보수**
의 각 단계에서 보안을 함께 고려하는 "시큐어 소프트웨어 공학"을 실천하는 것을 목표로 한다.

### 1.2 목표

- 중고거래에 필요한 핵심 기능(회원, 상품, 채팅, 신고, 송금, 관리자)을 모두 구현한다.
- 개발 전 과정에서 **선제적으로 보안 약점을 제거**한다.
- OWASP Top 10, KISA 시큐어 코딩 가이드에서 다루는 주요 취약점(SQL Injection, XSS,
  CSRF, 인증/인가 결함 등)이 발생하지 않도록 한다.
- 발견한 보안 약점과 그 조치 과정을 문서화한다.

### 1.3 개발 환경

| 구분 | 내용 |
|---|---|
| 언어 | Python 3.11 |
| 웹 프레임워크 | Flask 3.0 |
| 실시간 통신 | Flask-SocketIO 5.3 |
| 보안 | Flask-WTF(CSRF), bcrypt(비밀번호 해싱) |
| 데이터베이스 | SQLite 3 |
| 템플릿 | Jinja2 (자동 이스케이프) |
| 실행 환경 | Ubuntu (WSL/VM), miniconda |

> Python/Flask를 선택한 이유: 강의 실습 리포지토리가 miniconda 기반 Python 환경이며,
> 파라미터 바인딩·자동 이스케이프·CSRF 보호 등 시큐어 코딩에 필요한 기능이 표준적으로
> 제공되어 보안 통제를 일관되게 적용하기 쉽다.

---

## 2. 요구사항 분석

### 2.1 기능 요구사항

강의에서 제시한 중고거래 플랫폼의 필수 기능을 아래와 같이 도출하였다.

| ID | 기능 | 세부 요구사항 |
|---|---|---|
| F1 | 회원 관리 | 회원가입, 로그인/로그아웃, 마이페이지(소개글·비밀번호 수정), 사용자 프로필 조회, 아이디 중복 불가 |
| F2 | 상품 관리 | 상품 등록(상품명·가격·사진), 내 상품 관리(수정·삭제), 전체 상품 조회, 상품 상세 페이지 |
| F3 | 사용자 소통 | 실시간 전체 채팅, 1:1 채팅 |
| F4 | 악성 유저/상품 차단 | 사용자·상품 신고(사유 작성), 일정 횟수 이상 신고 시 상품 차단·유저 휴면 |
| F5 | 송금 | 사용자 간 포인트 송금 |
| F6 | 검색 | 상품명 검색 |
| F7 | 관리자 | 사용자·상품·신고 전체 관리 |

이 중 F1~F4는 강의에서 세부 명세를 제공하였고, **F5~F7은 직접 요구사항을 분석**하여 설계하였다.

### 2.2 직접 분석한 요구사항 (F5~F7)

**F5. 송금**
- 실제 결제(카드/계좌)는 금융 규제·보안 위험이 크므로, **가상 포인트(balance)** 방식으로 구현한다.
- 회원가입 시 기본 포인트를 지급하고, 사용자 간 이체를 지원한다.
- 보안 관점: 금액은 양의 정수여야 하고, 잔액을 초과할 수 없으며, 잔액 확인과 차감이
  **원자적(atomic)**으로 이뤄져야 한다(이중 송금·경쟁 조건 방지). 자기 자신에게 송금 불가.

**F6. 검색**
- 상품명(title) 부분 일치 검색을 지원한다.
- 보안 관점: 검색어 길이를 제한하고, SQL LIKE의 와일드카드(`%`, `_`)를 이스케이프하여
  의도치 않은 패턴 매칭·부하를 방지한다.

**F7. 관리자**
- 관리자는 전체 사용자/상품/신고를 조회하고, 사용자 휴면·상품 차단·삭제를 수행한다.
- 보안 관점: 일반 사용자와 **역할(role)로 분리**하고, 모든 관리자 기능은 `admin` 권한을
  서버에서 검증한다. 관리자 계정은 신고 누적으로 휴면되지 않는다.

### 2.3 비기능 요구사항

| 구분 | 내용 |
|---|---|
| 보안 | 입력 검증, 인증·인가, 데이터 보호. **최우선 요구사항** |
| 사용성 | 반응형 UI, 직관적인 상품 목록·검색·채팅 |
| 무결성 | DB 제약(CHECK, UNIQUE, FK)으로 데이터 정합성 보장 |
| 이식성 | 표준 라이브러리 위주로 구성, 소수 의존성 |

### 2.4 위협 모델링

각 기능에서 예상되는 공격과 대응 방향을 사전에 정리하였다.

| 기능 | 예상 위협 | 대응 방향 |
|---|---|---|
| 로그인 | SQL Injection, 무차별 대입, 계정 열거 | 파라미터 바인딩, 실패 잠금, 동일 오류 메시지 |
| 회원가입/프로필 | 약한 비밀번호, 평문 저장 | 비밀번호 정책, bcrypt 해싱 |
| 상품 등록 | XSS, 악성 파일 업로드 | 자동 이스케이프, 확장자 화이트리스트 |
| 상품 수정/삭제 | IDOR(타인 자원 조작) | 소유자/관리자 검증 |
| 채팅 | XSS, 메시지 도배, 미인증 접근 | textContent 렌더링, Rate limit, 소켓 인증 |
| 송금 | 음수/초과 금액, 경쟁 조건 | 입력 검증, 단일 트랜잭션 |
| 신고 | 신고 남용, 존재하지 않는 대상 | 중복 제한, Rate limit, 대상 검증 |
| 전역 | CSRF, 정보 노출 | CSRF 토큰, 오류 페이지·보안 헤더 |

---

## 3. 시스템 설계

### 3.1 아키텍처

```
[브라우저]
   │  HTTP / WebSocket
   ▼
[Flask 애플리케이션]
   ├─ Blueprint: auth      (회원/인증)
   ├─ Blueprint: products  (상품 CRUD·검색)
   ├─ Blueprint: chat      (전체/1:1 채팅, Socket.IO)
   ├─ Blueprint: reports   (신고·자동 차단)
   ├─ Blueprint: wallet    (포인트 송금)
   ├─ Blueprint: admin     (관리자)
   ├─ security.py          (입력 검증·권한·Rate limit)
   └─ 전역: CSRF, 보안 헤더, 오류 핸들러
   ▼
[SQLite DB]  user / product / report / dm_thread / message / transfer
```

애플리케이션 팩토리(`create_app`) 패턴으로 구성하고, 기능별 Blueprint로 분리하여
책임을 명확히 하였다. 보안 통제(입력 검증, 권한 데코레이터, Rate limiter)는
`security.py`에 모아 재사용한다.

### 3.2 데이터베이스 설계 (ERD 요약)

| 테이블 | 주요 컬럼 | 비고 |
|---|---|---|
| `user` | id, username(UNIQUE), password_hash, bio, role, status, balance, failed_logins, locked_until | role∈{user,admin}, status∈{active,dormant} |
| `product` | id, title, description, price, image, seller_id(FK), status | status∈{active,blocked}, price>0 |
| `report` | id, reporter_id(FK), target_type, target_id, reason | (reporter,target) UNIQUE로 중복 신고 방지 |
| `dm_thread` | id, user_lo, user_hi | (lo,hi) UNIQUE, 1:1 채팅방 |
| `message` | id, room, sender_id(FK), content | 전체/DM 메시지 |
| `transfer` | id, sender_id(FK), receiver_id(FK), amount, memo | amount>0 |

데이터 무결성은 애플리케이션 검증뿐 아니라 **DB 제약(CHECK, UNIQUE, FOREIGN KEY)**으로
이중 방어한다. 예: `balance >= 0`, `price > 0`, `role IN ('user','admin')`.

### 3.3 페이지 설계

| 페이지 | 경로 | 접근 권한 |
|---|---|---|
| 상품 목록 + 전체 채팅 | `/` | 공개(채팅은 로그인) |
| 회원가입 / 로그인 | `/auth/register`, `/auth/login` | 공개 |
| 마이페이지 | `/auth/profile` | 로그인 |
| 사용자 프로필 | `/auth/users/<id>` | 로그인 |
| 상품 등록/상세/수정 | `/products/new`, `/products/<id>`, `/products/<id>/edit` | 등록·수정은 로그인/소유자 |
| 1:1 채팅 | `/chat/dm`, `/chat/dm/<id>` | 로그인/당사자 |
| 신고 | `/reports/new` | 로그인 |
| 지갑 | `/wallet/` | 로그인 |
| 관리자 대시보드 | `/admin/` | 관리자 |

---

## 4. 시스템 구현

### 4.1 프로젝트 구조

```
tiny-market/
├── app.py                  # 실행 진입점
├── config.py               # 세션·쿠키·업로드 보안 설정
├── requirements.txt
├── market/
│   ├── __init__.py         # 앱 팩토리, CSRF, 보안 헤더, 오류 핸들러
│   ├── db.py               # DB 연결, init-db / create-admin CLI
│   ├── schema.sql          # 테이블 정의(제약 포함)
│   ├── security.py         # 입력 검증, 권한 데코레이터, Rate limiter
│   ├── auth.py             # 회원/인증
│   ├── products.py         # 상품 CRUD·검색·업로드
│   ├── chat.py             # 채팅(HTTP + Socket.IO)
│   ├── reports.py          # 신고·자동 차단
│   ├── wallet.py           # 송금
│   ├── admin.py            # 관리자
│   ├── templates/          # Jinja2 템플릿
│   └── static/             # CSS, 채팅 JS
├── tests/security_test.sh  # 보안·기능 테스트
└── docs/                   # 보고서, 체크리스트
```

### 4.2 주요 기능 구현 요약

- **회원/인증**: bcrypt 해싱, 로그인 실패 잠금, 세션 재발급, 비밀번호 변경 시 현재 비밀번호 재확인.
- **상품**: 서버측 입력 검증, 이미지 확장자 화이트리스트 + 무작위 파일명, 소유자 검증.
- **채팅**: Socket.IO 이벤트마다 세션 인증·방 권한 검증, 서버 저장 후 브로드캐스트, 클라이언트는 `textContent`로 렌더링.
- **신고**: 대상 실존 검증, 중복 신고 차단, 3회 누적 시 자동 차단/휴면.
- **송금**: `BEGIN IMMEDIATE` 트랜잭션으로 잔액 확인·차감·기록을 원자적으로 처리.
- **관리자**: `admin_required` 데코레이터로 역할 기반 접근 제어.

---

## 5. 보안 약점 분석 및 조치 (핵심)

개발 과정에서 확인한 보안 약점과, 이를 어떻게 안전한 코드로 변경하였는지를
**공격 시나리오 → 취약 코드(Before) → 조치 코드(After)** 형식으로 정리한다.
(Before는 "이렇게 짰다면 취약했을" 대표적 안티패턴이고, After는 실제 적용된 코드다.)

### 5.1 SQL Injection

- **시나리오**: 로그인 아이디에 `admin' OR '1'='1' --` 를 입력해 인증을 우회.
- **Before (취약)**
  ```python
  query = f"SELECT * FROM user WHERE username = '{username}'"
  user = db.execute(query).fetchone()
  ```
- **After (조치)** — `market/auth.py`
  ```python
  user = db.execute(
      "SELECT * FROM user WHERE username = ?", (username,)
  ).fetchone()
  ```
- **설명**: 모든 쿼리에서 문자열 포매팅을 배제하고 **파라미터 바인딩(`?`)**만 사용한다.
  프로젝트 전체 쿼리가 동일 원칙을 따른다.
- **검증**: 테스트 #1 통과(우회 불가).

### 5.2 저장형 XSS (Cross-Site Scripting)

- **시나리오**: 상품 설명·채팅 메시지에 `<script>alert('xss')</script>` 저장 후 열람자 브라우저에서 실행.
- **Before (취약)**
  ```python
  # 템플릿에서 이스케이프를 끄거나(safe), 문자열을 직접 innerHTML로 삽입
  element.innerHTML = data.content;   // chat.js
  ```
- **After (조치)** — `market/static/js/chat.js`
  ```javascript
  var b = document.createElement("b");
  b.textContent = username;
  div.appendChild(b);
  div.appendChild(document.createTextNode(" " + content)); // 텍스트로만 삽입
  ```
- **설명**: 서버 렌더링은 Jinja2 **자동 이스케이프**에 의존하고, 클라이언트 렌더링은
  `textContent`/`createTextNode`만 사용해 DOM 기반 XSS를 차단한다. 추가로 CSP 헤더로
  인라인 스크립트 실행을 제한한다.
- **검증**: 테스트 #2 통과(`&lt;script&gt;`로 이스케이프, 원본 스크립트 0건).

### 5.3 CSRF (Cross-Site Request Forgery)

- **시나리오**: 공격자가 만든 페이지에서 피해자의 세션으로 상품 삭제·송금 등 상태 변경 요청을 강제.
- **Before (취약)**: 아무 토큰 없이 폼 POST를 그대로 수락.
- **After (조치)** — `market/__init__.py`, 각 템플릿
  ```python
  from flask_wtf import CSRFProtect
  csrf = CSRFProtect()
  csrf.init_app(app)
  ```
  ```html
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  ```
- **설명**: 모든 상태 변경 요청(POST)에 CSRF 토큰을 요구한다. 토큰이 없거나 불일치하면 400.
- **검증**: 테스트 #3 통과(토큰 없는 POST 400).

### 5.4 IDOR (Insecure Direct Object Reference)

- **시나리오**: 사용자가 URL의 상품 ID만 바꿔 타인의 상품을 수정·삭제.
- **Before (취약)**
  ```python
  # 로그인만 확인하고 소유자는 확인하지 않음
  db.execute("UPDATE product SET ... WHERE id = ?", (product_id,))
  ```
- **After (조치)** — `market/products.py`
  ```python
  def _require_owner_or_admin(product):
      if g.user is None or (
          product["seller_id"] != g.user["id"] and g.user["role"] != "admin"
      ):
          abort(403)
  ```
- **설명**: 수정·삭제 시 **자원 소유자 또는 관리자**인지 서버에서 검증한다. 채팅방도
  당사자만 접근 가능하도록 동일하게 검증한다(`chat.py`의 `_authorized_room`).
- **검증**: 테스트 #4 통과(타인 접근 403).

### 5.5 인증·인가 결함

- **시나리오**: 미인증 사용자나 일반 사용자가 관리자 기능(사용자 휴면, 상품 삭제)에 접근.
- **After (조치)** — `market/security.py`
  ```python
  def admin_required(view):
      @wraps(view)
      def wrapped(**kwargs):
          if g.user is None:
              return redirect(url_for("auth.login"))
          if g.user["role"] != "admin":
              abort(403)
          return view(**kwargs)
      return wrapped
  ```
- **설명**: 역할 기반 접근 제어(RBAC). 모든 관리자 라우트에 `@admin_required`를 적용한다.
- **검증**: 테스트 #5 통과(미인증=302, 일반=403, 관리자=200).

### 5.6 비밀번호 평문 저장 / 약한 비밀번호

- **시나리오**: DB 유출 시 평문 비밀번호가 그대로 노출.
- **Before (취약)**
  ```python
  db.execute("INSERT INTO user (username, password) VALUES (?, ?)",
             (username, password))   # 평문 저장
  ```
- **After (조치)** — `market/auth.py`
  ```python
  pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
  db.execute("INSERT INTO user (username, password_hash) VALUES (?, ?)",
             (username, pw_hash))
  ```
- **설명**: **bcrypt**(salt 자동 포함, 적응적 비용)로 해싱 저장한다. 비밀번호 정책은
  8~72자 + 영문·숫자 포함으로 강제한다(`valid_password`).

### 5.7 무차별 대입(Brute-force) 및 계정 열거

- **시나리오**: 로그인 폼에 자동화 도구로 비밀번호를 반복 시도. 오류 메시지 차이로 아이디 존재 여부 파악.
- **After (조치)** — `market/auth.py`
  ```python
  # 5회 실패 시 5분 잠금
  locked_until = now + LOCKOUT_SECONDS if fails >= LOCKOUT_THRESHOLD else 0
  # 아이디 존재 여부와 무관하게 동일 메시지
  generic_error = "아이디 또는 비밀번호가 올바르지 않습니다."
  # 존재하지 않는 계정도 더미 해시로 검증 → 타이밍 차이 완화
  bcrypt.checkpw(password.encode(), DUMMY_HASH)
  ```
- **설명**: 실패 횟수 기반 잠금, 동일 오류 메시지, 더미 해시 검증으로 무차별 대입과
  계정 열거를 동시에 완화한다.
- **검증**: 테스트 #10 통과(5회 실패 후 정답도 잠금).

### 5.8 안전하지 않은 파일 업로드

- **시나리오**: `shell.php`, `../../etc/passwd` 등 악성/경로 조작 파일 업로드.
- **After (조치)** — `market/products.py`
  ```python
  ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
  if ext not in ALLOWED_EXT:
      return None, "이미지는 png/jpg/jpeg/gif/webp만 업로드할 수 있습니다."
  name = f"{uuid.uuid4().hex}.{ext}"   # 서버가 파일명 생성
  ```
- **설명**: 확장자 화이트리스트, **사용자 파일명을 신뢰하지 않고 서버가 무작위 이름 생성**,
  업로드 용량 2MB 제한(`MAX_CONTENT_LENGTH`). 다운로드는 `send_from_directory`로 경로 탈출을 차단.
- **검증**: 테스트 #12 통과(경로 탈출 404).

### 5.9 송금의 경쟁 조건(Race Condition)

- **시나리오**: 동시 요청으로 잔액 검사와 차감 사이 시점을 노려 잔액을 초과 인출(이중 송금).
- **Before (취약)**
  ```python
  if sender.balance >= amount:          # 검사
      update(sender, -amount)            # ...그 사이 다른 요청이 끼어들 수 있음
      update(receiver, +amount)
  ```
- **After (조치)** — `market/wallet.py`
  ```python
  db.execute("BEGIN IMMEDIATE")          # 쓰기 잠금 획득
  sender = db.execute("SELECT balance ...").fetchone()
  if sender["balance"] < amount:
      db.rollback()
  else:
      db.execute("UPDATE user SET balance = balance - ? ...")
      db.execute("UPDATE user SET balance = balance + ? ...")
      db.execute("INSERT INTO transfer ...")
      db.commit()
  ```
- **설명**: 잔액 확인·차감·기록을 **하나의 트랜잭션**으로 묶고, `BEGIN IMMEDIATE`로
  쓰기 잠금을 선점한다. DB에도 `balance >= 0` CHECK 제약을 두어 이중 방어한다.
- **검증**: 테스트 #6·#7 통과(잘못된 송금 거부, 정상 송금 원자 반영).

### 5.10 신고 남용 및 입력 검증

- **시나리오**: 한 사용자가 특정 대상을 반복 신고해 부당하게 차단시킴. 존재하지 않는 대상 신고.
- **After (조치)** — `market/reports.py`, `schema.sql`
  ```python
  # 대상 실존 검증, 사유 10~500자, 시간당 10건 제한
  report_limiter = RateLimiter(limit=10, window=3600)
  # DB: 동일 (신고자, 대상) 조합 UNIQUE → 중복 신고 불가
  UNIQUE (reporter_id, target_type, target_id)
  ```
- **설명**: 중복 신고는 UNIQUE 제약으로, 대량 신고는 Rate limit으로 막는다. 자동 차단은
  **서로 다른 신고자 3명** 이상일 때만 발동한다(관리자 계정은 휴면 제외).
- **검증**: 테스트 #8·#9 통과.

### 5.11 정보 노출 및 전역 보안 설정

- **시나리오**: 서버 오류 시 스택트레이스·DB 오류가 사용자에게 노출. 클릭재킹, MIME 스니핑.
- **After (조치)** — `market/__init__.py`, `config.py`
  ```python
  # 오류는 사용자에게 일반 메시지만, 세부 정보 미노출
  @app.errorhandler(500)
  def server_error(e): return render_template("errors/error.html", ...), 500
  # 보안 응답 헤더
  resp.headers["Content-Security-Policy"] = "default-src 'self'; ..."
  resp.headers["X-Frame-Options"] = "DENY"
  resp.headers["X-Content-Type-Options"] = "nosniff"
  # 세션 쿠키
  SESSION_COOKIE_HTTPONLY = True; SESSION_COOKIE_SAMESITE = "Lax"
  ```
- **설명**: 사용자 정의 오류 페이지, CSP·X-Frame-Options·nosniff 헤더, HttpOnly·SameSite
  세션 쿠키(HTTPS 배포 시 Secure). 비밀키는 코드에 하드코딩하지 않고 `instance/secret.key`
  파일(권한 0600)로 관리한다.
- **검증**: 테스트 #11 통과(보안 헤더 적용).

### 5.12 보안 약점 조치 요약표

| # | 취약점 | 조치 | 검증 |
|---|---|---|---|
| 1 | SQL Injection | 파라미터 바인딩 | 테스트 #1 |
| 2 | XSS | 자동 이스케이프 + textContent + CSP | 테스트 #2 |
| 3 | CSRF | Flask-WTF 토큰 | 테스트 #3 |
| 4 | IDOR | 소유자/당사자 검증 | 테스트 #4 |
| 5 | 인증·인가 | RBAC 데코레이터 | 테스트 #5 |
| 6 | 비밀번호 | bcrypt 해싱 + 정책 | — |
| 7 | 무차별 대입/열거 | 실패 잠금 + 동일 메시지 + 더미 해시 | 테스트 #10 |
| 8 | 파일 업로드 | 화이트리스트 + 무작위명 + 용량 제한 | 테스트 #12 |
| 9 | 경쟁 조건 | 단일 트랜잭션 + CHECK | 테스트 #6·#7 |
| 10 | 신고 남용 | UNIQUE + Rate limit | 테스트 #8·#9 |
| 11 | 정보 노출 | 오류 페이지 + 보안 헤더 + 쿠키 | 테스트 #11 |

---

## 6. 체크리스트 작성 및 테스팅

### 6.1 체크리스트

강의에서 제시한 체크리스트 예시를 바탕으로, 구현된 각 부분이 기능·보안 요구사항을
만족하는지 점검하는 체크리스트를 작성하였다. 각 항목은 코드 검토와 테스트를 통해
구현 여부를 확인하였다.

**보안 체크리스트**

| # | 구역 | 항목 | 내용 | 구현 위치 | 확인 |
|---|---|---|---|---|---|
| 1 | 회원가입/프로필 | 서버측 입력 검증 | 아이디/비밀번호 화이트리스트·길이·형식 검증 | `security.py` valid_username, valid_password | ✅ |
| 2 | | CSRF 보호 | 모든 POST 폼에 CSRF 토큰 | Flask-WTF CSRFProtect, 각 템플릿 | ✅ |
| 3 | | 비밀번호 보안 | bcrypt(salt 자동) 해싱 저장 | `auth.py`, `db.py` | ✅ |
| 4 | | 세션 쿠키 설정 | HttpOnly, SameSite=Lax, (HTTPS 시 Secure) | `config.py` | ✅ |
| 5 | | 세션 만료/재발급 | 1시간 만료, 로그인 시 세션 재발급 | `config.py`, `auth.py` | ✅ |
| 6 | | 실패 로그인 방어 | 5회 실패 시 5분 잠금, 계정 열거 방지 | `auth.py` login | ✅ |
| 7 | | 오류 메시지 | 내부 정보(스택트레이스 등) 미노출 | `__init__.py` errorhandler | ✅ |
| 8 | 상품 등록/관리 | 폼 입력 검증 | 제목/설명/가격 서버측 검증, 가격 정수·범위 | `products.py` _validate_form | ✅ |
| 9 | | XSS 방어 | Jinja2 autoescape (출력 시 이스케이프) | 전 템플릿 | ✅ |
| 10 | | 인증된 사용자만 등록 | login_required 적용 | `products.py` | ✅ |
| 11 | | 소유자 확인 (IDOR) | 수정/삭제 시 소유자·관리자 검증 | `products.py` _require_owner_or_admin | ✅ |
| 12 | | 데이터 무결성 | DB CHECK 제약(가격>0, 상태 값 등) | `schema.sql` | ✅ |
| 13 | | 파일 업로드 | 확장자 화이트리스트, 무작위 파일명, 2MB 제한 | `products.py` _save_image, `config.py` | ✅ |
| 14 | 채팅/메시징 | 메시지 내용 검증 | 길이 제한(500자) 서버측 검증 | `chat.py` on_send | ✅ |
| 15 | | 사용자 인증 | 소켓 연결·이벤트마다 세션 인증 확인 | `chat.py` _current_user, on_connect | ✅ |
| 16 | | 방 참여 권한 검증 | DM 방은 당사자만 join/send 가능 | `chat.py` _authorized_room | ✅ |
| 17 | | Rate Limiting | 10초당 5회 제한(도배 방지) | `chat.py` message_limiter | ✅ |
| 18 | | 출력 안전성 | 클라이언트 textContent 렌더링(DOM XSS 방지) | `static/js/chat.js` | ✅ |
| 19 | 신고 | 폼 입력 검증 | 대상 검증, 사유 10~500자 | `reports.py` | ✅ |
| 20 | | 인증된 사용자만 | login_required | `reports.py` | ✅ |
| 21 | | 신고 남용 방지 | 중복 신고 UNIQUE 제약, 시간당 10건 제한 | `schema.sql`, `reports.py` | ✅ |
| 22 | | 자동 조치 | 3회 누적 시 상품 차단/유저 휴면(관리자 제외) | `reports.py` _apply_auto_action | ✅ |
| 23 | 송금 | 금액 검증 | 정수, 1~1억, 자기송금 금지 | `wallet.py` | ✅ |
| 24 | | 원자성 | BEGIN IMMEDIATE 트랜잭션으로 잔액 확인+차감 | `wallet.py` transfer | ✅ |
| 25 | | 무결성 | balance >= 0 CHECK 제약 (이중 방어) | `schema.sql` | ✅ |
| 26 | 관리자 | 권한 분리 | admin_required, role 기반 접근 제어 | `admin.py`, `security.py` | ✅ |
| 27 | 공통 | SQL Injection 방지 | 전 쿼리 파라미터 바인딩 | 전 모듈 | ✅ |
| 28 | | 보안 응답 헤더 | CSP, X-Frame-Options, nosniff 등 | `__init__.py` after_request | ✅ |
| 29 | | 비밀키 관리 | 하드코딩 없이 instance/secret.key(0600) | `__init__.py` | ✅ |

**기능 체크리스트**

| # | 요구사항 | 확인 |
|---|---|---|
| 1 | 회원가입 / 로그인 / 로그아웃 | ✅ |
| 2 | 마이페이지: 소개글·비밀번호 수정 | ✅ |
| 3 | 다른 사용자 프로필 조회 | ✅ |
| 4 | 상품 등록(사진 포함) / 수정 / 삭제 | ✅ |
| 5 | 상품 목록(이름·가격) + 상세 페이지 | ✅ |
| 6 | 상품 검색 | ✅ |
| 7 | 실시간 전체 채팅 | ✅ |
| 8 | 1:1 채팅 | ✅ |
| 9 | 사용자/상품 신고 + 사유 작성 | ✅ |
| 10 | 신고 누적 시 상품 차단 / 유저 휴면 | ✅ |
| 11 | 포인트 송금 + 거래 내역 | ✅ |
| 12 | 관리자: 유저/상품/신고 관리 | ✅ |

### 6.2 테스트 방법

기능·보안 테스트를 자동화 스크립트(`tests/security_test.sh`)로 작성하고,
실제 공격 시나리오를 재현하여 방어 여부를 확인하였다. 스크립트는 curl로 HTTP 요청을
보내 SQL Injection·XSS·CSRF·IDOR 등 각 공격을 흉내내고, 응답 코드와 페이지 내용으로
방어 성공 여부를 자동 판정한다.

> **[스크린샷]** `bash tests/security_test.sh` 실행 결과 화면 (16 passed, 0 failed).

### 6.3 테스트 결과

`tests/security_test.sh`를 실행한 결과 **16개 항목 전부 통과(16 passed, 0 failed)**하였다.

**요약**

| 분류 | 항목 수 | 통과 |
|---|---|---|
| 기능 테스트 | 4 | 4 ✅ |
| 보안 테스트 | 12 | 12 ✅ |
| **합계** | **16** | **16 ✅** |

**기능 테스트 상세**

| # | 항목 | 방법 | 기대 동작 | 결과 |
|---|---|---|---|---|
| 1 | 회원가입 | 유효한 아이디/비밀번호로 가입 | 302 리다이렉트, 계정 생성 | ✅ |
| 2 | 정상 로그인 | 올바른 자격증명 입력 | 302, 세션 발급 | ✅ |
| 3 | 상품 등록 | 로그인 후 상품 등록 | 302, 상세 페이지 이동 | ✅ |
| 4 | 상품 검색(한글) | `?q=아이폰` 검색 | 결과에 상품 노출 | ✅ |

**보안 테스트 상세**

| # | 취약점 유형 | 공격 시나리오 | 기대 동작 | 결과 |
|---|---|---|---|---|
| 1 | SQL Injection | 아이디에 `admin' OR '1'='1' --` 입력해 로그인 우회 시도 | 우회 불가, 로그인 실패 | ✅ |
| 2 | XSS (저장형) | 상품 설명에 `<script>alert('xss')</script>` 저장 | 출력 시 `&lt;script&gt;`로 이스케이프, 스크립트 미실행 | ✅ |
| 3 | CSRF | CSRF 토큰 없이 상품 등록 POST | 400 차단 | ✅ |
| 4 | IDOR | 타인이 남의 상품 수정 페이지 접근 | 403 차단 | ✅ |
| 5 | 인가 우회 | 미인증/일반 유저가 관리자 페이지 접근 | 미인증=302, 일반=403, 관리자=200 | ✅ |
| 6 | 입력 검증 | 음수·잔액초과·자기송금 시도 | 모두 거부, 잔액 유지 | ✅ |
| 7 | 경쟁 조건/원자성 | 정상 송금 | 보낸이·받은이 잔액 원자적 반영 | ✅ |
| 8 | 신고 자동 조치 | 상품을 서로 다른 3명이 신고 | 자동 차단, 목록·타인 접근 불가 | ✅ |
| 9 | 신고 남용 | 동일 대상 중복 신고 | UNIQUE 제약으로 차단 | ✅ |
| 10 | 무차별 대입 | 로그인 5회 실패 후 정답 입력 | 계정 5분 잠금 | ✅ |
| 11 | 헤더 보안 | 응답 헤더 확인 | CSP·X-Frame-Options 등 적용 | ✅ |
| 12 | 경로 탈출 | `/uploads/../../market.sqlite` 요청 | 차단(404) | ✅ |

> **[스크린샷 삽입]** 테스트 스크립트(`tests/security_test.sh`) 실행 결과 화면 —
> "16 passed, 0 failed" 출력. 아래는 실제 실행 결과이다.

```
== 기능 테스트 ==
  ✅ PASS  회원가입(buyer_a)
  ✅ PASS  정상 로그인
  ✅ PASS  상품 등록
  ✅ PASS  상품 검색(한글)

== 보안 테스트 ==
  ✅ PASS  SQL Injection 로그인 우회 차단 (재렌더 200, 세션 없음)
  ✅ PASS  XSS 페이로드 이스케이프 (escaped=1, raw=0)
  ✅ PASS  CSRF 토큰 없는 요청 차단 (400)
  ✅ PASS  IDOR 타인 상품 수정 차단 (403)
  ✅ PASS  관리자 인가 (미인증=302, 일반=403, 관리자=200)
  ✅ PASS  잘못된 송금(음수/초과/자기송금) 거부 (잔액: 100,000 유지)
  ✅ PASS  정상 송금 원자적 반영 (보낸이 70,000 / 받은이 130,000)
  ✅ PASS  신고 3회 누적 → 상품 자동 차단 (타인 접근 404, 목록 비노출)
  ✅ PASS  동일 대상 중복 신고 차단
  ✅ PASS  로그인 5회 실패 시 계정 잠금 (무차별 대입 방어)
  ✅ PASS  보안 헤더(CSP, X-Frame-Options 등) 적용
  ✅ PASS  업로드 경로 탈출(../) 차단 (404)

== 결과: 16 passed, 0 failed ==
```

### 6.4 기능 테스트 (수동)

자동화 테스트와 별개로, 실제 브라우저에서 사용자 흐름을 따라가며 각 기능이 정상
동작하는지 수동으로 확인하였다. 각 흐름의 실행 화면을 스크린샷으로 첨부한다.

| # | 흐름 | 관련 페이지 | 확인 내용 | 스크린샷 |
|---|---|---|---|---|
| 1 | 회원가입 → 로그인 | `/auth/register`, `/auth/login` | 계정 생성, 로그인 시 세션 발급 및 네비게이션 변화 | (첨부) |
| 2 | 마이페이지 수정 | `/auth/profile` | 소개글·비밀번호 수정, 내 상품 목록 확인 | (첨부) |
| 3 | 상품 등록 → 상세 조회 | `/products/new`, `/products/<id>` | 사진 포함 등록 후 목록·상세 페이지 정상 표시 | (첨부) |
| 4 | 상품 검색 | `/` (검색창) | 상품명 키워드로 목록 필터링 | (첨부) |
| 5 | 전체 채팅 | `/` (채팅 패널) | 실시간 전체 메시지 송수신 | (첨부) |
| 6 | 1:1 채팅 | `/chat/dm/<id>` | 판매자와 1:1 대화, 당사자만 접근 | (첨부) |
| 7 | 포인트 송금 | `/wallet/` | 송금 후 송신자·수신자 잔액 반영, 거래 내역 표시 | (첨부) |
| 8 | 신고 → 자동 차단 | `/reports/new` | 서로 다른 3명이 신고 시 상품 자동 차단 | (첨부) |
| 9 | 관리자 대시보드 | `/admin/` | 사용자 휴면, 상품 차단/삭제, 신고 내역 조회 | (첨부) |

> 각 흐름별 스크린샷을 아래에 삽입한다.
>
> **[스크린샷 1] 회원가입 → 로그인**
>
> **[스크린샷 2] 마이페이지 (소개글·비밀번호 수정)**
>
> **[스크린샷 3] 상품 등록 → 상세 조회**
>
> **[스크린샷 4] 상품 검색**
>
> **[스크린샷 5] 전체 채팅**
>
> **[스크린샷 6] 1:1 채팅**
>
> **[스크린샷 7] 포인트 송금 (지갑·거래 내역)**
>
> **[스크린샷 8] 신고 → 자동 차단**
>
> **[스크린샷 9] 관리자 대시보드**

---

## 7. 유지보수

### 7.1 유지보수 관점 점검

실제 사용 시나리오를 따라가며 불편한 점과 각 단계의 오류를 점검하고 개선하였다.
예: 상품 이미지가 없을 때 빈 카드가 보이던 문제 → 플레이스홀더(📦) 표시로 개선,
휴면 처리된 사용자의 세션 즉시 무효화 추가.

### 7.2 향후 개선 과제

- **HTTPS 적용**: 배포 시 TLS 적용 및 `COOKIE_SECURE=1` 설정.
- **이미지 콘텐츠 검증**: 확장자뿐 아니라 매직 바이트(Pillow 등)로 실제 이미지인지 검증.
- **다중 프로세스 대응**: 현재 Rate limiter·소켓 세션은 인메모리이므로, 다중 워커 배포
  시 Redis 등 공유 저장소로 이전.
- **감사 로그**: 관리자 조치·로그인 이력 등 보안 이벤트 로깅.
- **비밀번호 재설정**: 이메일 인증 기반 재설정 흐름 추가.

---

## 8. 결론 및 AI 도구 활용

본 프로젝트는 중고거래 플랫폼을 SDLC 전 과정에 따라 개발하면서, 각 단계에서 보안을
함께 설계·검증하였다. OWASP Top 10의 주요 항목(인젝션, XSS, CSRF, 인증·인가 결함,
취약한 접근 제어 등)에 대한 방어를 구현하고 자동화 테스트로 검증하여, 16개 테스트를
모두 통과하였다.

**AI 도구 활용**: 요구사항 정리, 시스템 설계, 보안 통제 코드 구현, 테스트 스크립트 작성,
보고서 작성 전 과정에서 AI 코딩 도구(Claude 등)를 적극 활용하였다. 특히 AI가 생성한
코드를 그대로 신뢰하지 않고, 위협 모델을 기준으로 **보안 관점에서 재검토**하여
파라미터 바인딩·권한 검증·트랜잭션 처리 등을 보강한 점이 핵심이다. 이는 "보안은 여전히
사람이 직접 고려해야 하는 영역"이라는 강의 메시지와 일치한다.

---

## 9. 부록

### 9.1 실행 방법 (요약)

```bash
git clone <repository-url> && cd tiny-market
conda create -n tiny-market python=3.11 -y && conda activate tiny-market
pip install -r requirements.txt
flask --app app init-db
flask --app app create-admin admin      # 관리자 계정 생성
python app.py                            # http://127.0.0.1:5000
```

자세한 내용은 `README.md` 참조.

### 9.2 참고 자료

- KISA 소프트웨어 개발보안 가이드 (Python)
- OWASP Top 10, OWASP Cheat Sheet Series
- Flask / Flask-WTF / Flask-SocketIO 공식 문서

### 9.3 산출물

- 소스 코드: (GitHub public repository 링크)
- 보안 체크리스트: `docs/security-checklist.md`
- 테스트 결과: `docs/test-results.md`, `tests/security_test.sh`
