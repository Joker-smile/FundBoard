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

        # --- A股指数 ---
        self._add_separator()
        self.indices_frame = ttk.Frame(self)
        self.indices_frame.pack(side=tk.LEFT, padx=6)

        self.index_names = {
            "sh000001": "沪指",
            "sz399001": "深指",
            "sz399006": "创业",
            "sh000688": "科创50",
        }
        self.index_labels = {}
        for symbol, name in self.index_names.items():
            label = ttk.Label(
                self.indices_frame,
                text=f"{name}: -- (--%)",
                font=("Microsoft YaHei", 9),
            )
            label.pack(side=tk.LEFT, padx=8)
            self.index_labels[symbol] = label

        # 启动后台更新指数
        self.update_indices()

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

    def update_indices(self):
        """发起后台请求更新指数"""
        if not self.winfo_exists():
            return
            
        import threading
        
        def fetch_task():
            import urllib.request
            import re
            
            # 使用新浪的指数接口
            req = urllib.request.Request(
                'http://hq.sinajs.cn/list=sh000001,sz399001,sz399006,sh000688',
                headers={'Referer': 'https://finance.sina.com.cn'}
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    content = response.read().decode('gb18030', errors='ignore')
                
                parsed_data = {}
                for line in content.splitlines():
                    m = re.match(r'var hq_str_(s[hz]\d+)="([^"]+)"', line)
                    if m:
                        symbol = m.group(1)
                        fields = m.group(2).split(',')
                        if len(fields) >= 4:
                            yesterday_close = float(fields[2])
                            current = float(fields[3])
                            parsed_data[symbol] = (current, yesterday_close)
                
                # 回到主线程更新UI
                if self.winfo_exists():
                    self.after(0, self._on_indices_fetched, parsed_data)
            except Exception as e:
                print("Fetch indices error:", e)
                # 失败时也调度下一次更新，确保不中断
                if self.winfo_exists():
                    self.after(3000, self.update_indices)
                
        thread = threading.Thread(target=fetch_task, daemon=True)
        thread.start()

    def _on_indices_fetched(self, data):
        """在主线程更新指数显示，并安排下一次更新"""
        if not self.winfo_exists():
            return
            
        for symbol, label in self.index_labels.items():
            if symbol in data:
                current, yesterday_close = data[symbol]
                change = current - yesterday_close
                pct = (change / yesterday_close) * 100 if yesterday_close else 0.0
                
                sign = "+" if change >= 0 else ""
                name = self.index_names.get(symbol, symbol)
                label.configure(text=f"{name}: {current:.1f} ({sign}{pct:.2f}%)")
                
                if change > 0:
                    label.configure(foreground="#e74c3c")  # 红
                elif change < 0:
                    label.configure(foreground="#27ae60")  # 绿
                else:
                    label.configure(foreground="")
                    
        # 安排下一次更新 (3秒)
        if self.winfo_exists():
            self.after(3000, self.update_indices)
