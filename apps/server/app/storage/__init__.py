"""建表。首版直接 create_all；迁移工具选型见 docs/06 §9 Q6。

create_all 只建缺失的表，不会给已有表补列；下面按需补齐后续新增的列。
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.storage.db import engine
from app.storage.models import Base

# 表名 → (列名, 列定义)。只用于演进早期新增的可空列。
_ADDED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "users": [("display_name", "VARCHAR(64)"), ("avatar", "VARCHAR(128)")],
    "sites": [
        ("limit_interval", "INTEGER DEFAULT 0"),
        ("limit_count", "INTEGER DEFAULT 0"),
        ("limit_seconds", "INTEGER DEFAULT 0"),
    ],
    "site_statistics": [
        ("lst_mod_date", "VARCHAR(32) DEFAULT ''"),
        ("note", "TEXT DEFAULT ''"),
    ],
    "preferences": [
        ("icon_libraries", "TEXT DEFAULT '[]'"),
        ("settings", "TEXT DEFAULT '{}'"),
        ("api_token", "VARCHAR(64) DEFAULT ''"),
        ("updated_at", "DATETIME"),
    ],
    "storage_bindings": [
        ("access_token", "TEXT DEFAULT ''"),
        ("refresh_token", "TEXT DEFAULT ''"),
        ("refresh_at", "INTEGER DEFAULT 0"),
        ("expires_in", "INTEGER DEFAULT 0"),
        ("account_name", "VARCHAR(128) DEFAULT ''"),
        ("account_avatar", "VARCHAR(512) DEFAULT ''"),
        ("vip_level", "VARCHAR(64) DEFAULT ''"),
        ("vip_expire", "INTEGER DEFAULT 0"),
        ("total_bytes", "INTEGER DEFAULT 0"),
        ("used_bytes", "INTEGER DEFAULT 0"),
        ("info_at", "INTEGER DEFAULT 0"),
        ("throttle_until", "INTEGER DEFAULT 0"),
    ],
}


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if not inspector.has_table(table):
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            added: list[str] = []
            for name, ddl in columns:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                    added.append(name)
            # 网盘概况新增头像 / 会员字段后清同步时间，下次读绑定会补拉一次
            if table == "storage_bindings" and (
                "account_avatar" in added or "vip_level" in added or "vip_expire" in added
            ):
                conn.execute(text("UPDATE storage_bindings SET info_at = 0"))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
