"""
场外指数基金数据获取工具 - 程序入口

启动 GUI 应用主窗口。
"""

import os
import sys

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import FundApp


def main():
    """程序主入口"""
    app = FundApp()
    app.run()


if __name__ == "__main__":
    main()
