import os
import secrets

from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect

csrf = CSRFProtect()
socketio = SocketIO()


def _load_secret_key(instance_path: str) -> str:
    """비밀키를 파일에서 읽고, 없으면 새로 만들어 저장한다."""
    path = os.path.join(instance_path, "secret.key")
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(path, "w") as f:
        f.write(key)
    os.chmod(path, 0o600)
    return key


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_object("config.Config")
    app.config["SECRET_KEY"] = _load_secret_key(app.instance_path)
    app.config["DATABASE"] = os.path.join(app.instance_path, "market.sqlite")
    app.config["UPLOAD_FOLDER"] = os.path.join(app.instance_path, "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    csrf.init_app(app)
    socketio.init_app(app)

    from . import db
    db.init_app(app)

    from . import auth, products, chat, reports, wallet, admin
    app.register_blueprint(auth.bp)
    app.register_blueprint(products.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(wallet.bp)
    app.register_blueprint(admin.bp)
    app.add_url_rule("/", endpoint="products.index")

    # 오류가 나도 사용자에게는 간단한 안내만 보여준다
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/error.html", code=400, msg="잘못된 요청입니다."), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/error.html", code=403, msg="접근 권한이 없습니다."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/error.html", code=404, msg="페이지를 찾을 수 없습니다."), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/error.html", code=413, msg="업로드 용량 제한(2MB)을 초과했습니다."), 413

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/error.html", code=500, msg="서버 오류가 발생했습니다."), 500

    # 모든 응답에 기본 보안 헤더를 붙인다
    @app.after_request
    def set_security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.socket.io; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'"
        )
        return resp

    return app
