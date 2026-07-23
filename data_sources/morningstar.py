# -*- coding: utf-8 -*-
"""
晨星数据源（备用） - 场外指数基金数据获取工具

使用天天基金的 rankhandler 排行 API 批量获取基金数据，
作为主数据源的备选方案。数据获取效率更高（单次请求批量返回），
但字段精度略低。

只保留基金类型包含"指数"或"QDII"的基金，排除混合型。
"""

import json
import re
import logging
from typing import List, Dict, Optional, Callable

from config import (
    INDEX_KEYWORDS,
    EXCLUDED_FUND_TYPES,
    TIANTIAN_FUND_CONFIG,
)
from anti_block import requester
from data_sources.base import BaseDataSource

logger = logging.getLogger(__name__)


class MorningstarDataSource(BaseDataSource):
    """晨星数据源（实际使用天天基金排行API实现）。"""

    def get_source_name(self) -> str:
        return "晨星数据"

    def is_available(self) -> bool:
        """检查排行 API 是否可达。"""
        try:
            resp = requester.get(
                TIANTIAN_FUND_CONFIG["fund_rank_url"],
                params={
                    "op": "ph", "dt": "kf", "ft": "gp",
                    "rs": "", "gs": "0", "sc": "zzf", "st": "desc",
                    "pi": "1", "pn": "1", "dx": "1",
                },
                referer=TIANTIAN_FUND_CONFIG["referer"],
            )
            return resp.status_code == 200 and "datas" in resp.text
        except Exception as exc:
            logger.warning("晨星数据源不可达: %s", exc)
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
        if not funds:
            return []
            
        if progress_callback:
            progress_callback(0, 0, "[晨星] 正在重新获取排行数据...")
            
        all_raw = []
        fund_type_params = [
            ("gp", "股票型"),
            ("zq", "债券型"),
            ("qdii", "QDII"),
        ]
        
        for ft_code, ft_name in fund_type_params:
            if progress_callback:
                progress_callback(0, 0, f"[晨星] 正在获取{ft_name}榜单...")
            raw = self._fetch_rank_data(ft_code)
            if raw:
                all_raw.extend(raw)
                
        if not all_raw:
            return []
            
        target_codes = {f["code"]: f for f in funds}
        results = []
        
        for item in all_raw:
            fields = item.split(",")
            if len(fields) < 23:
                continue
            code = fields[0].strip()
            
            if code in target_codes:
                name = fields[1].strip()
                nav = self._safe_float(fields[4])
                acc_nav = self._safe_float(fields[5])
                daily_pct = self._safe_float(fields[6])
                since_inception = fields[14].strip() if len(fields) > 14 else ""
                purchase_status = fields[22].strip() if len(fields) > 22 else ""
                nav_date = fields[3].strip()
                
                daily_change = None
                if nav is not None and daily_pct is not None:
                    try:
                        daily_change = round(nav * daily_pct / (100 + daily_pct), 4)
                    except ZeroDivisionError:
                        daily_change = None
                        
                since_str = None
                if since_inception and since_inception not in ("", "--"):
                    since_str = f"{since_inception}%"
                    
                fund_data = self._create_fund_dict(
                    code=code,
                    name=name,
                    index_type=target_codes[code].get("index_type", ""),
                    nav=nav,
                    nav_date=nav_date,
                    acc_nav=acc_nav,
                    daily_change=daily_change,
                    daily_change_pct=daily_pct,
                    since_inception=since_str,
                    purchase_status=purchase_status,
                )
                results.append(fund_data)
                if len(results) == len(target_codes):
                    break
                    
        return results

    def fetch_fund_list(
        self,
        index_type: str = "all",
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """通过排行API批量获取指数基金数据。

        Args:
            index_type: 'all' | '纳指' | '标普' | '道指'
            progress_callback: callback(current, total, message)

        Returns:
            标准化基金字典列表。
        """
        if progress_callback:
            progress_callback(0, 0, "正在从晨星数据源获取数据...")

        # ---- 分批请求不同基金类型 ----
        all_raw = []
        fund_type_params = [
            ("gp", "股票型"),   # 包含指数型-股票
            ("zq", "债券型"),   # 包含指数型-债券
            ("qdii", "QDII"),   # 包含 QDII-指数与QDII主动
        ]

        for ft_code, ft_name in fund_type_params:
            if progress_callback:
                progress_callback(0, 0, f"正在获取{ft_name}基金排行数据...")

            raw = self._fetch_rank_data(ft_code)
            if raw:
                all_raw.extend(raw)
                logger.info("从 %s 类型获取到 %d 条记录", ft_name, len(raw))

        if not all_raw:
            logger.error("未能从排行API获取到任何数据")
            return []

        # ---- 过滤指数基金 ----
        if progress_callback:
            progress_callback(0, 0, "正在过滤指数基金...")

        results = self._filter_and_parse(all_raw, index_type)

        if progress_callback:
            progress_callback(len(results), len(results), f"共获取到 {len(results)} 只指数基金")

        logger.info("晨星数据源共获取 %d 只指数基金", len(results))
        return results

    # ===========================================================
    # 内部方法
    # ===========================================================

    def _fetch_rank_data(self, ft: str) -> List[str]:
        """请求 rankhandler API 获取原始数据行。

        Args:
            ft: 基金类型代码 (gp/zq/qq 等)。

        Returns:
            原始逗号分隔字符串列表。
        """
        try:
            resp = requester.get(
                TIANTIAN_FUND_CONFIG["fund_rank_url"],
                params={
                    "op": "ph",
                    "dt": "kf",
                    "ft": ft,
                    "rs": "",
                    "gs": "0",
                    "sc": "zzf",
                    "st": "desc",
                    "pi": "1",
                    "pn": "20000",
                    "dx": "1",
                },
                referer=TIANTIAN_FUND_CONFIG["referer"],
            )
            text = resp.text

            # 解析 JSONP: var rankData = {datas:["...","..."],allRecords:N,...}
            # 提取 datas 数组
            datas_match = re.search(r'datas:\[(.*?)\]', text, re.DOTALL)
            if not datas_match:
                logger.warning("rankhandler 响应中未找到 datas 字段 (ft=%s)", ft)
                return []

            datas_str = datas_match.group(1)
            # 每条数据用双引号包裹，逗号分隔
            items = re.findall(r'"([^"]*)"', datas_str)
            return items

        except Exception as exc:
            logger.error("请求排行API失败 (ft=%s): %s", ft, exc)
            return []

    def _filter_and_parse(
        self, raw_items: List[str], index_type: str
    ) -> List[Dict]:
        """过滤并解析原始数据行。

        字段位置（逗号分隔）:
        [0]=code, [1]=name, [2]=pinyin, [3]=nav_date, [4]=dwjz,
        [5]=ljjz, [6]=daily_pct%, ..., [14]=since_inception%,
        ..., [20]=fee, ..., [22]=purchase_status

        Returns:
            标准化基金字典列表。
        """
        # 确定要搜索的关键词范围
        if index_type == "all":
            search_map = INDEX_KEYWORDS
        elif index_type in INDEX_KEYWORDS:
            search_map = {index_type: INDEX_KEYWORDS[index_type]}
        else:
            return []

        seen: Dict[str, bool] = {}
        results: List[Dict] = []

        for item in raw_items:
            fields = item.split(",")
            if len(fields) < 23:
                continue

            code = fields[0].strip()
            name = fields[1].strip()

            # ---- 去重 ----
            if code in seen:
                continue

            name_upper = name.upper()
            is_index_type = "指数" in name or ("ETF" in name_upper and "联接" not in name)

            # ---- 关键词匹配 ----
            matched_type = None
            for idx_type, keywords in search_map.items():
                if idx_type == "海外主动":
                    is_qdii_or_overseas = (
                        "QDII" in name_upper
                        or any(kw.upper() in name_upper for kw in keywords)
                    )
                    if is_qdii_or_overseas and not is_index_type:
                        matched_type = idx_type
                        break
                else:
                    if "混合" in name and "QDII" not in name_upper:
                        continue
                    for kw in keywords:
                        if kw.upper() in name_upper:
                            matched_type = idx_type
                            break
                if matched_type:
                    break

            if not matched_type:
                continue

            seen[code] = True

            # ---- 解析数值字段 ----
            nav = self._safe_float(fields[4])
            acc_nav = self._safe_float(fields[5])
            daily_pct = self._safe_float(fields[6])
            since_inception = fields[14].strip() if len(fields) > 14 else ""
            purchase_status = fields[22].strip() if len(fields) > 22 else ""
            nav_date = fields[3].strip()

            # 计算日涨跌额
            daily_change = None
            if nav is not None and daily_pct is not None:
                try:
                    daily_change = round(nav * daily_pct / (100 + daily_pct), 4)
                except ZeroDivisionError:
                    daily_change = None

            # 格式化成立来收益
            since_str = None
            if since_inception and since_inception not in ("", "--"):
                since_str = f"{since_inception}%"

            fund = self._create_fund_dict(
                code=code,
                name=name,
                index_type=matched_type,
                nav=nav,
                nav_date=nav_date,
                acc_nav=acc_nav,
                daily_change=daily_change,
                daily_change_pct=daily_pct,
                since_inception=since_str,
                purchase_status=purchase_status,
            )
            results.append(fund)

        return results

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
