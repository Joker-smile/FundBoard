"""
对话框模块

包含以下弹窗：
- HistoryDialog: 基金历史净值对话框
- AboutDialog: 关于对话框
- SettingsDialog: 设置对话框
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List

from config import APP_SETTINGS, INDEX_KEYWORDS, save_user_config


class HistoryDialog(tk.Toplevel):
    """基金历史净值对话框"""

    def __init__(self, parent, fund_code: str, fund_name: str, history_data: List[Dict]):
        """
        初始化历史净值对话框。

        Args:
            parent: 父窗口
            fund_code: 基金代码
            fund_name: 基金名称
            history_data: 历史净值数据列表
        """
        super().__init__(parent)

        self.title(f"历史净值 - {fund_code} {fund_name}")
        self.geometry("650x450")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        # 窗口居中
        self._center_window(650, 450)

        self._fund_code = fund_code
        self._fund_name = fund_name
        self._history_data = history_data

        self._setup_ui()
        self._load_data()

    def _center_window(self, width: int, height: int):
        """将窗口居中显示"""
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_ui(self):
        """构建界面"""
        # 标题区域
        header_frame = ttk.Frame(self, padding=(12, 10))
        header_frame.pack(fill=tk.X)

        ttk.Label(
            header_frame,
            text=f"📈 {self._fund_code} - {self._fund_name}",
            font=("Microsoft YaHei", 12, "bold"),
        ).pack(side=tk.LEFT)

        ttk.Label(
            header_frame,
            text=f"最近 {len(self._history_data)} 条记录",
            font=("Microsoft YaHei", 9),
            foreground="#888888",
        ).pack(side=tk.RIGHT)

        # 分隔线
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)

        # 表格区域
        table_frame = ttk.Frame(self, padding=(10, 8))
        table_frame.pack(fill=tk.BOTH, expand=True)

        # 定义列
        columns = ("date", "nav", "acc_nav", "daily_change_pct")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        # 配置列
        self.tree.heading("date", text="日期", anchor="center")
        self.tree.heading("nav", text="单位净值", anchor="center")
        self.tree.heading("acc_nav", text="累计净值", anchor="center")
        self.tree.heading("daily_change_pct", text="日增长率(%)", anchor="center")

        self.tree.column("date", width=120, anchor="center")
        self.tree.column("nav", width=120, anchor="center")
        self.tree.column("acc_nav", width=120, anchor="center")
        self.tree.column("daily_change_pct", width=120, anchor="center")

        # 涨跌标签
        self.tree.tag_configure("up", foreground="#e74c3c")
        self.tree.tag_configure("down", foreground="#27ae60")
        self.tree.tag_configure("flat", foreground="")

        # 滚动条
        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部按钮
        btn_frame = ttk.Frame(self, padding=(10, 8))
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame,
            text="关闭",
            command=self.destroy,
            style="secondary.TButton",
            width=10,
        ).pack(side=tk.RIGHT)

    def _load_data(self):
        """加载历史数据到表格"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for record in self._history_data:
            date_str = record.get("nav_date", record.get("date", "--"))
            nav = record.get("nav", "--")
            acc_nav = record.get("acc_nav", "--")
            daily_pct = record.get("daily_change_pct", None)

            # 格式化净值
            try:
                nav_str = f"{float(nav):.4f}" if nav not in (None, "--") else "--"
            except (ValueError, TypeError):
                nav_str = str(nav)

            try:
                acc_nav_str = f"{float(acc_nav):.4f}" if acc_nav not in (None, "--") else "--"
            except (ValueError, TypeError):
                acc_nav_str = str(acc_nav)

            # 格式化日增长率
            try:
                if daily_pct is not None:
                    pct_val = float(daily_pct)
                    pct_str = f"{pct_val:+.2f}"
                    if pct_val > 0:
                        tag = ("up",)
                    elif pct_val < 0:
                        tag = ("down",)
                    else:
                        tag = ("flat",)
                else:
                    pct_str = "--"
                    tag = ("flat",)
            except (ValueError, TypeError):
                pct_str = str(daily_pct) if daily_pct else "--"
                tag = ("flat",)

            self.tree.insert(
                "", tk.END,
                values=(date_str, nav_str, acc_nav_str, pct_str),
                tags=tag,
            )


class AboutDialog(tk.Toplevel):
    """关于对话框"""

    def __init__(self, parent):
        super().__init__(parent)

        self.title("关于")
        self.geometry("420x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._center_window(420, 320)
        self._setup_ui()

    def _center_window(self, width: int, height: int):
        """将窗口居中显示"""
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_ui(self):
        """构建界面"""
        main_frame = ttk.Frame(self, padding=30)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 应用图标/标题
        ttk.Label(
            main_frame,
            text="📊",
            font=("Segoe UI Emoji", 36),
        ).pack(pady=(0, 8))

        app_title = APP_SETTINGS.get("title", "场外指数基金数据获取工具")
        ttk.Label(
            main_frame,
            text=app_title,
            font=("Microsoft YaHei", 14, "bold"),
        ).pack(pady=(0, 4))

        version = APP_SETTINGS.get("version", "1.0.0")
        ttk.Label(
            main_frame,
            text=f"版本 {version}",
            font=("Microsoft YaHei", 10),
            foreground="#888888",
        ).pack(pady=(0, 16))

        # 功能简介
        features_text = (
            "功能特性：\n"
            "• 支持多数据源（天天基金、晨星、蚂蚁基金）\n"
            "• 实时获取纳指、标普、道指场外基金数据\n"
            "• 自动刷新、筛选、搜索功能\n"
            "• 历史净值查询\n"
            "• 数据导出（Excel / CSV）\n"
            "• 亮色/暗色主题切换"
        )
        ttk.Label(
            main_frame,
            text=features_text,
            font=("Microsoft YaHei", 9),
            justify="left",
            wraplength=350,
        ).pack(pady=(0, 16), anchor="w")

        # 关闭按钮
        ttk.Button(
            main_frame,
            text="确定",
            command=self.destroy,
            style="primary.TButton",
            width=10,
        ).pack()


class SettingsDialog(tk.Toplevel):
    """设置对话框"""

    def __init__(self, parent, current_settings: Dict = None):
        """
        初始化设置对话框。

        Args:
            parent: 父窗口
            current_settings: 当前设置字典
        """
        super().__init__(parent)

        self.title("设置")
        self.geometry("520x650")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._settings = current_settings or {}
        self._result = None

        self._center_window(520, 650)
        self._setup_ui()

    def _center_window(self, width: int, height: int):
        """将窗口居中显示"""
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_ui(self):
        """构建界面"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(
            main_frame,
            text="⚙️ 应用设置",
            font=("Microsoft YaHei", 13, "bold"),
        ).pack(pady=(0, 16), anchor="w")

        # 设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="网络设置", padding=12)
        settings_frame.pack(fill=tk.X, pady=(0, 12))

        # 请求延迟
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=tk.X, pady=4)
        ttk.Label(row1, text="请求延迟 (秒):", font=("Microsoft YaHei", 9), width=16, anchor="w").pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value=str(self._settings.get("request_delay", 1.0)))
        ttk.Entry(row1, textvariable=self.delay_var, width=10, font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=4)

        # 重试次数
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill=tk.X, pady=4)
        ttk.Label(row2, text="重试次数:", font=("Microsoft YaHei", 9), width=16, anchor="w").pack(side=tk.LEFT)
        self.retry_var = tk.StringVar(value=str(self._settings.get("retry_count", 3)))
        ttk.Entry(row2, textvariable=self.retry_var, width=10, font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=4)

        # 超时时间
        row3 = ttk.Frame(settings_frame)
        row3.pack(fill=tk.X, pady=4)
        ttk.Label(row3, text="超时时间 (秒):", font=("Microsoft YaHei", 9), width=16, anchor="w").pack(side=tk.LEFT)
        self.timeout_var = tk.StringVar(value=str(self._settings.get("timeout", 30)))
        ttk.Entry(row3, textvariable=self.timeout_var, width=10, font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=4)

        # 数据设置
        data_frame = ttk.LabelFrame(main_frame, text="数据设置", padding=12)
        data_frame.pack(fill=tk.X, pady=(0, 12))

        row4 = ttk.Frame(data_frame)
        row4.pack(fill=tk.X, pady=4)
        ttk.Label(row4, text="数据库文件:", font=("Microsoft YaHei", 9), width=16, anchor="w").pack(side=tk.LEFT)
        db_file = self._settings.get("db_file", APP_SETTINGS.get("db_file", "fund_data.db"))
        ttk.Label(row4, text=db_file, font=("Microsoft YaHei", 9), foreground="#888888").pack(side=tk.LEFT, padx=4)

        row5 = ttk.Frame(data_frame)
        row5.pack(fill=tk.X, pady=4)
        ttk.Label(row5, text="历史记录条数:", font=("Microsoft YaHei", 9), width=16, anchor="w").pack(side=tk.LEFT)
        self.history_limit_var = tk.StringVar(value=str(self._settings.get("history_limit", 30)))
        ttk.Entry(row5, textvariable=self.history_limit_var, width=10, font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=4)

        # 指数关键词设置
        keyword_frame = ttk.LabelFrame(main_frame, text="指数自定义 (格式: 名称: 关键词1, 关键词2)", padding=12)
        keyword_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        
        self.keyword_text = tk.Text(keyword_frame, height=6, font=("Microsoft YaHei", 9))
        self.keyword_text.pack(fill=tk.BOTH, expand=True)
        
        # 加载当前关键词
        keyword_lines = []
        for name, kws in INDEX_KEYWORDS.items():
            keyword_lines.append(f"{name}: {', '.join(kws)}")
        self.keyword_text.insert("1.0", "\n".join(keyword_lines))

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(
            btn_frame,
            text="取消",
            command=self.destroy,
            style="secondary.TButton",
            width=10,
        ).pack(side=tk.RIGHT, padx=(4, 0))

        ttk.Button(
            btn_frame,
            text="保存",
            command=self._save_settings,
            style="primary.TButton",
            width=10,
        ).pack(side=tk.RIGHT)

    def _save_settings(self):
        """保存设置"""
        try:
            settings_dict = {
                "request_delay": float(self.delay_var.get()),
                "retry_count": int(self.retry_var.get()),
                "timeout": int(self.timeout_var.get()),
                "history_limit": int(self.history_limit_var.get()),
            }
            
            # 解析关键词
            text_content = self.keyword_text.get("1.0", tk.END).strip()
            keywords_dict = {}
            for line in text_content.split('\n'):
                line = line.strip()
                if not line or (':' not in line and '：' not in line):
                    continue
                # 兼容中英文冒号
                sep = ':' if ':' in line else '：'
                name, kws_str = line.split(sep, 1)
                name = name.strip()
                # 兼容中英文逗号
                kws_str = kws_str.replace('，', ',')
                kws = [kw.strip() for kw in kws_str.split(',') if kw.strip()]
                if name and kws:
                    keywords_dict[name] = kws
                    
            if not keywords_dict:
                from tkinter import messagebox
                messagebox.showwarning("输入错误", "指数关键词不能为空，且格式必须正确！", parent=self)
                return
                
            # 保存到文件
            save_user_config(keywords_dict, settings_dict)
            
            self._result = {
                "settings": settings_dict,
                "keywords": keywords_dict
            }
        except ValueError:
            from tkinter import messagebox
            messagebox.showwarning("输入错误", "请输入有效的数值", parent=self)
            return

        self.destroy()

    def get_result(self) -> Dict:
        """获取保存的设置结果（窗口关闭后调用）"""
        return self._result
