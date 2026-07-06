# -*- coding: utf-8 -*-
"""
配置文件 - 场外指数基金数据获取工具

包含所有常量配置：指数关键词映射、基金类型过滤、数据源API地址、
User-Agent池、应用设置等。
"""

import os
import json

# ============================================================
# 指数关键词映射
# key: 指数类型名称  value: 对应的搜索关键词列表
# ============================================================
INDEX_KEYWORDS = {
    "纳指": ["纳斯达克", "纳指100","纳指"],
    "标普": ["标普500", "标普"],
    "道指": ["道琼斯", "道指"],
}



# ============================================================
# 基金类型过滤
# ============================================================
# 允许的基金类型（只获取指数型基金）
INDEX_FUND_TYPES = ["指数型", "指数型-股票", "QDII", "QDII-指数"]

# 排除的基金类型（排除混合型基金）
EXCLUDED_FUND_TYPES = ["混合型", "混合型-偏股", "混合型-偏债", "混合型-灵活"]

# ============================================================
# 天天基金(EastMoney) API 配置
# ============================================================
EASTMONEY_CONFIG = {
    "fund_list_url": "http://fund.eastmoney.com/js/fundcode_search.js",
    "fund_nav_url": "https://api.fund.eastmoney.com/f10/lsjz",
    "fund_detail_url": "http://fundf10.eastmoney.com/jbgk_{code}.html",
    "fund_perf_url": "https://api.fund.eastmoney.com/pinzhong/LJSYLK",
    "referer": "https://fundf10.eastmoney.com/",
}

# ============================================================
# 蛋卷基金(DanJuan) API 配置 —— 第二数据源
# ============================================================
DANJUAN_CONFIG = {
    "fund_detail_url": "https://danjuanfunds.com/djapi/fund/detail/{code}",
    "fund_nav_url": "https://danjuanfunds.com/djapi/fund/nav/history/{code}",
    "referer": "https://danjuanfunds.com/",
}

# ============================================================
# 天天基金排行API 配置 —— 第三数据源
# ============================================================
TIANTIAN_FUND_CONFIG = {
    "fund_rank_url": "http://fund.eastmoney.com/data/rankhandler.aspx",
    "referer": "http://fund.eastmoney.com/data/fundranking.html",
}

# ============================================================
# User-Agent 池 —— 用于反封锁轮换
# ============================================================
USER_AGENTS = [
    # Chrome - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Chrome - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Firefox - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Edge - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    # Safari - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    # Safari - iOS
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    # Chrome - Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# ============================================================
# 应用全局设置
# ============================================================
APP_SETTINGS = {
    "title": "场外指数基金数据获取工具",
    "version": "1.0.0",
    "window_size": "1400x800",
    "min_size": (1200, 600),
    "request_delay_min": 0.3,
    "request_delay_max": 1.5,
    "max_retries": 3,
    "retry_backoff": 2,
    "request_timeout": 15,
    "auto_refresh_intervals": [5, 10, 30, 60],
    "db_file": "fund_data.db",
    "history_limit": 30,
}

import sys

# 获取运行根目录（兼容打包后的 exe 和直接运行的 py 脚本）
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

USER_CONFIG_FILE = os.path.join(BASE_DIR, "user_config.json")

def load_user_config():
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                user_conf = json.load(f)
            
            if "INDEX_KEYWORDS" in user_conf:
                INDEX_KEYWORDS.clear()
                INDEX_KEYWORDS.update(user_conf["INDEX_KEYWORDS"])
                
            if "APP_SETTINGS" in user_conf:
                APP_SETTINGS.update(user_conf["APP_SETTINGS"])
        except Exception as e:
            print(f"加载用户配置失败: {e}")

def save_user_config(keywords_dict, settings_dict):
    user_conf = {
        "INDEX_KEYWORDS": keywords_dict,
        "APP_SETTINGS": settings_dict
    }
    try:
        with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(user_conf, f, ensure_ascii=False, indent=4)
        # 更新内存中的配置
        INDEX_KEYWORDS.clear()
        INDEX_KEYWORDS.update(keywords_dict)
        APP_SETTINGS.update(settings_dict)
        return True
    except Exception as e:
        print(f"保存用户配置失败: {e}")
        return False

# 启动时自动加载配置
load_user_config()
