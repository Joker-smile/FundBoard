# -*- coding: utf-8 -*-
"""
数据源基类 - 场外指数基金数据获取工具

定义所有数据源必须实现的接口：
- get_source_name(): 返回数据源名称
- fetch_fund_list(): 获取基金列表
- is_available(): 检查数据源可用性

同时提供 _create_fund_dict() 工具方法，统一基金数据字典格式。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable


class BaseDataSource(ABC):
    """数据源抽象基类。

    所有数据源实现都必须继承此类并实现所有抽象方法。
    progress_callback 签名: callback(current: int, total: int, message: str)
    """

    @abstractmethod
    def get_source_name(self) -> str:
        """返回数据源的显示名称。"""
        ...

    @abstractmethod
    def fetch_fund_list(
        self,
        index_type: str = "all",
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """获取基金列表。

        Args:
            index_type: 指数类型过滤，'all' 返回全部类型。
                        可选值: 'all', '纳指', '标普', '道指'。
            progress_callback: 进度回调函数，签名为
                               callback(current: int, total: int, message: str)。

        Returns:
            标准化的基金字典列表。
        """
        ...

    @abstractmethod
    def fetch_specific_funds(
        self,
        funds: List[Dict],
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """获取指定基金列表的最新详细数据。

        Args:
            funds: 包含 'code', 'name', 'index_type' 的字典列表。
            progress_callback: 进度回调函数。

        Returns:
            更新后的标准基金字典列表。
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可达/可用。"""
        ...

    def _create_fund_dict(self, **kwargs) -> Dict:
        """创建标准化的基金数据字典。

        Args:
            **kwargs: 基金各字段值。

        Returns:
            统一格式的基金字典。
        """
        return {
            "code": kwargs.get("code", ""),
            "name": kwargs.get("name", ""),
            "index_type": kwargs.get("index_type", ""),
            "nav": kwargs.get("nav"),
            "nav_date": kwargs.get("nav_date", ""),
            "acc_nav": kwargs.get("acc_nav"),
            "daily_change": kwargs.get("daily_change"),
            "daily_change_pct": kwargs.get("daily_change_pct"),
            "since_inception": kwargs.get("since_inception"),
            "purchase_limit": kwargs.get("purchase_limit", ""),
            "purchase_status": kwargs.get("purchase_status", ""),
            "data_source": self.get_source_name(),
        }
