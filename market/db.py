import sqlite3

import bcrypt
import click
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))


@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("데이터베이스를 초기화했습니다.")


@click.command("create-admin")
@click.argument("username")
@click.password_option()
def create_admin_command(username, password):
    """관리자 계정 생성: flask --app app create-admin <username>"""
    from .security import valid_password, valid_username

    if not valid_username(username):
        click.echo("아이디는 영문/숫자/밑줄 4~20자여야 합니다.")
        return
    if not valid_password(password):
        click.echo("비밀번호는 8~72자, 영문과 숫자를 포함해야 합니다.")
        return
    db = get_db()
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        db.execute(
            "INSERT INTO user (username, password_hash, role) VALUES (?, ?, 'admin')",
            (username, pw_hash),
        )
        db.commit()
        click.echo(f"관리자 '{username}' 생성 완료.")
    except sqlite3.IntegrityError:
        click.echo("이미 존재하는 아이디입니다.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin_command)
