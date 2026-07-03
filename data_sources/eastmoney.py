# -*- coding: utf-8 -*-
"""
天天基金数据源 - 场外指数基金数据获取工具（主数据源）

通过 EastMoney 多个 API 获取场外指数基金数据：
1. fundcode_search.js  —— 全量基金代码列表
2. lsjz API            —— 最新净值 / 历史净值
3. LJSYLK API          —— 成立来收益率
4. jbgk 详情页         —— 申购限额

只保留基金类型包含"指数"或"QDII"的基金，排除混合型。
"""

import json
import re
import logging
from typing import List, Dict, Optional, Callable

from config import (
    INDEX_KEYWORDS,
    INDEX_FUND_TYPES,
    EXCLUDED_FUND_TYPES,
    EASTMONEY_CONFIG,
)
from anti_block import requester
from data_sources.base import BaseDataSource

logger = logging.getLogger(__name__)


class EastMoneyDataSource(BaseDataSource):
    """天天基金（EastMoney）主数据源。"""

    def get_source_name(self) -> str:
        return "天天基金"

    def is_available(self) -> bool:
        """尝试请求基金列表 JS 文件，判断服务是否可达。"""
        try:
            resp = requester.get(
                EASTMONEY_CONFIG["fund_list_url"],
                referer=EASTMONEY_CONFIG["referer"],
            )
            return resp.status_code == 200 and len(resp.text) > 100
        except Exception as exc:
            logger.warning("天天基金不可达: %s", exc)
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
                progress_callback(idx, total, f"正在获取 {name}({code}) 数据...")
                
            fund_data = self._fetch_fund_detail(code, name, idx_type)
            if fund_data:
                results.append(fund_data)
                
        return results

    def fetch_fund_list(
        self,
        index_type: str = "all",
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """获取指数基金列表及其详细数据。

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
            logger.error("未能获取到基金代码列表")
            return []

        # ---------- Step 2: 按关键词 + 类型过滤 ----------
        if progress_callback:
            progress_callback(0, 0, "正在过滤指数基金...")

        matched = self._filter_index_funds(all_records, index_type)
        if not matched:
            logger.warning("未匹配到任何指数基金")
            return []

        logger.info("共匹配到 %d 只指数基金", len(matched))

        # ---------- Step 3-5: 逐只获取详细数据 ----------
        results: List[Dict] = []
        total = len(matched)

        for idx, (code, name, idx_type) in enumerate(matched, start=1):
            if progress_callback:
                progress_callback(idx, total, f"正在获取 {name}({code}) 的数据...")

            fund_data = self._fetch_fund_detail(code, name, idx_type)
            if fund_data:
                results.append(fund_data)

        logger.info("成功获取 %d 只基金的详细数据", len(results))
        return results

    # ===========================================================
    # Step 1 - 获取基金代码列表
    # ===========================================================

    def _fetch_fund_code_list(self) -> list:
        """从 fundcode_search.js 解析全量基金代码列表。

        响应格式:
            var r = [["000001","HXCZHH","华夏成长混合","混合型-偏股","HUAXIACHENGZHANGHUNHE"],...]

        Returns:
            二维列表，每条记录 [代码, 拼音缩写, 名称, 类型, 拼音全称]。
        """
        try:
            resp = requester.get(
                EASTMONEY_CONFIG["fund_list_url"],
                referer=EASTMONEY_CONFIG["referer"],
            )
            text = resp.text.strip()

            # 去掉 'var r = ' 前缀和 ';' 后缀
            if text.startswith("var r"):
                text = text.split("=", 1)[1].strip()
            if text.endswith(";"):
                text = text[:-1].strip()

            records = json.loads(text)
            logger.info("获取到 %d 条基金记录", len(records))
            return records
        except Exception as exc:
            logger.error("解析基金代码列表失败: %s", exc)
            return []

    # ===========================================================
    # Step 2 - 过滤指数基金
    # ===========================================================

    def _filter_index_funds(
        self, records: list, index_type: str
    ) -> List[tuple]:
        """根据关键词和基金类型过滤指数基金。

        过滤规则：
        1. 基金名称必须包含 INDEX_KEYWORDS 中的至少一个关键词
        2. 基金类型必须包含"指数"或"QDII"（在 INDEX_FUND_TYPES 中）
        3. 基金类型不能包含"混合"（在 EXCLUDED_FUND_TYPES 中）

        Args:
            records: 全量基金记录。
            index_type: 过滤类型，'all' 表示全部。

        Returns:
            匹配列表: [(code, name, index_type), ...]
        """
        matched: Dict[str, tuple] = {}  # code -> (code, name, idx_type)  去重用

        # 确定要搜索的关键词范围
        if index_type == "all":
            search_map = INDEX_KEYWORDS
        elif index_type in INDEX_KEYWORDS:
            search_map = {index_type: INDEX_KEYWORDS[index_type]}
        else:
            logger.warning("未知指数类型: %s", index_type)
            return []

        for record in records:
            if not isinstance(record, (list, tuple)) or len(record) < 5:
                continue

            code = record[0]
            name = record[2]
            fund_type = record[3]

            # ---- 类型过滤 ----
            # 排除包含"混合"的基金类型
            if any(excluded in fund_type for excluded in EXCLUDED_FUND_TYPES):
                continue
            if "混合" in fund_type:
                continue

            # 只保留包含"指数"或"QDII"的基金类型
            type_ok = any(
                allowed in fund_type for allowed in INDEX_FUND_TYPES
            )
            if not type_ok:
                continue

            # 过滤场内 ETF（名称中包含 "ETF" 但不包含 "联接" 的通常是场内基金）
            if "ETF" in name.upper() and "联接" not in name:
                continue

            # ---- 关键词匹配 ----
            for idx_type, keywords in search_map.items():
                for kw in keywords:
                    if kw.upper() in name.upper():
                        if code not in matched:
                            matched[code] = (code, name, idx_type)
                        break  # 同一 idx_type 命中即停

        return list(matched.values())

    # ===========================================================
    # Step 3 - 获取基金详细数据（净值 + 收益 + 限额）
    # ===========================================================

    def _fetch_fund_detail(
        self, code: str, name: str, idx_type: str
    ) -> Optional[Dict]:
        """获取单只基金的完整数据。

        依次调用：净值 API → 收益 API → 限额页面。
        任何子步骤失败不影响其他步骤。

        Returns:
            标准基金字典，或 None（净值获取失败时）。
        """
        # ---- 净值数据（必须成功） ----
        nav_info = self._fetch_nav(code)
        if nav_info is None:
            logger.warning("跳过 %s(%s): 无法获取净值", name, code)
            return None

        # ---- 成立来收益率（允许失败） ----
        since_inception = self._fetch_since_inception(code)

        # ---- 申购限额（允许失败） ----
        purchase_limit = self._fetch_purchase_limit(code)

        return self._create_fund_dict(
            code=code,
            name=name,
            index_type=idx_type,
            nav=nav_info.get("nav"),
            nav_date=nav_info.get("nav_date", ""),
            acc_nav=nav_info.get("acc_nav"),
            daily_change=nav_info.get("daily_change"),
            daily_change_pct=nav_info.get("daily_change_pct"),
            since_inception=since_inception,
            purchase_limit=purchase_limit,
            purchase_status=nav_info.get("purchase_status", ""),
        )

    # ===========================================================
    # Step 3a - 获取净值
    # ===========================================================

    def _fetch_nav(self, code: str) -> Optional[Dict]:
        """通过 lsjz API 获取最新净值及日涨跌。

        使用 pageSize=2 获取最近两个净值日数据，用于计算日涨跌额。

        Returns:
            dict with nav/nav_date/acc_nav/daily_change/daily_change_pct/purchase_status
            或 None。
        """
        try:
            resp = requester.get(
                EASTMONEY_CONFIG["fund_nav_url"],
                params={"fundCode": code, "pageIndex": 1, "pageSize": 2},
                referer=EASTMONEY_CONFIG["referer"],
            )
            data = resp.json()

            if data.get("ErrCode") != 0:
                logger.warning("lsjz API 错误 [%s]: ErrCode=%s", code, data.get("ErrCode"))
                return None

            nav_list = data.get("Data", {}).get("LSJZList", [])
            if not nav_list:
                return None

            latest = nav_list[0]
            nav = self._safe_float(latest.get("DWJZ"))
            acc_nav = self._safe_float(latest.get("LJJZ"))
            daily_change_pct = self._safe_float(latest.get("JZZZL"))

            # 计算日涨跌额: 当日净值 - 前日净值
            daily_change = None
            if len(nav_list) >= 2 and nav is not None:
                prev_nav = self._safe_float(nav_list[1].get("DWJZ"))
                if prev_nav is not None:
                    daily_change = round(nav - prev_nav, 4)

            return {
                "nav": nav,
                "nav_date": latest.get("FSRQ", ""),
                "acc_nav": acc_nav,
                "daily_change": daily_change,
                "daily_change_pct": daily_change_pct,
                "purchase_status": latest.get("SGZT", ""),
            }

        except Exception as exc:
            logger.error("获取净值失败 [%s]: %s", code, exc)
            return None

    # ===========================================================
    # Step 4 - 获取成立来收益
    # ===========================================================

    def _fetch_since_inception(self, code: str) -> Optional[str]:
        """通过 LJSYLK API 获取成立来收益率。

        Returns:
            收益率字符串（如 '123.45%'），获取失败返回 None。
        """
        try:
            resp = requester.get(
                EASTMONEY_CONFIG["fund_perf_url"],
                params={
                    "fundCode": code,
                    "indexcode": "000300",
                    "type": "se",
                },
                referer=EASTMONEY_CONFIG["referer"],
            )
            data = resp.json()

            # 尝试多种响应结构
            # 结构1: {"Data": [{"syl": "123.45"}, ...]}  最后一条为成立来
            if "Data" in data and isinstance(data["Data"], list):
                for item in reversed(data["Data"]):
                    if isinstance(item, dict):
                        syl = item.get("syl")
                        if syl is not None and syl != "":
                            return f"{syl}%"

            # 结构2: {"Datas": [...]}
            if "Datas" in data and isinstance(data["Datas"], list):
                datas = data["Datas"]
                if datas:
                    last = datas[-1] if isinstance(datas[-1], dict) else {}
                    syl = last.get("syl") or last.get("data")
                    if syl is not None and syl != "":
                        return f"{syl}%"

            return None
        except Exception as exc:
            logger.debug("获取成立来收益失败 [%s]: %s", code, exc)
            return None

    # ===========================================================
    # Step 5 - 获取申购限额
    # ===========================================================

    def _fetch_purchase_limit(self, code: str) -> str:
        """从基金详情页解析完整的交易状态（包括限额等信息）。

        Returns:
            完整的交易状态字符串，获取失败返回空字符串。
        """
        try:
            url = EASTMONEY_CONFIG["fund_detail_url"].format(code=code)
            resp = requester.get(url, referer=EASTMONEY_CONFIG["referer"])
            resp.encoding = "utf-8"
            html = resp.text

            # 直接提取带有详细状态和限额的 label 内容
            match = re.search(r'<label>.*?交易状态：(.*?)</label>', html, re.DOTALL)
            if match:
                raw_text = match.group(1)
                clean_text = re.sub(r'<[^>]+>', '', raw_text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                clean_text = clean_text.replace("&nbsp;", " ")
                return clean_text

            return ""
        except Exception as exc:
            logger.debug("获取交易状态失败 [%s]: %s", code, exc)
            return ""

    # ===========================================================
    # 工具方法
    # ===========================================================

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """安全地将值转为 float，失败返回 None。"""
        if value is None or value == "" or value == "--":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
