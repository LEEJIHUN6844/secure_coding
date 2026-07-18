import re
import time
from collections import defaultdict, deque
from functools import wraps

from flask import abort, g, redirect, session, url_for

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,20}$")


def valid_username(u):
    """아이디는 영문/숫자/밑줄 4~20자만 허용한다"""
    return bool(u) and bool(USERNAME_RE.fullmatch(u))


def valid_password(p):
    """비밀번호는 8~72자이고 영문과 숫자를 모두 포함해야 한다"""
    if not p or not (8 <= len(p) <= 72):
        return False
    return bool(re.search(r"[A-Za-z]", p)) and bool(re.search(r"\d", p))


def valid_int(value, min_v, max_v):
    """입력값을 정수로 바꾸고 범위를 확인한다. 안 맞으면 None."""
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not (min_v <= n <= max_v):
        return None
    return n


def clean_text(value, max_len, min_len=0):
    """앞뒤 공백을 없애고 길이를 확인한다. 안 맞으면 None."""
    if value is None:
        return None
    s = str(value).strip()
    if not (min_len <= len(s) <= max_len):
        return None
    return s


def login_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if g.user["role"] != "admin":
            abort(403)
        return view(**kwargs)
    return wrapped


class RateLimiter:
    """window초 동안 limit회까지만 허용하는 간단한 횟수 제한기"""

    def __init__(self, limit, window):
        self.limit = limit
        self.window = window
        self.hits = defaultdict(deque)

    def allow(self, key):
        now = time.time()
        q = self.hits[key]
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
