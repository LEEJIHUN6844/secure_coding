from flask import (
    Blueprint, abort, g, redirect, render_template, session, url_for,
)
from flask_socketio import emit, join_room

from . import socketio
from .db import get_db
from .security import RateLimiter, clean_text, login_required

bp = Blueprint("chat", __name__, url_prefix="/chat")

# 도배 방지: 한 사람이 10초에 5개까지만
message_limiter = RateLimiter(limit=5, window=10)
MAX_MESSAGE_LEN = 500


def _thread_room(thread):
    return f"dm-{thread['user_lo']}-{thread['user_hi']}"


def _get_my_thread_or_404(thread_id, user_id):
    thread = get_db().execute(
        "SELECT * FROM dm_thread WHERE id = ?", (thread_id,)
    ).fetchone()
    # 내가 참여한 대화방만 열 수 있게 한다
    if thread is None or user_id not in (thread["user_lo"], thread["user_hi"]):
        abort(404)
    return thread


@bp.route("/dm")
@login_required
def dm_list():
    db = get_db()
    threads = db.execute(
        "SELECT t.id, ulo.username AS name_lo, uhi.username AS name_hi "
        "FROM dm_thread t "
        "JOIN user ulo ON t.user_lo = ulo.id "
        "JOIN user uhi ON t.user_hi = uhi.id "
        "WHERE t.user_lo = ? OR t.user_hi = ? ORDER BY t.id DESC",
        (g.user["id"], g.user["id"]),
    ).fetchall()
    return render_template("chat/dm_list.html", threads=threads)


@bp.route("/dm/start/<int:user_id>", methods=("POST",))
@login_required
def dm_start(user_id):
    if user_id == g.user["id"]:
        abort(400)
    db = get_db()
    other = db.execute("SELECT id FROM user WHERE id = ?", (user_id,)).fetchone()
    if other is None:
        abort(404)
    lo, hi = sorted((g.user["id"], user_id))
    db.execute(
        "INSERT OR IGNORE INTO dm_thread (user_lo, user_hi) VALUES (?, ?)", (lo, hi)
    )
    db.commit()
    thread = db.execute(
        "SELECT * FROM dm_thread WHERE user_lo = ? AND user_hi = ?", (lo, hi)
    ).fetchone()
    return redirect(url_for("chat.dm_room", thread_id=thread["id"]))


@bp.route("/dm/<int:thread_id>")
@login_required
def dm_room(thread_id):
    thread = _get_my_thread_or_404(thread_id, g.user["id"])
    room = _thread_room(thread)
    db = get_db()
    other_id = thread["user_hi"] if thread["user_lo"] == g.user["id"] else thread["user_lo"]
    other = db.execute("SELECT username FROM user WHERE id = ?", (other_id,)).fetchone()
    messages = db.execute(
        "SELECT m.content, m.created_at, u.username FROM message m "
        "JOIN user u ON m.sender_id = u.id WHERE m.room = ? ORDER BY m.id LIMIT 200",
        (room,),
    ).fetchall()
    return render_template(
        "chat/dm_room.html", room=room, other=other, messages=messages
    )


# ---------- Socket.IO ----------

def _current_user():
    """소켓 이벤트에서 로그인한 사용자를 세션으로 확인한다"""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    user = get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    if user is None or user["status"] != "active":
        return None
    return user


def _authorized_room(user, room):
    """이 사용자가 들어갈 수 있는 방인지 확인한다"""
    if room == "global":
        return True
    if room.startswith("dm-"):
        parts = room.split("-")
        if len(parts) == 3 and all(p.isdigit() for p in parts[1:]):
            lo, hi = int(parts[1]), int(parts[2])
            if user["id"] not in (lo, hi):
                return False
            thread = get_db().execute(
                "SELECT id FROM dm_thread WHERE user_lo = ? AND user_hi = ?", (lo, hi)
            ).fetchone()
            return thread is not None
    return False


@socketio.on("connect")
def on_connect():
    # 로그인하지 않았으면 연결을 막는다
    if _current_user() is None:
        return False


@socketio.on("join")
def on_join(data):
    user = _current_user()
    if user is None or not isinstance(data, dict):
        return
    room = str(data.get("room", ""))
    if not _authorized_room(user, room):
        return
    join_room(room)


@socketio.on("send_message")
def on_send(data):
    user = _current_user()
    if user is None or not isinstance(data, dict):
        return
    room = str(data.get("room", ""))
    if not _authorized_room(user, room):
        return
    content = clean_text(data.get("content"), max_len=MAX_MESSAGE_LEN, min_len=1)
    if content is None:
        emit("error_message", {"msg": f"메시지는 1~{MAX_MESSAGE_LEN}자여야 합니다."})
        return
    if not message_limiter.allow(user["id"]):
        emit("error_message", {"msg": "메시지를 너무 빠르게 보내고 있습니다."})
        return
    db = get_db()
    db.execute(
        "INSERT INTO message (room, sender_id, content) VALUES (?, ?, ?)",
        (room, user["id"], content),
    )
    db.commit()
    # 받는 쪽 화면에서는 글자로만 표시해서 태그가 실행되지 않게 한다
    emit(
        "new_message",
        {"username": user["username"], "content": content},
        to=room,
    )
