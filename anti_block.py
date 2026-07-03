# -*- coding: utf-8 -*-
"""
反封锁模块 - 场外指数基金数据获取工具

提供 AntiBlockRequester 类，封装了以下反封锁策略：
- 随机 User-Agent 轮换
- 线程安全的请求限速（随机间隔）
- 指数退避重试机制
- Referer 伪装
- 常见浏览器请求头模拟
"""

import random
import threading
import time
import logging

import requests

from config import USER_AGENTS, APP_SETTINGS

logger = logging.getLogger(__name__)


class AntiBlockRequester:
    """带反封锁策略的 HTTP 请求器。

    所有 HTTP 请求都通过此类发出，自动附加随机 UA、限速、
    指数退避重试等保护机制，降低被数据源封禁的概率。
    """

    def __init__(self):
        """初始化请求器。

        创建 requests.Session 以复用 TCP 连接，初始化线程锁和
        上次请求时间戳用于限速控制。
        """
        self.session = requests.Session()
        self._lock = threading.Lock()
        self._last_request_time = 0.0

    # ----------------------------------------------------------
    # 内部方法
    # ----------------------------------------------------------

    def _get_random_ua(self) -> str:
        """随机返回一个 User-Agent 字符串。"""
        return random.choice(USER_AGENTS)

    def _wait_for_rate_limit(self):
        """线程安全的请求限速。

        确保两次请求之间至少间隔一个随机时间（在配置的
        request_delay_min 和 request_delay_max 之间），
        防止请求过于密集被服务器识别。
        """
        with self._lock:
            now = time.time()
            delay = random.uniform(
                APP_SETTINGS["request_delay_min"],
                APP_SETTINGS["request_delay_max"],
            )
            elapsed = now - self._last_request_time
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self._last_request_time = time.time()

    # ----------------------------------------------------------
    # 公开方法
    # ----------------------------------------------------------

    def get(self, url, params=None, headers=None, referer=None, **kwargs):
        """发送 GET 请求，附带反封锁策略。

        Args:
            url: 目标 URL。
            params: 查询参数字典。
            headers: 额外请求头（会与默认头合并，额外头优先）。
            referer: Referer 地址，用于伪装来源页面。
            **kwargs: 传递给 requests.Session.get 的其他参数。

        Returns:
            requests.Response: 响应对象。

        Raises:
            requests.RequestException: 经过所有重试仍然失败时抛出。
        """
        max_retries = APP_SETTINGS["max_retries"]
        backoff = APP_SETTINGS["retry_backoff"]
        timeout = kwargs.pop("timeout", APP_SETTINGS["request_timeout"])

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                # 限速等待
                self._wait_for_rate_limit()

                # 构建请求头 —— 每次重试都换 UA
                default_headers = {
                    "User-Agent": self._get_random_ua(),
                    "Accept": "text/html,application/xhtml+xml,application/xml;"
                              "q=0.9,application/json,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                }
                if referer:
                    default_headers["Referer"] = referer

                # 合并外部传入的 headers（外部优先）
                if headers:
                    default_headers.update(headers)

                response = self.session.get(
                    url,
                    params=params,
                    headers=default_headers,
                    timeout=timeout,
                    **kwargs,
                )
                response.raise_for_status()
                return response

            except requests.RequestException as exc:
                last_exception = exc
                if attempt < max_retries:
                    wait_time = backoff ** attempt + random.uniform(0.1, 0.5)
                    logger.warning(
                        "请求失败 [%s] (第%d/%d次重试，等待%.1fs): %s",
                        url, attempt + 1, max_retries, wait_time, exc,
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        "请求最终失败 [%s] 已重试%d次: %s",
                        url, max_retries, exc,
                    )

        raise last_exception  # type: ignore[misc]

    def close(self):
        """关闭底层 Session，释放连接池资源。"""
        try:
            self.session.close()
        except Exception:
            pass


# ============================================================
# 模块级全局实例 —— 整个应用共享同一个请求器
# ============================================================
requester = AntiBlockRequester()
