import sqlite3
import time

import bcrypt
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for,
)

from .db import get_db
from .security import clean_text, login_required, valid_password, valid_username

bp = Blueprint("auth", __name__, url_prefix="/auth")

LOCKOUT_THRESHOLD = 5      # 로그인 실패 허용 횟수
LOCKOUT_SECONDS = 300      # 잠금 시간(초)

# 없는 아이디로 로그인해도 있는 아이디와 비슷한 시간이 걸리도록 비교용으로 쓰는 해시
DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt())


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        user = get_db().execute(
            "SELECT * FROM user WHERE id = ?", (user_id,)
        ).fetchone()
        # 휴면 계정이면 로그아웃 처리
        if user is not None and user["status"] == "active":
            g.user = user
        else:
            session.clear()


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        error = None
        if not valid_username(username):
            error = "아이디는 영문/숫자/밑줄 4~20자여야 합니다."
        elif not valid_password(password):
            error = "비밀번호는 8~72자, 영문과 숫자를 포함해야 합니다."
        elif password != password2:
            error = "비밀번호 확인이 일치하지 않습니다."

        if error is None:
            db = get_db()
            pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            try:
                db.execute(
                    "INSERT INTO user (username, password_hash) VALUES (?, ?)",
                    (username, pw_hash),
                )
                db.commit()
            except sqlite3.IntegrityError:
                error = "이미 사용 중인 아이디입니다."
            else:
                flash("회원가입이 완료되었습니다. 로그인해주세요.")
                return redirect(url_for("auth.login"))
        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()

        now = int(time.time())
        # 아이디가 틀렸는지 비밀번호가 틀렸는지 구분해서 알려주지 않는다
        generic_error = "아이디 또는 비밀번호가 올바르지 않습니다."

        if user is None:
            # 없는 아이디여도 비밀번호 비교를 한 번 해서 응답 시간을 비슷하게 맞춘다
            bcrypt.checkpw(password.encode(), DUMMY_HASH)
            flash(generic_error)
        elif user["locked_until"] > now:
            flash("로그인 실패가 반복되어 계정이 잠시 잠겼습니다. 잠시 후 다시 시도해주세요.")
        elif not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            fails = user["failed_logins"] + 1
            locked_until = now + LOCKOUT_SECONDS if fails >= LOCKOUT_THRESHOLD else 0
            db.execute(
                "UPDATE user SET failed_logins = ?, locked_until = ? WHERE id = ?",
                (0 if locked_until else fails, locked_until, user["id"]),
            )
            db.commit()
            flash(generic_error)
        elif user["status"] != "active":
            flash("휴면 처리된 계정입니다. 관리자에게 문의하세요.")
        else:
            db.execute(
                "UPDATE user SET failed_logins = 0, locked_until = 0 WHERE id = ?",
                (user["id"],),
            )
            db.commit()
            # 로그인할 때 기존 세션을 지우고 새로 발급한다
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            return redirect(url_for("products.index"))

    return render_template("auth/login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    return redirect(url_for("products.index"))


@bp.route("/profile", methods=("GET", "POST"))
@login_required
def profile():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "bio":
            bio = clean_text(request.form.get("bio"), max_len=500)
            if bio is None:
                flash("소개글은 500자 이내여야 합니다.")
            else:
                db.execute("UPDATE user SET bio = ? WHERE id = ?", (bio, g.user["id"]))
                db.commit()
                flash("소개글이 수정되었습니다.")
        elif action == "password":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            new2 = request.form.get("new_password2", "")
            # 현재 비밀번호를 먼저 확인한다
            if not bcrypt.checkpw(current.encode(), g.user["password_hash"].encode()):
                flash("현재 비밀번호가 올바르지 않습니다.")
            elif not valid_password(new):
                flash("새 비밀번호는 8~72자, 영문과 숫자를 포함해야 합니다.")
            elif new != new2:
                flash("새 비밀번호 확인이 일치하지 않습니다.")
            else:
                pw_hash = bcrypt.hashpw(new.encode(), bcrypt.gensalt()).decode()
                db.execute(
                    "UPDATE user SET password_hash = ? WHERE id = ?",
                    (pw_hash, g.user["id"]),
                )
                db.commit()
                flash("비밀번호가 변경되었습니다.")
        return redirect(url_for("auth.profile"))

    my_products = db.execute(
        "SELECT * FROM product WHERE seller_id = ? ORDER BY id DESC",
        (g.user["id"],),
    ).fetchall()
    return render_template("auth/profile.html", my_products=my_products)


@bp.route("/users/<int:user_id>")
@login_required
def user_detail(user_id):
    """다른 사용자 프로필 조회 (비밀번호 등은 제외하고 조회)"""
    db = get_db()
    user = db.execute(
        "SELECT id, username, bio, status, created_at FROM user WHERE id = ?",
        (user_id,),
    ).fetchone()
    if user is None:
        from flask import abort
        abort(404)
    products = db.execute(
        "SELECT * FROM product WHERE seller_id = ? AND status = 'active' ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    return render_template("auth/user_detail.html", profile=user, products=products)
