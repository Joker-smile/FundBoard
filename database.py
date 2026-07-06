# -*- coding: utf-8 -*-
"""
SQLite 数据库模块 - 场外指数基金数据获取工具

提供 FundDatabase 类，管理三张核心表：
- funds：基金最新数据快照
- nav_history：历史净值记录
- source_status：数据源健康状态

所有数据持久化操作通过此模块完成。
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional

from config import APP_SETTINGS, BASE_DIR

logger = logging.getLogger(__name__)


class FundDatabase:
    """基金数据 SQLite 持久化层。"""

    def __init__(self, db_path: Optional[str] = None):
        """逻辑。"""
        if db_path is None:
            db_path = os.path.join(BASE_DIR, APP_SETTINGS["db_file"])
        self.db_path = db_path
        self._init_db()

    # ----------------------------------------------------------
    # 连接 & 初始化
    # ----------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        """获取一个数据库连接，row_factory 设为 sqlite3.Row。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self):
        """创建所需的表（如果不存在）。"""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            # ---------- funds 表 ----------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS funds (
                    code            TEXT PRIMARY KEY,
                    name            TEXT NOT NULL,
                    index_type      TEXT NOT NULL,
                    nav             REAL,
                    nav_date        TEXT,
                    acc_nav         REAL,
                    daily_change    REAL,
                    daily_change_pct REAL,
                    since_inception TEXT,
                    purchase_limit  TEXT DEFAULT '',
                    purchase_status TEXT DEFAULT '',
                    data_source     TEXT DEFAULT '',
                    updated_at      TEXT,
                    is_custom       INTEGER DEFAULT 0
                );
            """)

            # 尝试添加 is_custom 字段，防止已有表结构冲突
            try:
                cursor.execute("ALTER TABLE funds ADD COLUMN is_custom INTEGER DEFAULT 0;")
            except sqlite3.OperationalError:
                # 字段可能已经存在，忽略错误
                pass

            # ---------- nav_history 表 ----------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nav_history (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    code            TEXT NOT NULL,
                    nav             REAL,
                    acc_nav         REAL,
                    daily_change_pct REAL,
                    nav_date        TEXT,
                    fetched_at      TEXT,
                    UNIQUE(code, nav_date)
                );
            """)

            # ---------- source_status 表 ----------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS source_status (
                    source_name     TEXT PRIMARY KEY,
                    last_success    TEXT,
                    last_failure    TEXT,
                    fail_count      INTEGER DEFAULT 0,
                    is_available    INTEGER DEFAULT 1
                );
            """)

            conn.commit()
            logger.info("数据库初始化完成: %s", self.db_path)
        except sqlite3.Error as exc:
            logger.error("数据库初始化失败: %s", exc)
            raise
        finally:
            conn.close()

    # ----------------------------------------------------------
    # 基金数据操作
    # ----------------------------------------------------------

    def save_funds(self, funds: List[Dict]):
        """批量保存基金数据（INSERT INTO ... ON CONFLICT DO UPDATE）。

        同时向 nav_history 插入一条历史净值记录。

        Args:
            funds: 基金字典列表，每个字典包含 code/name/nav 等字段。
        """
        if not funds:
            return

        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for fund in funds:
                # 写入 / 更新 funds 表，防止覆盖已有的 is_custom 标记
                cursor.execute("""
                    INSERT INTO funds
                        (code, name, index_type, nav, nav_date, acc_nav,
                         daily_change, daily_change_pct, since_inception,
                         purchase_limit, purchase_status, data_source, updated_at, is_custom)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                        name=excluded.name,
                        index_type=excluded.index_type,
                        nav=excluded.nav,
                        nav_date=excluded.nav_date,
                        acc_nav=excluded.acc_nav,
                        daily_change=excluded.daily_change,
                        daily_change_pct=excluded.daily_change_pct,
                        since_inception=excluded.since_inception,
                        purchase_limit=excluded.purchase_limit,
                        purchase_status=excluded.purchase_status,
                        data_source=excluded.data_source,
                        updated_at=excluded.updated_at,
                        is_custom=CASE WHEN excluded.is_custom = 1 THEN 1 ELSE funds.is_custom END
                """, (
                    fund.get("code", ""),
                    fund.get("name", ""),
                    fund.get("index_type", ""),
                    fund.get("nav"),
                    fund.get("nav_date", ""),
                    fund.get("acc_nav"),
                    fund.get("daily_change"),
                    fund.get("daily_change_pct"),
                    fund.get("since_inception"),
                    fund.get("purchase_limit", ""),
                    fund.get("purchase_status", ""),
                    fund.get("data_source", ""),
                    now,
                    fund.get("is_custom", 0),
                ))

                # 同时插入 nav_history（忽略重复）
                if fund.get("nav") is not None and fund.get("nav_date"):
                    cursor.execute("""
                        INSERT OR IGNORE INTO nav_history
                            (code, nav, acc_nav, daily_change_pct, nav_date, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        fund.get("code", ""),
                        fund.get("nav"),
                        fund.get("acc_nav"),
                        fund.get("daily_change_pct"),
                        fund.get("nav_date", ""),
                        now,
                    ))

            conn.commit()
            logger.info("成功保存 %d 条基金数据", len(funds))
        except sqlite3.Error as exc:
            logger.error("保存基金数据失败: %s", exc)
            conn.rollback()
        finally:
            conn.close()

    def get_funds(self, index_type: str = "all") -> List[Dict]:
        """查询基金数据。

        Args:
            index_type: 指数类型过滤，'all' 表示不过滤，'自选' 表示仅获取自选基金。

        Returns:
            基金字典列表。
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            if index_type == "all":
                cursor.execute("SELECT * FROM funds ORDER BY index_type, code")
            elif index_type == "自选":
                cursor.execute("SELECT * FROM funds WHERE is_custom = 1 ORDER BY code")
            else:
                cursor.execute(
                    "SELECT * FROM funds WHERE index_type = ? ORDER BY code",
                    (index_type,),
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("查询基金数据失败: %s", exc)
            return []
        finally:
            conn.close()

    def get_history(self, code: str, limit: int = 30) -> List[Dict]:
        """获取某基金的历史净值记录。

        Args:
            code: 基金代码。
            limit: 返回最近 N 条记录，默认 30。

        Returns:
            历史净值字典列表（按日期倒序）。
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM nav_history WHERE code = ? "
                "ORDER BY nav_date DESC LIMIT ?",
                (code, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("查询历史净值失败 [%s]: %s", code, exc)
            return []
        finally:
            conn.close()

    def get_last_update_time(self) -> str:
        """返回最后一次更新时间的字符串。

        Returns:
            格式如 '2026-07-03 14:30:00'，无数据时返回 '暂无数据'。
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(updated_at) AS last_update FROM funds")
            row = cursor.fetchone()
            if row and row["last_update"]:
                return row["last_update"]
            return "暂无数据"
        except sqlite3.Error as exc:
            logger.error("查询更新时间失败: %s", exc)
            return "暂无数据"
        finally:
            conn.close()

    # ----------------------------------------------------------
    # 数据源状态
    # ----------------------------------------------------------

    def update_source_status(self, source_name: str, success: bool = True):
        """更新数据源的健康状态。

        Args:
            source_name: 数据源名称。
            success: 本次请求是否成功。
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if success:
                cursor.execute("""
                    INSERT INTO source_status (source_name, last_success, fail_count, is_available)
                    VALUES (?, ?, 0, 1)
                    ON CONFLICT(source_name) DO UPDATE SET
                        last_success = ?,
                        fail_count = 0,
                        is_available = 1
                """, (source_name, now, now))
            else:
                cursor.execute("""
                    INSERT INTO source_status (source_name, last_failure, fail_count, is_available)
                    VALUES (?, ?, 1, 1)
                    ON CONFLICT(source_name) DO UPDATE SET
                        last_failure = ?,
                        fail_count = fail_count + 1,
                        is_available = CASE WHEN fail_count + 1 >= 5 THEN 0 ELSE 1 END
                """, (source_name, now, now))

            conn.commit()
        except sqlite3.Error as exc:
            logger.error("更新数据源状态失败 [%s]: %s", source_name, exc)
        finally:
            conn.close()

    # ----------------------------------------------------------
    # 维护操作
    # ----------------------------------------------------------

    def clear_funds(self, keep_custom=True):
        """清空 funds 表（不影响 nav_history）。"""
        conn = self._get_conn()
        try:
            if keep_custom:
                conn.execute("DELETE FROM funds WHERE is_custom = 0")
            else:
                conn.execute("DELETE FROM funds")
            conn.commit()
            logger.info("funds 表已清空")
        except sqlite3.Error as exc:
            logger.error("清空 funds 表失败: %s", exc)
        finally:
            conn.close()
