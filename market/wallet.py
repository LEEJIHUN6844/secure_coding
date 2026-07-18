import sqlite3

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for,
)

from .db import get_db
from .security import clean_text, login_required, valid_int, valid_username

bp = Blueprint("wallet", __name__, url_prefix="/wallet")

MAX_TRANSFER = 100_000_000


@bp.route("/")
@login_required
def index():
    db = get_db()
    history = db.execute(
        "SELECT t.*, s.username AS sender_name, r.username AS receiver_name "
        "FROM transfer t "
        "JOIN user s ON t.sender_id = s.id "
        "JOIN user r ON t.receiver_id = r.id "
        "WHERE t.sender_id = ? OR t.receiver_id = ? "
        "ORDER BY t.id DESC LIMIT 50",
        (g.user["id"], g.user["id"]),
    ).fetchall()
    return render_template(
        "wallet/index.html",
        history=history,
        receiver=request.args.get("receiver", ""),
    )


@bp.route("/transfer", methods=("POST",))
@login_required
def transfer():
    receiver_name = request.form.get("receiver", "").strip()
    amount = valid_int(request.form.get("amount"), 1, MAX_TRANSFER)
    memo = clean_text(request.form.get("memo", ""), max_len=100) or ""

    error = None
    if not valid_username(receiver_name):
        error = "받는 사람 아이디 형식이 올바르지 않습니다."
    elif amount is None:
        error = f"금액은 1~{MAX_TRANSFER:,}원 사이의 정수여야 합니다."

    db = get_db()
    receiver = None
    if error is None:
        receiver = db.execute(
            "SELECT id, status FROM user WHERE username = ?", (receiver_name,)
        ).fetchone()
        if receiver is None or receiver["status"] != "active":
            error = "받는 사람을 찾을 수 없습니다."
        elif receiver["id"] == g.user["id"]:
            error = "자기 자신에게는 송금할 수 없습니다."

    if error is None:
        # 잔액 확인 → 차감 → 기록을 한 번에 처리해서 중간에 끼어드는 요청을 막는다
        try:
            db.execute("BEGIN IMMEDIATE")
            sender = db.execute(
                "SELECT balance FROM user WHERE id = ?", (g.user["id"],)
            ).fetchone()
            if sender["balance"] < amount:
                db.rollback()
                error = "잔액이 부족합니다."
            else:
                db.execute(
                    "UPDATE user SET balance = balance - ? WHERE id = ?",
                    (amount, g.user["id"]),
                )
                db.execute(
                    "UPDATE user SET balance = balance + ? WHERE id = ?",
                    (amount, receiver["id"]),
                )
                db.execute(
                    "INSERT INTO transfer (sender_id, receiver_id, amount, memo) "
                    "VALUES (?, ?, ?, ?)",
                    (g.user["id"], receiver["id"], amount, memo),
                )
                db.commit()
                flash(f"{receiver_name}님에게 {amount:,}원을 송금했습니다.")
                return redirect(url_for("wallet.index"))
        except sqlite3.Error:
            db.rollback()
            error = "송금 처리 중 오류가 발생했습니다."

    flash(error)
    return redirect(url_for("wallet.index", receiver=receiver_name))
