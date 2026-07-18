from flask import Blueprint, abort, flash, redirect, render_template, url_for

from .db import get_db
from .security import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def dashboard():
    db = get_db()
    users = db.execute(
        "SELECT id, username, role, status, balance, created_at, "
        "(SELECT COUNT(*) FROM report WHERE target_type = 'user' AND target_id = user.id) AS report_count "
        "FROM user ORDER BY id"
    ).fetchall()
    products = db.execute(
        "SELECT p.id, p.title, p.price, p.status, u.username AS seller_name, "
        "(SELECT COUNT(*) FROM report WHERE target_type = 'product' AND target_id = p.id) AS report_count "
        "FROM product p JOIN user u ON p.seller_id = u.id ORDER BY p.id DESC"
    ).fetchall()
    reports = db.execute(
        "SELECT r.*, u.username AS reporter_name FROM report r "
        "JOIN user u ON r.reporter_id = u.id ORDER BY r.id DESC LIMIT 100"
    ).fetchall()
    return render_template(
        "admin/dashboard.html", users=users, products=products, reports=reports
    )


@bp.route("/users/<int:user_id>/toggle-status", methods=("POST",))
@admin_required
def toggle_user_status(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        abort(404)
    if user["role"] == "admin":
        flash("관리자 계정은 상태를 변경할 수 없습니다.")
        return redirect(url_for("admin.dashboard"))
    new_status = "dormant" if user["status"] == "active" else "active"
    db.execute("UPDATE user SET status = ? WHERE id = ?", (new_status, user_id))
    if new_status == "active":
        # 복구 시 누적 신고 초기화
        db.execute(
            "DELETE FROM report WHERE target_type = 'user' AND target_id = ?", (user_id,)
        )
    db.commit()
    flash(f"'{user['username']}' 계정을 {'휴면' if new_status == 'dormant' else '활성'} 처리했습니다.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/products/<int:product_id>/toggle-status", methods=("POST",))
@admin_required
def toggle_product_status(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM product WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        abort(404)
    new_status = "blocked" if product["status"] == "active" else "active"
    db.execute("UPDATE product SET status = ? WHERE id = ?", (new_status, product_id))
    if new_status == "active":
        db.execute(
            "DELETE FROM report WHERE target_type = 'product' AND target_id = ?",
            (product_id,),
        )
    db.commit()
    flash(f"상품 '{product['title']}'을(를) {'차단' if new_status == 'blocked' else '복구'}했습니다.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/products/<int:product_id>/delete", methods=("POST",))
@admin_required
def delete_product(product_id):
    db = get_db()
    product = db.execute("SELECT id FROM product WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        abort(404)
    db.execute("DELETE FROM report WHERE target_type = 'product' AND target_id = ?", (product_id,))
    db.execute("DELETE FROM product WHERE id = ?", (product_id,))
    db.commit()
    flash("상품을 삭제했습니다.")
    return redirect(url_for("admin.dashboard"))
