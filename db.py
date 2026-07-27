"""
PMP 备考辅助系统 — 配置 & 数据库 Schema
"""
import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "pmp_study.db")
PMP_KUID = "0s_3145869891"          # PMP备考知识库

def _find_kwiki_cli() -> str:
    """查找 kwiki-cli 可执行文件路径"""
    import shutil
    path = shutil.which("kwiki-cli")
    if path:
        return path
    npm_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "npm")
    for name in ["kwiki-cli.cmd", "kwiki-cli"]:
        candidate = os.path.join(npm_dir, name)
        if os.path.exists(candidate):
            return candidate
    for prefix in ["/usr/local/bin", "/usr/bin"]:
        candidate = os.path.join(prefix, "kwiki-cli")
        if os.path.exists(candidate):
            return candidate
    return "kwiki-cli"

KWIKI_CLI = _find_kwiki_cli()
KWIKI_AUTH = os.environ.get(
    "X_KWIKI_AUTH",
    "ps6gnmorfaZk3DR8+G+ts4gQerR+nkFNG2Q/4EMHqd2mgp50FBzIuAM/XVbV3dJkeE7uOIW9l1atEgLyJzCGpacY/bK/+IOv7Xh65W1x31jwXHoXH5hP/WkmnW6VBNHTo259mmeQmT1A3MkexQ==",
)

PMP_DOMAINS = [
    "整合管理", "范围管理", "时间管理", "成本管理",
    "质量管理", "人力资源管理", "沟通管理", "风险管理",
    "采购管理", "干系人管理",
]


def hash_password(password: str) -> str:
    return hashlib.sha256(f"pmp_{password}_salt".encode()).hexdigest()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表结构 + 默认用户"""
    conn = get_db()
    conn.executescript("""
        -- 用户表
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user',  -- admin / user
            created_at  TEXT    DEFAULT (datetime('now','localtime'))
        );

        -- 每日知识卡片
        CREATE TABLE IF NOT EXISTS cards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            date        TEXT    NOT NULL,
            topic       TEXT    NOT NULL,
            title       TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            source_ref  TEXT,
            is_reviewed INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_cards_user_date ON cards(user_id, date);

        -- 测验记录
        CREATE TABLE IF NOT EXISTS quizzes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            date        TEXT    NOT NULL,
            topic       TEXT    NOT NULL,
            questions   TEXT    NOT NULL,
            total       INTEGER NOT NULL,
            correct     INTEGER NOT NULL,
            score       REAL    NOT NULL,
            created_at  TEXT    DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_quizzes_user_date ON quizzes(user_id, date);

        -- 单题答题记录
        CREATE TABLE IF NOT EXISTS quiz_answers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            quiz_id     INTEGER NOT NULL REFERENCES quizzes(id),
            topic       TEXT    NOT NULL,
            question    TEXT    NOT NULL,
            user_answer TEXT,
            correct_answer TEXT NOT NULL,
            is_correct  INTEGER NOT NULL,
            explanation TEXT,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_answers_user_topic ON quiz_answers(user_id, topic);
        CREATE INDEX IF NOT EXISTS idx_answers_user_correct ON quiz_answers(user_id, is_correct);

        -- 错题库（含艾宾浩斯记忆曲线）
        CREATE TABLE IF NOT EXISTS wrong_answer_bank (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            quiz_answer_id  INTEGER NOT NULL REFERENCES quiz_answers(id),
            topic           TEXT    NOT NULL,
            question        TEXT    NOT NULL,
            options_json    TEXT    NOT NULL,
            correct_answer  TEXT    NOT NULL,
            explanation     TEXT,
            review_count    INTEGER DEFAULT 0,
            next_review     TEXT    NOT NULL,
            last_reviewed   TEXT,
            created_at      TEXT    DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_wrong_user_next ON wrong_answer_bank(user_id, next_review);
        CREATE INDEX IF NOT EXISTS idx_wrong_user_topic ON wrong_answer_bank(user_id, topic);

        -- 学习日志
        CREATE TABLE IF NOT EXISTS study_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            date        TEXT    NOT NULL,
            activity    TEXT    NOT NULL,
            duration_min INTEGER DEFAULT 0,
            detail      TEXT,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_study_user_date ON study_log(user_id, date);
    """)

    # 迁移：为旧表添加 user_id 列（新增时忽略已存在错误）
    for table in ["cards", "quizzes", "quiz_answers", "wrong_answer_bank", "study_log"]:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # 列已存在

    # 创建默认用户（admin / user）
    existing = conn.execute("SELECT id FROM users").fetchall()
    if not existing:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?,?,?)",
            ("admin", hash_password("admin123"), "admin"),
        )
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?,?,?)",
            ("user", hash_password("user123"), "user"),
        )

    conn.commit()
    conn.close()


def verify_login(username: str, password: str):  # -> dict or None
    """验证登录，返回用户信息或 None"""
    conn = get_db()
    row = conn.execute(
        "SELECT id, username, role FROM users WHERE username=? AND password=?",
        (username, hash_password(password)),
    ).fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"], "role": row["role"]}
    return None


def reset_db():
    """重置数据库（删除所有表并重建）"""
    conn = get_db()
    conn.executescript("""
        DROP TABLE IF EXISTS wrong_answer_bank;
        DROP TABLE IF EXISTS quiz_answers;
        DROP TABLE IF EXISTS quizzes;
        DROP TABLE IF EXISTS cards;
        DROP TABLE IF EXISTS study_log;
    """)
    conn.commit()
    conn.close()
    init_db()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized: {DB_PATH}")
