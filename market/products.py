import os
import uuid

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template,
    request, send_from_directory, url_for,
)

from .db import get_db
from .security import clean_text, login_required, valid_int

bp = Blueprint("products", __name__)

# 허용할 이미지 확장자
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_PRICE = 100_000_000


def _save_image(file):
    """이미지 확장자를 확인하고 새 파일명으로 저장한다. 실패 시 (None, 오류메시지)."""
    if file is None or file.filename == "":
        return None, None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXT:
        return None, "이미지는 png/jpg/jpeg/gif/webp만 업로드할 수 있습니다."
    # 사용자가 올린 파일명은 쓰지 않고 서버에서 새 이름을 만든다
    name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], name))
    return name, None


def _validate_form(form):
    """상품 등록/수정 공통 검증. (data, error) 반환."""
    title = clean_text(form.get("title"), max_len=80, min_len=1)
    description = clean_text(form.get("description"), max_len=2000)
    price = valid_int(form.get("price"), 1, MAX_PRICE)
    if title is None:
        return None, "상품명은 1~80자여야 합니다."
    if description is None:
        return None, "설명은 2000자 이내여야 합니다."
    if price is None:
        return None, f"가격은 1~{MAX_PRICE:,}원 사이의 정수여야 합니다."
    return {"title": title, "description": description, "price": price}, None


def _get_product_or_404(product_id):
    product = get_db().execute(
        "SELECT p.*, u.username AS seller_name FROM product p "
        "JOIN user u ON p.seller_id = u.id WHERE p.id = ?",
        (product_id,),
    ).fetchone()
    if product is None:
        abort(404)
    return product


def _require_owner_or_admin(product):
    """상품 주인이나 관리자만 수정/삭제할 수 있게 확인한다"""
    if g.user is None or (
        product["seller_id"] != g.user["id"] and g.user["role"] != "admin"
    ):
        abort(403)


@bp.route("/")
def index():
    q = clean_text(request.args.get("q", ""), max_len=50) or ""
    db = get_db()
    if q:
        products = db.execute(
            "SELECT p.id, p.title, p.price, p.image FROM product p "
            "WHERE p.status = 'active' AND p.title LIKE ? ESCAPE '\\' ORDER BY p.id DESC",
            ("%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",),
        ).fetchall()
    else:
        products = db.execute(
            "SELECT p.id, p.title, p.price, p.image FROM product p "
            "WHERE p.status = 'active' ORDER BY p.id DESC"
        ).fetchall()

    recent_messages = []
    if g.user:
        recent_messages = db.execute(
            "SELECT m.content, m.created_at, u.username FROM message m "
            "JOIN user u ON m.sender_id = u.id "
            "WHERE m.room = 'global' ORDER BY m.id DESC LIMIT 30"
        ).fetchall()[::-1]
    return render_template(
        "products/list.html", products=products, q=q, recent_messages=recent_messages
    )


@bp.route("/products/new", methods=("GET", "POST"))
@login_required
def new():
    if request.method == "POST":
        data, error = _validate_form(request.form)
        if error is None:
            image, error = _save_image(request.files.get("image"))
        if error:
            flash(error)
        else:
            db = get_db()
            cur = db.execute(
                "INSERT INTO product (title, description, price, image, seller_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (data["title"], data["description"], data["price"], image, g.user["id"]),
            )
            db.commit()
            return redirect(url_for("products.detail", product_id=cur.lastrowid))
    return render_template("products/form.html", product=None)


@bp.route("/products/<int:product_id>")
def detail(product_id):
    product = _get_product_or_404(product_id)
    # 차단된 상품은 주인과 관리자만 볼 수 있다
    if product["status"] != "active":
        if g.user is None or (
            product["seller_id"] != g.user["id"] and g.user["role"] != "admin"
        ):
            abort(404)
    return render_template("products/detail.html", product=product)


@bp.route("/products/<int:product_id>/edit", methods=("GET", "POST"))
@login_required
def edit(product_id):
    product = _get_product_or_404(product_id)
    _require_owner_or_admin(product)
    if request.method == "POST":
        data, error = _validate_form(request.form)
        image = product["image"]
        if error is None:
            new_image, error = _save_image(request.files.get("image"))
            if new_image:
                image = new_image
        if error:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE product SET title = ?, description = ?, price = ?, image = ? "
                "WHERE id = ?",
                (data["title"], data["description"], data["price"], image, product_id),
            )
            db.commit()
            flash("상품이 수정되었습니다.")
            return redirect(url_for("products.detail", product_id=product_id))
    return render_template("products/form.html", product=product)


@bp.route("/products/<int:product_id>/delete", methods=("POST",))
@login_required
def delete(product_id):
    product = _get_product_or_404(product_id)
    _require_owner_or_admin(product)
    db = get_db()
    db.execute("DELETE FROM report WHERE target_type = 'product' AND target_id = ?", (product_id,))
    db.execute("DELETE FROM product WHERE id = ?", (product_id,))
    db.commit()
    flash("상품이 삭제되었습니다.")
    return redirect(url_for("auth.profile"))


@bp.route("/uploads/<name>")
def uploaded_file(name):
    # send_from_directory는 지정한 폴더 밖 파일 요청(../)을 막아준다
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], name)
