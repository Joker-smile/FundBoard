# -*- coding: utf-8 -*-
"""
蚂蚁基金数据源（备用） - 场外指数基金数据获取工具

使用蛋卷基金 (DanJuan / 雪球旗下) 的 API 获取基金详细数据。
基金代码列表复用天天基金的 fundcode_search.js，然后通过蛋卷
API 逐只获取净值和详情。

只保留基金类型包含"指数"或"QDII"的基金，排除混合型。
"""

import json
import logging
from typing import List, Dict, Optional, Callable

from config import (
    INDEX_KEYWORDS,
    INDEX_FUND_TYPES,
    EXCLUDED_FUND_TYPES,
    EASTMONEY_CONFIG,
    DANJUAN_CONFIG,
)
from anti_block import requester
from data_sources.base import BaseDataSource

logger = logging.getLogger(__name__)


class AntFundDataSource(BaseDataSource):
    """蚂蚁基金数据源（使用蛋卷基金API实现）。"""

    def get_source_name(self) -> str:
        return "蚂蚁基金"

    def is_available(self) -> bool:
        """检查蛋卷基金 API 是否可达。"""
        try:
            # 用一只常见基金测试 API 可用性
            test_url = DANJUAN_CONFIG["fund_detail_url"].format(code="110011")
            resp = requester.get(test_url, referer=DANJUAN_CONFIG["referer"])
            data = resp.json()
            # 蛋卷 API 正常响应包含 data 或 result_code 字段
            return resp.status_code == 200 and (
                "data" in data or "result_code" in data
            )
        except Exception as exc:
            logger.warning("蚂蚁基金数据源不可达: %s", exc)
            return False

    # ===========================================================
    # 公开接口
    # ===========================================================

    def fetch_specific_funds(
        self,
        funds: List[Dict],
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """获取指定基金的最新详细数据。"""
        results: List[Dict] = []
        total = len(funds)
        
        for idx, fund in enumerate(funds, start=1):
            code = fund.get("code", "")
            name = fund.get("name", "")
            idx_type = fund.get("index_type", "")
            if progress_callback:
                progress_callback(
                    idx, total,
                    f"[蚂蚁] 正在更新 {name}({code}) 数据...",
                )
                
            fund_data = self._fetch_danjuan_detail(code, name, idx_type)
            if fund_data:
                results.append(fund_data)
                
        return results

    def fetch_fund_list(
        self,
        index_type: str = "all",
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """获取指数基金列表。

        流程：
        1. 复用天天基金的 fundcode_search.js 获取全量基金代码
        2. 按关键词 + 类型过滤指数基金
        3. 通过蛋卷 API 逐只获取详细数据

        Args:
            index_type: 'all' | '纳指' | '标普' | '道指'
            progress_callback: callback(current, total, message)

        Returns:
            标准化基金字典列表。
        """
        # ---------- Step 1: 获取全量代码列表 ----------
        if progress_callback:
            progress_callback(0, 0, "正在获取基金代码列表...")

        all_records = self._fetch_fund_code_list()
        if not all_records:
            logger.error("蚂蚁基金: 未能获取到基金代码列表")
            return []

        # ---------- Step 2: 按关键词 + 类型过滤 ----------
        if progress_callback:
            progress_callback(0, 0, "正在过滤指数基金...")

        matched = self._filter_index_funds(all_records, index_type)
        if not matched:
            logger.warning("蚂蚁基金: 未匹配到任何指数基金")
            return []

        logger.info("蚂蚁基金: 共匹配到 %d 只指数基金", len(matched))

        # ---------- Step 3: 逐只获取详细数据 ----------
        results: List[Dict] = []
        total = len(matched)

        for idx, (code, name, idx_type) in enumerate(matched, start=1):
            if progress_callback:
                progress_callback(
                    idx, total,
                    f"[蚂蚁基金] 正在获取 {name}({code}) 的数据...",
                )

            fund_data = self._fetch_danjuan_detail(code, name, idx_type)
            if fund_data:
                results.append(fund_data)

        logger.info("蚂蚁基金: 成功获取 %d 只基金的详细数据", len(results))
        return results

    # ===========================================================
    # Step 1 - 获取基金代码列表（复用天天基金）
    # ===========================================================

    def _fetch_fund_code_list(self) -> list:
        """从天天基金的 fundcode_search.js 获取全量基金代码列表。"""
        try:
            resp = requester.get(
                EASTMONEY_CONFIG["fund_list_url"],
                referer=EASTMONEY_CONFIG["referer"],
            )
            text = resp.text.strip()

            if text.startswith("var r"):
                text = text.split("=", 1)[1].strip()
            if text.endswith(";"):
                text = text[:-1].strip()

            records = json.loads(text)
            logger.info("蚂蚁基金: 获取到 %d 条基金记录", len(records))
            return records
        except Exception as exc:
            logger.error("蚂蚁基金: 解析基金代码列表失败: %s", exc)
            return []

    # ===========================================================
    # Step 2 - 过滤指数基金（逻辑同 EastMoney）
    # ===========================================================

    def _filter_index_funds(
        self, records: list, index_type: str
    ) -> List[tuple]:
        """根据关键词和基金类型过滤指数基金或海外主动基金。

        过滤规则同 EastMoneyDataSource。
        """
        matched: Dict[str, tuple] = {}

        if index_type == "all":
            search_map = INDEX_KEYWORDS
        elif index_type in INDEX_KEYWORDS:
            search_map = {index_type: INDEX_KEYWORDS[index_type]}
        else:
            logger.warning("蚂蚁基金: 未知指数类型: %s", index_type)
            return []

        for record in records:
            if not isinstance(record, (list, tuple)) or len(record) < 5:
                continue

            code = record[0]
            name = record[2]
            fund_type = record[3]

            is_index_type = "指数" in fund_type or "指数" in name or ("ETF" in name.upper() and "联接" not in name)

            # 关键词与分类匹配
            for idx_type, keywords in search_map.items():
                if idx_type == "海外主动":
                    is_qdii_or_overseas = (
                        "QDII" in fund_type
                        or "QDII" in name.upper()
                        or any(kw.upper() in name.upper() for kw in keywords)
                    )
                    if is_qdii_or_overseas and not is_index_type:
                        if code not in matched:
                            matched[code] = (code, name, idx_type)
                        break
                else:
                    if "混合" in fund_type and "QDII" not in fund_type:
                        continue

                    type_ok = any(allowed in fund_type for allowed in INDEX_FUND_TYPES)
                    if not type_ok:
                        continue
                    if "ETF" in name.upper() and "联接" not in name:
                        continue

                    for kw in keywords:
                        if kw.upper() in name.upper():
                            if code not in matched:
                                matched[code] = (code, name, idx_type)
                            break

        return list(matched.values())

    # ===========================================================
    # Step 3 - 蛋卷 API 获取详细数据
    # ===========================================================

    def _fetch_danjuan_detail(
        self, code: str, name: str, idx_type: str
    ) -> Optional[Dict]:
        """通过蛋卷基金 API 获取单只基金数据。

        蛋卷 API 响应结构示例:
        {
            "data": {
                "fd_code": "270042",
                "fd_name": "广发纳斯达克100指数",
                "fund_derived": {
                    "unit_nav": "5.1234",
                    "unit_nav_date": 1719763200000,
                    "nav_grtd": "-1.23",
                    "nav_grinc": "-0.0638",
                    ...
                },
                "fund_nav_info": {
                    "nav": "5.1234",
                    "nav_date": "2026-07-01",
                    ...
                }
            },
            "result_code": 0
        }

        Returns:
            标准基金字典，或 None。
        """
        try:
            url = DANJUAN_CONFIG["fund_detail_url"].format(code=code)
            resp = requester.get(url, referer=DANJUAN_CONFIG["referer"])
            body = resp.json()

            data = body.get("data")
            if not data:
                logger.warning("蛋卷API无数据 [%s]", code)
                return None

            # 解析净值信息
            derived = data.get("fund_derived", {}) or {}
            nav_info = data.get("fund_nav_info", {}) or {}

            nav = self._safe_float(
                derived.get("unit_nav") or nav_info.get("nav")
            )
            acc_nav = self._safe_float(
                derived.get("totol_nav") or nav_info.get("accnav")
            )

            # 日涨跌
            daily_change_pct = self._safe_float(derived.get("nav_grtd"))
            daily_change = self._safe_float(derived.get("nav_grinc"))

            # 净值日期
            nav_date = nav_info.get("nav_date", "")
            if not nav_date:
                # 从时间戳转换
                ts = derived.get("unit_nav_date")
                if ts:
                    try:
                        import datetime
                        nav_date = datetime.datetime.fromtimestamp(
                            int(ts) / 1000
                        ).strftime("%Y-%m-%d")
                    except Exception:
                        nav_date = ""

            # 成立来收益
            since_inception = None
            inception_val = derived.get("inception_growth")
            if inception_val is not None and inception_val != "":
                try:
                    since_inception = f"{float(inception_val) * 100:.2f}%"
                except (ValueError, TypeError):
                    since_inception = None

            # 申购状态
            purchase_status = data.get("fund_buy_info", {}).get("buy_status_desc", "")
            if not purchase_status:
                purchase_status = ""

            # 申购限额
            purchase_limit = ""
            buy_info = data.get("fund_buy_info", {}) or {}
            limit_val = buy_info.get("day_buy_limit")
            if limit_val:
                purchase_limit = str(limit_val)

            return self._create_fund_dict(
                code=code,
                name=name,
                index_type=idx_type,
                nav=nav,
                nav_date=nav_date,
                acc_nav=acc_nav,
                daily_change=daily_change,
                daily_change_pct=daily_change_pct,
                since_inception=since_inception,
                purchase_limit=purchase_limit,
                purchase_status=purchase_status,
            )

        except Exception as exc:
            logger.warning("蛋卷API请求失败 [%s]: %s", code, exc)
            # 蛋卷 API 失败时返回 None，不阻塞整体流程
            return None

    # ===========================================================
    # 工具方法
    # ===========================================================

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """安全地将值转为 float，失败返回 None。"""
        if value is None or value == "" or value == "--":
            return None
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            return None
