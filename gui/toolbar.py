"""
工具栏组件

水平排列的工具栏，包含：
- 数据源选择下拉框
- 获取数据按钮
- 自动刷新间隔选择
- 指数类型筛选按钮组（全部/纳指/标普/道指）
- 搜索输入框
- 导出菜单按钮
- 主题切换按钮
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from config import INDEX_KEYWORDS


class ToolBar(ttk.Frame):
    """顶部工具栏组件"""

    # 数据源选项
    SOURCE_OPTIONS = ["天天基金", "晨星数据", "蚂蚁基金"]

    # 自动刷新选项: (显示文本, 分钟数)
    REFRESH_OPTIONS = ["关闭", "5分钟", "10分钟", "30分钟", "60分钟"]
    
    # 交易状态筛选选项
    STATUS_OPTIONS = [
        "全部状态",
        "可买入 (开放+限额)",
        "完全开放申购",
        "限大额",
        "暂停申购",
        "暂停赎回"
    ]

    # 自动刷新选项: (显示文本, 分钟数)
    REFRESH_OPTIONS = ["关闭", "5分钟", "10分钟", "30分钟", "60分钟"]

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # 回调属性（由 app.py 设置）
        self.on_fetch: Optional[Callable] = None
        # 相关回调
        self.on_filter_change = None
        self.on_search = None
        self.on_fetch_click = None
        self.on_update_selected_click = None
        self.on_auto_refresh_change = None
        self.on_export_excel: Optional[Callable] = None
        self.on_export_csv: Optional[Callable] = None
        self.on_theme_toggle: Optional[Callable] = None
        self.on_source_change: Optional[Callable] = None

        # 变量
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        
        self.source_var = tk.StringVar(value="天天基金")
        self.refresh_var = tk.StringVar(value=self.REFRESH_OPTIONS[0])
        self._filter_var = tk.StringVar(value="all")
        self.status_var = tk.StringVar(value=self.STATUS_OPTIONS[0])

        self._setup_ui()
        self._setup_bindings()

    def _setup_ui(self):
        """构建工具栏界面"""
        self.configure(padding=(10, 6))

        # ========================
        # 左侧区域：数据源 + 获取 + 自动刷新
        # ========================
        left_frame = ttk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        # 数据源标签 + 下拉框
        ttk.Label(
            left_frame,
            text="数据源:",
            font=("Microsoft YaHei", 9),
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.source_combo = ttk.Combobox(
            left_frame,
            textvariable=self.source_var,
            values=self.SOURCE_OPTIONS,
            state="readonly",
            width=10,
            font=("Microsoft YaHei", 9),
        )
        self.source_combo.pack(side=tk.LEFT, padx=(0, 8))

        # 获取数据按钮
        self.fetch_btn = ttk.Button(
            left_frame,
            text="🔄 获取数据",
            command=self._on_fetch_click,
            style="primary.TButton",
            width=12,
        )
        self.fetch_btn.pack(side=tk.LEFT, padx=(0, 4))
        
        # 更新选中数据按钮
        self.update_selected_btn = ttk.Button(
            left_frame,
            text="⚡ 更新选中",
            command=self._on_update_selected_click,
            style="info.TButton",
            width=12,
        )
        self.update_selected_btn.pack(side=tk.LEFT, padx=(0, 8))

        # 自动刷新
        ttk.Label(
            left_frame,
            text="⏱ 自动刷新:",
            font=("Microsoft YaHei", 9),
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.refresh_combo = ttk.Combobox(
            left_frame,
            textvariable=self.refresh_var,
            values=self.REFRESH_OPTIONS,
            state="readonly",
            width=8,
            font=("Microsoft YaHei", 9),
        )
        self.refresh_combo.pack(side=tk.LEFT, padx=(0, 4))

        # ========================
        # 分隔符
        # ========================
        sep1 = ttk.Separator(self, orient=tk.VERTICAL)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=2)

        # ========================
        # 中间区域：筛选按钮组
        # ========================
        self.filter_frame = ttk.Frame(self)
        self.filter_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(
            self.filter_frame,
            text="筛选:",
            font=("Microsoft YaHei", 9),
        ).pack(side=tk.LEFT, padx=(0, 4))

        self._filter_buttons = {}
        self.rebuild_filters()

        # ========================
        # 分隔符
        # ========================
        sep2 = ttk.Separator(self, orient=tk.VERTICAL)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=2)
        
        # ========================
        # 交易状态筛选
        # ========================
        status_frame = ttk.Frame(self)
        status_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(
            status_frame,
            text="状态:",
            font=("Microsoft YaHei", 9)
        ).pack(side=tk.LEFT, padx=(0, 4))
        
        self.status_combo = ttk.Combobox(
            status_frame,
            textvariable=self.status_var,
            values=self.STATUS_OPTIONS,
            state="readonly",
            width=16,
            font=("Microsoft YaHei", 9)
        )
        self.status_combo.pack(side=tk.LEFT, padx=(0, 4))
        self.status_combo.bind("<<ComboboxSelected>>", self._on_status_select)

        # ========================
        # 分隔符
        # ========================
        sep3 = ttk.Separator(self, orient=tk.VERTICAL)
        sep3.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=2)

        # ========================
        # 搜索区域
        # ========================
        search_frame = ttk.Frame(self)
        search_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(
            search_frame,
            text="🔍 搜索:",
            font=("Microsoft YaHei", 9),
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self._search_var,
            width=18,
            font=("Microsoft YaHei", 9),
        )
        self.search_entry.pack(side=tk.LEFT, padx=(0, 4))

        # 清除搜索按钮
        self.clear_search_btn = ttk.Button(
            search_frame,
            text="✕",
            command=self._clear_search,
            width=3,
            style="secondary.TButton",
        )
        self.clear_search_btn.pack(side=tk.LEFT)

        # ========================
        # 右侧区域：导出 + 主题
        # ========================
        right_frame = ttk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # 主题切换按钮
        self.theme_btn = ttk.Button(
            right_frame,
            text="🌙 暗色",
            command=self._on_theme_click,
            width=8,
            style="info.Outline.TButton",
        )
        self.theme_btn.pack(side=tk.RIGHT, padx=(8, 0))

        # 导出菜单按钮
        self.export_btn = ttk.Menubutton(
            right_frame,
            text="📥 导出 ▼",
            style="success.Outline.TMenubutton",
            width=10,
        )
        self.export_menu = tk.Menu(self.export_btn, tearoff=0)
        self.export_menu.add_command(
            label="📊 导出到 Excel",
            command=self._on_export_excel,
        )
        self.export_menu.add_command(
            label="📄 导出到 CSV",
            command=self._on_export_csv,
        )
        self.export_btn["menu"] = self.export_menu
        self.export_btn.pack(side=tk.RIGHT, padx=(0, 4))

    def _setup_bindings(self):
        """绑定事件"""
        # 搜索输入实时触发
        self._search_var.trace_add("write", self._on_search_change)

        # 数据源变化
        self.source_combo.bind("<<ComboboxSelected>>", self._on_source_select)

        # 自动刷新变化
        self.refresh_combo.bind("<<ComboboxSelected>>", self._on_refresh_select)

    # === 内部事件处理 ===

    def _on_fetch_click(self):
        """获取数据按钮点击"""
        if self.on_fetch:
            self.on_fetch()
            
    def _on_update_selected_click(self):
        """更新选中按钮点击"""
        if self.on_update_selected_click:
            self.on_update_selected_click()

    def _on_filter_click(self):
        """筛选按钮点击"""
        if self.on_filter_change:
            self.on_filter_change()

    def _on_search_change(self, *args):
        """搜索文本变化"""
        if self.on_search:
            self.on_search()

    def _clear_search(self):
        """清除搜索框"""
        self._search_var.set("")

    def _on_export_excel(self):
        """导出Excel"""
        if self.on_export_excel:
            self.on_export_excel()

    def _on_export_csv(self):
        """导出CSV"""
        if self.on_export_csv:
            self.on_export_csv()

    def _on_theme_click(self):
        """主题切换"""
        if self.on_theme_toggle:
            self.on_theme_toggle()

    def _on_source_select(self, event=None):
        """数据源选择变化"""
        if self.on_source_change:
            self.on_source_change()

    def _on_refresh_select(self, event=None):
        """自动刷新选择变化"""
        if self.on_auto_refresh_change:
            self.on_auto_refresh_change()
            
    def _on_status_select(self, event=None):
        """状态筛选选择变化"""
        if self.on_filter_change:
            self.on_filter_change()

    # === 公共方法 ===

    def rebuild_filters(self):
        """根据当前的 INDEX_KEYWORDS 重建过滤按钮"""
        # 销毁旧的按钮
        if hasattr(self, '_filter_buttons'):
            for btn in self._filter_buttons.values():
                btn.destroy()
        
        self._filter_buttons = {}
        
        # 重新生成选项
        options = [("all", "全部")]
        for name in INDEX_KEYWORDS.keys():
            options.append((name, name))
            
        for filter_key, filter_text in options:
            btn = ttk.Radiobutton(
                self.filter_frame,
                text=filter_text,
                variable=self._filter_var,
                value=filter_key,
                command=self._on_filter_click,
                style="Toolbutton",
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._filter_buttons[filter_key] = btn
            
        # 如果当前选中的不在选项里，重置为all
        if self._filter_var.get() not in [opt[0] for opt in options]:
            self._filter_var.set("all")

    def get_selected_source(self) -> str:
        """获取当前选中的数据源名称"""
        return self.source_var.get()

    def get_filter_type(self) -> str:
        """获取当前筛选类型 ("all"/"纳指"/"标普"/"道指")"""
        return self._filter_var.get()

    def get_search_text(self) -> str:
        """获取搜索框文本"""
        return self._search_var.get().strip()
        
    def get_status_filter(self) -> str:
        """获取交易状态过滤条件"""
        return self.status_var.get()

    def set_fetch_enabled(self, enabled: bool):
        """启用/禁用获取按钮"""
        state = "normal" if enabled else "disabled"
        self.fetch_btn.configure(state=state)

    def set_fetch_button_text(self, text: str):
        """设置获取按钮文本"""
        self.fetch_btn.configure(text=text)

    def set_theme_button(self, is_dark: bool):
        """更新主题按钮显示"""
        if is_dark:
            self.theme_btn.configure(text="🌙 暗色")
        else:
            self.theme_btn.configure(text="☀️ 亮色")

    def get_refresh_interval(self) -> int:
        """获取自动刷新间隔（分钟），0 表示关闭"""
        text = self.refresh_var.get()
        if text == "关闭":
            return 0
        try:
            return int(text.replace("分钟", ""))
        except ValueError:
            return 0
