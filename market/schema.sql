DROP TABLE IF EXISTS transfer;
DROP TABLE IF EXISTS message;
DROP TABLE IF EXISTS dm_thread;
DROP TABLE IF EXISTS report;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    bio           TEXT NOT NULL DEFAULT '',
    role          TEXT NOT NULL DEFAULT 'user'    CHECK (role IN ('user', 'admin')),
    status        TEXT NOT NULL DEFAULT 'active'  CHECK (status IN ('active', 'dormant')),
    balance       INTEGER NOT NULL DEFAULT 100000 CHECK (balance >= 0),
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked_until  INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price       INTEGER NOT NULL CHECK (price > 0),
    image       TEXT,
    seller_id   INTEGER NOT NULL REFERENCES user (id),
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked')),
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE report (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER NOT NULL REFERENCES user (id),
    target_type TEXT NOT NULL CHECK (target_type IN ('user', 'product')),
    target_id   INTEGER NOT NULL,
    reason      TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (reporter_id, target_type, target_id)
);

CREATE TABLE dm_thread (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_lo INTEGER NOT NULL REFERENCES user (id),
    user_hi INTEGER NOT NULL REFERENCES user (id),
    UNIQUE (user_lo, user_hi)
);

CREATE TABLE message (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    room       TEXT NOT NULL,
    sender_id  INTEGER NOT NULL REFERENCES user (id),
    content    TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transfer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id   INTEGER NOT NULL REFERENCES user (id),
    receiver_id INTEGER NOT NULL REFERENCES user (id),
    amount      INTEGER NOT NULL CHECK (amount > 0),
    memo        TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_product_status ON product (status);
CREATE INDEX idx_message_room ON message (room, id);
CREATE INDEX idx_report_target ON report (target_type, target_id);
