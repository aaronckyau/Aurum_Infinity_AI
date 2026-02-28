"""
database.py - SQLite 資料庫管理
============================================================
現階段只負責：
  - Admin session 管理（記住登入狀態）

未來第三階段擴充：
  - 用戶資料表（users）
  - 會員等級管理
============================================================
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aurum.db')


def get_db() -> sqlite3.Connection:
    """取得資料庫連線，欄位可用名稱存取"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化資料庫，app 啟動時執行一次"""
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS admin_sessions (
                token      TEXT PRIMARY KEY,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()
    finally:
        conn.close()
