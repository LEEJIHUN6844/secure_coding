import os


class Config:
    # SECRET_KEY는 코드에 적지 않고 create_app()에서 파일로 불러온다
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # HTTPS로 배포할 때는 COOKIE_SECURE=1 로 켠다
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = 3600  # 세션 유지 시간(초)
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 업로드 최대 2MB
    WTF_CSRF_TIME_LIMIT = 3600
