import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "bot.db")


class Database:
    def __init__(self):
        self.path = DB_PATH

    def _conn(self):
        return sqlite3.connect(self.path)

    def init(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    username    TEXT,
                    language    TEXT DEFAULT 'ru',
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS purchases (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    plan        TEXT NOT NULL,
                    amount      INTEGER NOT NULL,
                    pay_method  TEXT,
                    payer_name  TEXT,
                    bought_at   TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );
            """)

    def ensure_user(self, user_id: int, username: str | None):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )

    def get_language(self, user_id: int) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT language FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row[0] if row else None

    def set_language(self, user_id: int, lang: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id)
            )

    def has_plan(self, user_id: int, plan: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM purchases WHERE user_id = ? AND plan = ?",
                (user_id, plan)
            ).fetchone()
            return row is not None

    def add_purchase(self, user_id: int, plan: str, amount: int = 0,
                     pay_method: str = "", payer_name: str = ""):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO purchases (user_id, plan, amount, pay_method, payer_name)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, plan, amount, pay_method, payer_name)
            )

    def get_purchases(self, user_id: int) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT plan, amount, pay_method, payer_name, bought_at "
                "FROM purchases WHERE user_id = ? ORDER BY bought_at DESC",
                (user_id,)
            ).fetchall()
            return [
                {"plan": r[0], "amount": r[1], "pay_method": r[2],
                 "payer_name": r[3], "bought_at": r[4]}
                for r in rows
            ]
