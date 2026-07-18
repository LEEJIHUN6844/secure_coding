import sqlite3

from flask import (
    Blueprint, abort, flash, g, redirect, render_template, request, url_for,
)

from .db import get_db
from .security import RateLimiter, clean_text, login_required, valid_int

bp = Blueprint("reports", __name__, url_prefix="/reports")

BLOCK_THRESHOLD = 3   # 신고가 이만큼 쌓이면 자동 조치
# 신고 남용 막기: 한 사람이 1시간에 10건까지
report_limiter = RateLimiter(limit=10, window=3600)


def _apply_auto_action(db, target_type, target_id):
    """신고가 기준치를 넘으면 상품은 차단, 사용자는 휴면 처리한다"""
    count = db.execute(
        "SELECT COUNT(*) AS c FROM report WHERE target_type = ? AND target_id = ?",
        (target_type, target_id),
    ).fetchone()["c"]
    if count < BLOCK_THRESHOLD:
        return
    if target_type == "product":
        db.execute(
            "UPDATE product SET status = 'blocked' WHERE id = ?", (target_id,)
        )
    else:
        # 관리자 계정은 휴면 처리에서 제외한다
        db.execute(
            "UPDATE user SET status = 'dormant' WHERE id = ? AND role != 'admin'",
            (target_id,),
        )


@bp.route("/new", methods=("GET", "POST"))
@login_required
def new():
    target_type = request.values.get("target_type", "")
    target_id = valid_int(request.values.get("target_id"), 1, 2**31)

    if target_type not in ("user", "product") or target_id is None:
        abort(400)

    db = get_db()
    # 신고 대상이 실제로 있는지 확인
    if target_type == "product":
        target = db.execute(
            "SELECT p.id, p.title AS label FROM product p WHERE p.id = ?", (target_id,)
        ).fetchone()
    else:
        target = db.execute(
            "SELECT id, username AS label FROM user WHERE id = ?", (target_id,)
        ).fetchone()
    if target is None:
        abort(404)

    if target_type == "user" and target_id == g.user["id"]:
        abort(400)

    if request.method == "POST":
        reason = clean_text(request.form.get("reason"), max_len=500, min_len=10)
        if reason is None:
            flash("신고 사유는 10~500자로 작성해주세요.")
        elif not report_limiter.allow(g.user["id"]):
            flash("신고가 너무 잦습니다. 잠시 후 다시 시도해주세요.")
        else:
            try:
                db.execute(
                    "INSERT INTO report (reporter_id, target_type, target_id, reason) "
                    "VALUES (?, ?, ?, ?)",
                    (g.user["id"], target_type, target_id, reason),
                )
                _apply_auto_action(db, target_type, target_id)
                db.commit()
                flash("신고가 접수되었습니다.")
                return redirect(url_for("products.index"))
            except sqlite3.IntegrityError:
                # 같은 대상을 두 번 신고하면 여기로 걸린다
                flash("이미 신고한 대상입니다.")

    return render_template(
        "reports/new.html", target_type=target_type, target_id=target_id, target=target
    )
