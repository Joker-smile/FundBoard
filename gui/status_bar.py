"""
状态栏组件

显示应用运行状态、数据源、更新时间、基金统计等信息。
支持不同状态类型的颜色区分（info/success/error/warning）。
"""

import tkinter as tk
from tkinter import ttk

from config import APP_SETTINGS


class StatusBar(ttk.Frame):
    """底部状态栏组件"""

    STATUS_ICONS = {
        "info": "ℹ️",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
    }

    STATUS_COLORS = {
        "info": "#3498db",
        "success": "#27ae60",
        "error": "#e74c3c",
        "warning": "#f39c12",
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self._setup_ui()

    def _setup_ui(self):
        """构建状态栏界面"""
        # 外层容器，添加顶部分隔线效果
        self.configure(padding=(8, 4))

        # --- 状态文字 ---
        self.status_var = tk.StringVar(value="✅ 就绪")
        self.status_label = ttk.Label(
            self,
            textvariable=self.status_var,
            font=("Microsoft YaHei", 9),
            width=30,
            anchor="w",
        )
        self.status_label.pack(side=tk.LEFT, padx=(0, 6))

        # 分隔符
        self._add_separator()

        # --- 数据源 ---
        self.source_var = tk.StringVar(value="数据源: --")
        ttk.Label(
            self,
            textvariable=self.source_var,
            font=("Microsoft YaHei", 9),
            anchor="center",
        ).pack(side=tk.LEFT, padx=6)

        self._add_separator()

        # --- 更新时间 ---
        self.update_time_var = tk.StringVar(value="上次更新: --")
        ttk.Label(
            self,
            textvariable=self.update_time_var,
            font=("Microsoft YaHei", 9),
            anchor="center",
        ).pack(side=tk.LEFT, padx=6)

        self._add_separator()

        # --- 基金数量 ---
        self.fund_count_var = tk.StringVar(value="共 0 只基金")
        ttk.Label(
            self,
            textvariable=self.fund_count_var,
            font=("Microsoft YaHei", 9),
            anchor="center",
        ).pack(side=tk.LEFT, padx=6)

        self._add_separator()

        # --- 平均日增长率 ---
        self.avg_change_var = tk.StringVar(value="平均日增长: --")
        self.avg_change_label = ttk.Label(
            self,
            textvariable=self.avg_change_var,
            font=("Microsoft YaHei", 9),
            anchor="center",
        )
        self.avg_change_label.pack(side=tk.LEFT, padx=6)

        # --- 版本号（右侧） ---
        version = APP_SETTINGS.get("version", "1.0.0")
        ttk.Label(
            self,
            text=f"v{version}",
            font=("Microsoft YaHei", 8),
            foreground="#888888",
            anchor="e",
        ).pack(side=tk.RIGHT, padx=(6, 0))

    def _add_separator(self):
        """添加竖直分隔符"""
        sep = ttk.Separator(self, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)

    # === 公共方法 ===

    def set_status(self, text: str, status_type: str = "info"):
        """
        设置状态文字。

        Args:
            text: 状态文字内容
            status_type: 状态类型 (info/success/error/warning)
        """
        icon = self.STATUS_ICONS.get(status_type, "ℹ️")
        self.status_var.set(f"{icon} {text}")

        # 尝试设置颜色
        color = self.STATUS_COLORS.get(status_type, "")
        try:
            self.status_label.configure(foreground=color)
        except tk.TclError:
            pass

    def set_source(self, name: str):
        """设置当前数据源名称"""
        self.source_var.set(f"数据源: {name}")

    def set_update_time(self, time_str: str):
        """设置更新时间"""
        self.update_time_var.set(f"上次更新: {time_str}")

    def set_fund_count(self, count: int):
        """设置基金数量"""
        self.fund_count_var.set(f"共 {count} 只基金")

    def set_avg_change(self, pct: float):
        """设置平均日增长率"""
        if pct is None:
            self.avg_change_var.set("平均日增长: --")
            try:
                self.avg_change_label.configure(foreground="")
            except tk.TclError:
                pass
            return

        sign = "+" if pct >= 0 else ""
        self.avg_change_var.set(f"平均日增长: {sign}{pct:.2f}%")

        # 涨跌颜色
        try:
            if pct > 0:
                self.avg_change_label.configure(foreground="#e74c3c")
            elif pct < 0:
                self.avg_change_label.configure(foreground="#27ae60")
            else:
                self.avg_change_label.configure(foreground="")
        except tk.TclError:
            pass

    def show_progress(self, current: int, total: int, message: str = ""):
        """
        显示进度信息。

        Args:
            current: 当前进度
            total: 总数
            message: 附加消息
        """
        if total > 0:
            pct = current / total * 100
            progress_text = f"⏳ [{current}/{total}] {pct:.0f}% {message}"
        else:
            progress_text = f"⏳ {message}"

        self.status_var.set(progress_text)
        try:
            self.status_label.configure(foreground="#3498db")
        except tk.TclError:
            pass
