"""
数据表格组件

使用 ttk.Treeview 实现基金数据的表格展示，支持：
- 列标题点击排序（升序/降序切换）
- 涨跌着色（红涨绿跌，中国惯例）
- 交替行背景色
- 双击行触发回调
- 垂直和水平滚动条
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional


class FundTableView(ttk.Frame):
    """基金数据表格视图组件"""

    # 列定义: (列ID, 列标题, 宽度, 对齐方式)
    COLUMNS = [
        ("code", "基金代码", 80, "center"),
        ("name", "基金名称", 180, "center"),
        ("purchase_limit", "交易状态", 220, "center"),
        ("index_type", "跟踪指数", 80, "center"),
        ("nav", "单位净值", 90, "center"),
        ("nav_date", "净值日期", 90, "center"),
        ("acc_nav", "累计净值", 90, "center"),
        ("daily_change", "日增长值", 90, "center"),
        ("daily_change_pct", "日增长率(%)", 100, "center"),
    ]

    # 涨跌着色
    COLOR_UP = "#e74c3c"      # 红色（涨）
    COLOR_DOWN = "#27ae60"    # 绿色（跌）
    COLOR_FLAT = ""           # 默认色
    ALT_ROW_BG = "#f2f7fa"    # 交替行背景（亮色主题 flatly）
    ALT_ROW_BG_DARK = "#273b4d"  # 交替行背景（暗色主题 superhero）

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self._funds_data: List[Dict] = []
        self._sort_column: str = ""
        self._sort_reverse: bool = False
        self._double_click_callback: Optional[Callable] = None
        self._history_callback: Optional[Callable] = None
        self._right_click_callback: Optional[Callable] = None
        self._delete_custom_callback: Optional[Callable] = None
        self._add_custom_callback: Optional[Callable] = None
        self._is_dark_theme = True

        self._setup_ui()
        self._setup_tags()
        self._setup_bindings()

    def _setup_ui(self):
        """创建表格和滚动条"""
        # 创建容器
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        # 列 ID 列表
        col_ids = [col[0] for col in self.COLUMNS]

        # 创建 Treeview
        self.tree = ttk.Treeview(
            container,
            columns=col_ids,
            show="headings",
            selectmode="extended",
        )
        
        # 调整行高和字体
        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=("Microsoft YaHei", 9))
        style.configure("Treeview.Heading", font=("Microsoft YaHei", 10, "bold"), padding=4)

        # 配置各列
        for col_id, col_title, col_width, col_anchor in self.COLUMNS:
            self.tree.heading(
                col_id,
                text=col_title,
                anchor=col_anchor,
                command=lambda c=col_id: self._on_heading_click(c),
            )
            self.tree.column(
                col_id,
                width=col_width,
                minwidth=60,
                anchor=col_anchor,
                stretch=(col_id in ("name", "purchase_limit")),  # 名称和交易状态自动拉伸
            )

        # 垂直滚动条
        v_scroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scroll.set)

        # 水平滚动条
        h_scroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scroll.set)

        # 布局
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

    def _setup_tags(self):
        """配置涨跌和交替行的标签样式"""
        # 涨跌标签
        self.tree.tag_configure("up", foreground=self.COLOR_UP)
        self.tree.tag_configure("down", foreground=self.COLOR_DOWN)
        self.tree.tag_configure("flat", foreground="")

        # 交替行标签
        self.tree.tag_configure("even_row", background=self.ALT_ROW_BG_DARK if self._is_dark_theme else self.ALT_ROW_BG)
        self.tree.tag_configure("odd_row", background="")

        # 涨跌 + 交替行组合标签
        self.tree.tag_configure("up_even", foreground=self.COLOR_UP,
                                background=self.ALT_ROW_BG_DARK if self._is_dark_theme else self.ALT_ROW_BG)
        self.tree.tag_configure("down_even", foreground=self.COLOR_DOWN,
                                background=self.ALT_ROW_BG_DARK if self._is_dark_theme else self.ALT_ROW_BG)
        self.tree.tag_configure("flat_even", foreground="",
                                background=self.ALT_ROW_BG_DARK if self._is_dark_theme else self.ALT_ROW_BG)

    def _setup_bindings(self):
        """绑定事件"""
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)

    def _on_right_click(self, event):
        """处理右键点击，弹出上下文菜单"""
        # 选中右键点击的行（如果没有选中多行的话）
        item = self.tree.identify_row(event.y)
        if item:
            # 如果右击的行不在已选中的行中，则单选该行
            if item not in self.tree.selection():
                self.tree.selection_set(item)
                
            menu = tk.Menu(self, tearoff=0)
            
            if self._right_click_callback:
                menu.add_command(label="🔄 更新选中基金状态", command=self._right_click_callback)
                
            if self._history_callback:
                fund = self.get_selected_fund()
                if fund:
                    menu.add_command(label="📈 查看历史净值图表", command=lambda f=fund: self._history_callback(f))
                    
                    # 根据是否已经是自选，显示加入自选或取消自选
                    is_custom_fund = (fund.get("is_custom") == 1 or fund.get("index_type") == "自选")
                    if is_custom_fund and self._delete_custom_callback:
                        menu.add_separator()
                        menu.add_command(label="🗑️ 取消自选", command=lambda f=fund: self._delete_custom_callback(f))
                    elif not is_custom_fund and self._add_custom_callback:
                        menu.add_separator()
                        menu.add_command(label="⭐ 加入自选", command=lambda f=fund: self._add_custom_callback(f))
                    
            if menu.index("end") is not None:
                menu.post(event.x_root, event.y_root)

    def _get_sort_indicator(self, col_id: str) -> str:
        """获取排序指示器"""
        if self._sort_column == col_id:
            return " ▼" if self._sort_reverse else " ▲"
        return ""

    def _on_heading_click(self, col_id: str):
        """列标题点击排序"""
        if self._sort_column == col_id:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col_id
            self._sort_reverse = False

        self.sort_by_column(col_id, self._sort_reverse)

        # 更新所有列标题（清除旧指示器，添加新指示器）
        for cid, title, _, _ in self.COLUMNS:
            indicator = self._get_sort_indicator(cid)
            self.tree.heading(cid, text=f"{title}{indicator}")

    def _on_double_click(self, event):
        """双击行事件"""
        if self._double_click_callback:
            fund = self.get_selected_fund()
            if fund:
                self._double_click_callback(fund)

    @property
    def on_right_click(self) -> Optional[Callable]:
        return self._right_click_callback

    @on_right_click.setter
    def on_right_click(self, callback: Callable):
        self._right_click_callback = callback

    def _get_row_tags(self, fund: Dict, row_idx: int) -> tuple:
        """根据涨跌和行号决定标签"""
        is_even = row_idx % 2 == 0
        daily_change_pct = fund.get("daily_change_pct")

        # 判断涨跌
        direction = "flat"
        if daily_change_pct is not None:
            try:
                pct_val = float(daily_change_pct)
                if pct_val > 0:
                    direction = "up"
                elif pct_val < 0:
                    direction = "down"
            except (ValueError, TypeError):
                pass

        if is_even:
            return (f"{direction}_even",)
        else:
            return (direction,)

    def _format_value(self, key: str, value) -> str:
        """格式化显示值"""
        if value is None:
            return "--"

        if key in ("nav", "acc_nav"):
            try:
                return f"{float(value):.4f}"
            except (ValueError, TypeError):
                return str(value)
        elif key == "daily_change":
            try:
                v = float(value)
                return f"{v:+.4f}" if v != 0 else "0.0000"
            except (ValueError, TypeError):
                return str(value)
        elif key == "daily_change_pct":
            try:
                v = float(value)
                return f"{v:+.2f}" if v != 0 else "0.00"
            except (ValueError, TypeError):
                return str(value)
        elif key == "since_inception":
            try:
                v = float(value)
                return f"{v:+.2f}" if v != 0 else "0.00"
            except (ValueError, TypeError):
                return str(value)

        return str(value)

    # === 公共方法 ===

    def load_data(self, funds: List[Dict]):
        """清空并重新加载数据"""
        # 保存数据副本
        self._funds_data = list(funds)

        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 插入新数据
        for row_idx, fund in enumerate(funds):
            values = []
            for col_id, _, _, _ in self.COLUMNS:
                raw_val = fund.get(col_id, "")
                values.append(self._format_value(col_id, raw_val))

            tags = self._get_row_tags(fund, row_idx)
            self.tree.insert("", tk.END, values=values, tags=tags)

    def get_selected_fund(self) -> Optional[Dict]:
        """获取当前选中的基金数据"""
        selection = self.tree.selection()
        if not selection:
            return None

        item = selection[0]
        values = self.tree.item(item, "values")
        if not values:
            return None

        # 从原始数据中查找匹配的基金（通过代码匹配）
        code = values[0]
        for fund in self._funds_data:
            if fund.get("code") == code:
                return fund

        # 如果找不到原始数据，构建一个基本的字典
        result = {}
        for idx, (col_id, _, _, _) in enumerate(self.COLUMNS):
            if idx < len(values):
                result[col_id] = values[idx]
        return result

    def sort_by_column(self, col: str, reverse: bool = False):
        """按指定列排序"""
        # 数值列需要数值排序
        numeric_cols = {"nav", "acc_nav", "daily_change", "daily_change_pct", "since_inception"}

        def sort_key(fund):
            val = fund.get(col, "")
            if col in numeric_cols:
                try:
                    return float(val) if val is not None else float("-inf")
                except (ValueError, TypeError):
                    return float("-inf")
            return str(val or "").lower()

        self._funds_data.sort(key=sort_key, reverse=reverse)
        self._sort_column = col
        self._sort_reverse = reverse

        # 重新加载数据
        self.load_data(self._funds_data)

    def set_double_click_callback(self, callback: Callable):
        """设置双击行的回调函数"""
        self._double_click_callback = callback
        
    def set_history_callback(self, callback: Callable):
        """设置查看历史净值的回调函数"""
        self._history_callback = callback
        
    def set_delete_custom_callback(self, callback: Callable):
        """设置删除自选的回调函数"""
        self._delete_custom_callback = callback

    def set_add_custom_callback(self, callback: Callable):
        """设置加入自选的回调函数"""
        self._add_custom_callback = callback

    def get_all_data(self) -> List[Dict]:
        """返回当前显示的所有数据"""
        return self._funds_data

    def get_selected_funds(self) -> List[Dict]:
        """获取当前选中的所有基金数据"""
        selected = []
        for item in self.tree.selection():
            values = self.tree.item(item, "values")
            if values:
                # 根据 values 找到原始 fund 数据
                code = values[0]
                for f in self._funds_data:
                    if f.get("code") == code:
                        selected.append(f)
                        break
        return selected

    def update_theme(self, is_dark: bool):
        """更新主题相关样式"""
        self._is_dark_theme = is_dark
        self._setup_tags()
        # 重新加载以应用新标签样式
        if self._funds_data:
            self.load_data(self._funds_data)
