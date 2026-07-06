"""
主应用窗口

场外指数基金数据获取工具的核心应用类。
使用 ttkbootstrap 创建主窗口，组装所有 GUI 组件，
协调数据获取、筛选、搜索、导出等功能。

关键设计：
- 数据获取在后台线程中执行，不阻塞 UI
- 线程完成后通过 root.after() 回到主线程更新 UI
- 筛选和搜索使用 AND 逻辑同时生效
- 自动刷新使用 root.after() 定时器实现
"""

import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from config import APP_SETTINGS
from database import FundDatabase
from data_sources import AntFundDataSource, EastMoneyDataSource, MorningstarDataSource
from export import export_to_csv, export_to_excel
from gui.dialogs import AboutDialog, HistoryDialog, SettingsDialog
from gui.status_bar import StatusBar
from gui.table_view import FundTableView
from gui.toolbar import ToolBar


class FundApp:
    """场外指数基金数据获取工具主应用"""

    # 主题配置
    DARK_THEME = "superhero"
    LIGHT_THEME = "flatly"

    def __init__(self):
        # 创建主窗口
        self.root = ttk.Window(
            title=APP_SETTINGS["title"],
            themename=self.DARK_THEME,
            size=(1400, 800),
            minsize=APP_SETTINGS["min_size"],
        )

        # 设置默认字体
        self.root.option_add("*Font", "Microsoft\\ YaHei 10")

        # 初始化数据库
        self.db = FundDatabase()

        # 初始化数据源
        self.data_sources = {
            "天天基金": EastMoneyDataSource(),
            "晨星数据": MorningstarDataSource(),
            "蚂蚁基金": AntFundDataSource(),
        }
        self.current_source = "天天基金"

        # 数据状态
        self.all_funds = []          # 当前所有基金数据（未经筛选）
        self.auto_refresh_job = None # 自动刷新定时任务 ID
        self.is_dark_theme = True    # 当前主题
        self._is_fetching = False    # 是否正在获取数据

        # 设置 UI
        self._setup_ui()
        self._bind_events()
        self._center_window()
        self._load_cached_data()

    def _setup_ui(self):
        """构建主界面布局"""
        # === 顶部工具栏 ===
        self.toolbar = ToolBar(self.root)
        self.toolbar.pack(fill=tk.X, side=tk.TOP, padx=0, pady=0)

        # 工具栏下方分隔线
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # === 中间表格区域（填充剩余空间） ===
        table_container = ttk.Frame(self.root)
        table_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 0))

        self.table_view = FundTableView(table_container)
        self.table_view.pack(fill=tk.BOTH, expand=True)

        # === 底部状态栏 ===
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X)

        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)

        # 设置初始状态
        self.status_bar.set_source(self.current_source)
        self.status_bar.set_status("就绪", "success")

        # === 菜单栏 ===
        self._setup_menubar()

    def _setup_menubar(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="获取数据", command=self._fetch_data, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="导出 Excel", command=self._export_excel)
        file_menu.add_command(label="导出 CSV", command=self._export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_close)
        menubar.add_cascade(label="文件", menu=file_menu)

        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="清空数据", command=self._clear_data)
        edit_menu.add_separator()
        edit_menu.add_command(label="设置", command=self._show_settings)
        menubar.add_cascade(label="编辑", menu=edit_menu)

        # 视图菜单
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="切换主题", command=self._toggle_theme)
        menubar.add_cascade(label="视图", menu=view_menu)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.root.configure(menu=menubar)

        # 快捷键绑定
        self.root.bind("<F5>", lambda e: self._fetch_data())

    def _bind_events(self):
        """绑定工具栏和表格的回调事件"""
        # 工具栏回调
        self.toolbar.on_fetch = self._fetch_data
        self.toolbar.on_filter_change = self._apply_filter
        self.toolbar.on_search = self._apply_search
        self.toolbar.on_export_excel = self._export_excel
        self.toolbar.on_export_csv = self._export_csv
        self.toolbar.on_theme_toggle = self._toggle_theme
        self.toolbar.on_source_change = self._change_source
        self.toolbar.on_auto_refresh_change = self._setup_auto_refresh
        self.toolbar.on_update_selected_click = self._update_selected_funds

        # 表格双击和右键回调
        self.table_view.set_double_click_callback(self._show_fund_webview)
        self.table_view.set_history_callback(self._show_fund_history)
        self.table_view.set_delete_custom_callback(self._delete_custom_fund)
        self.table_view.on_right_click = self._update_selected_funds
        
        # 添加自选回调
        self.toolbar.on_add_custom_fund_click = self._show_add_fund_dialog

        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # ============================
    # 数据获取
    # ============================

    def _fetch_data(self, is_auto=False):
        """在后台线程获取数据，不阻塞 UI"""
        if self._is_fetching:
            return

        self._is_fetching = True
        self.toolbar.set_fetch_enabled(False)
        self.toolbar.set_fetch_button_text("⏳ 获取中...")
        self.status_bar.set_status("正在获取数据...", "info")

        # 获取当前选中的数据源
        source_name = self.toolbar.get_selected_source()
        source = self.data_sources.get(source_name)

        if not source:
            self._on_fetch_error(f"未知数据源: {source_name}")
            return

        # 进度回调（将在后台线程中调用，需通过 after 回到主线程）
        def progress_callback(current, total, message):
            self.root.after(0, self.status_bar.show_progress, current, total, message)

        # 后台线程执行数据获取
        def fetch_task():
            try:
                # 检查数据源是否可用
                if not source.is_available():
                    self.root.after(0, self._on_fetch_error, f"数据源 [{source_name}] 不可用")
                    return

                # 获取数据
                funds = source.fetch_fund_list(
                    index_type="all",
                    progress_callback=progress_callback,
                )

                # 从数据库中读取所有自选基金
                custom_funds = self.db.get_funds(index_type="自选")
                if custom_funds:
                    # 找出不在主列表中的自选基金进行额外拉取
                    main_codes = {f["code"] for f in funds}
                    needed_custom_funds = [cf for cf in custom_funds if cf["code"] not in main_codes]
                    
                    # 标记主列表中已经属于自选的基金
                    for f in funds:
                        if f["code"] in {cf["code"] for cf in custom_funds}:
                            f["is_custom"] = 1

                    if needed_custom_funds:
                        custom_funds_data = source.fetch_specific_funds(needed_custom_funds, progress_callback=progress_callback)
                        if custom_funds_data:
                            for cf in custom_funds_data:
                                cf["is_custom"] = 1
                                funds.append(cf)

                # 回到主线程处理结果
                self.root.after(0, self._on_fetch_success, funds, source_name, is_auto)

            except Exception as e:
                self.root.after(0, self._on_fetch_error, str(e), is_auto)

        thread = threading.Thread(target=fetch_task, daemon=True)
        thread.start()

    def _update_selected_funds(self):
        """手动更新选中基金的状态和数据"""
        selected_funds = self.table_view.get_selected_funds()
        if not selected_funds:
            messagebox.showinfo("提示", "请先在表格中选中要更新的基金（按住 Ctrl/Shift 可多选）。", parent=self.root)
            return

        if self._is_fetching:
            messagebox.showinfo("提示", "当前正在获取数据，请稍后再试。", parent=self.root)
            return

        self._is_fetching = True
        self.status_bar.set_status(f"正在更新选中的 {len(selected_funds)} 只基金...", "info")

        source_name = self.toolbar.get_selected_source()
        source = self.data_sources.get(source_name)

        if not source:
            self._on_fetch_error(f"未知数据源: {source_name}")
            return

        def progress_callback(current, total, message):
            self.root.after(0, self.status_bar.show_progress, current, total, message)

        def update_task():
            try:
                if not source.is_available():
                    self.root.after(0, self._on_fetch_error, f"数据源 [{source_name}] 不可用")
                    return

                updated = source.fetch_specific_funds(selected_funds, progress_callback)
                self.root.after(0, self._on_update_selected_success, updated)
            except Exception as e:
                self.root.after(0, self._on_fetch_error, str(e), False)

        thread = threading.Thread(target=update_task, daemon=True)
        thread.start()

    def _on_update_selected_success(self, updated_funds):
        """选中基金更新成功回调（主线程）"""
        self._is_fetching = False
        
        if not updated_funds:
            self.status_bar.set_status("未获取到更新数据", "warning")
            return
            
        # 合并更新的数据到 self.all_funds 中
        updated_dict = {f["code"]: f for f in updated_funds}
        for i, fund in enumerate(self.all_funds):
            if fund["code"] in updated_dict:
                self.all_funds[i].update(updated_dict[fund["code"]])
                
        # 更新数据库
        try:
            self.db.clear_funds()
            self.db.save_funds(self.all_funds)
        except Exception as e:
            print(f"保存数据库失败: {e}")
            
        self._apply_filter_and_search()
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_bar.set_status(f"成功更新 {len(updated_funds)} 只基金", "success")
        self.status_bar.set_update_time(now_str)

    def _on_fetch_success(self, funds, source_name, is_auto=False):
        """数据获取成功回调（主线程）"""
        self._is_fetching = False
        self.toolbar.set_fetch_enabled(True)
        self.toolbar.set_fetch_button_text("🔄 获取数据")

        if not funds:
            self.status_bar.set_status("未获取到数据", "warning")
            return

        # 保存到数据库
        try:
            # 每次获取全量新数据后，清空非自选的旧的快照以移除不再跟踪的废弃基金
            self.db.clear_funds(keep_custom=True)
            self.db.save_funds(funds)
        except Exception as e:
            print(f"保存数据库失败: {e}")

        # 更新数据
        self.all_funds = funds
        self.current_source = source_name

        # 应用当前筛选和搜索
        self._apply_filter_and_search()

        # 更新状态栏
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_bar.set_status(f"数据获取成功 ({source_name})", "success")
        self.status_bar.set_source(source_name)
        self.status_bar.set_update_time(now_str)
        self._update_stats(funds)

        # 弹窗通知 (仅在手动获取时提示，避免自动刷新打扰用户)
        if not is_auto:
            messagebox.showinfo(
                "获取完成",
                f"数据获取完毕，共获取 {len(funds)} 条记录。",
                parent=self.root
            )

    def _on_fetch_error(self, error_msg, is_auto=False):
        """数据获取失败回调（主线程）"""
        self._is_fetching = False
        self.toolbar.set_fetch_enabled(True)
        self.toolbar.set_fetch_button_text("🔄 获取数据")
        self.status_bar.set_status(f"获取失败: {error_msg}", "error")

        messagebox.showerror(
            "获取数据失败",
            f"数据获取过程中发生错误：\n\n{error_msg}\n\n请检查网络连接或切换数据源重试。",
            parent=self.root,
        )

    # ============================
    # 筛选和搜索
    # ============================

    def _apply_filter(self):
        """应用指数类型筛选"""
        self._apply_filter_and_search()

    def _apply_search(self, *args):
        """应用搜索过滤"""
        self._apply_filter_and_search()

    def _apply_filter_and_search(self):
        """同时应用筛选和搜索（AND 逻辑）"""
        filtered = list(self.all_funds)

        # 应用指数类型筛选
        filter_type = self.toolbar.get_filter_type()
        if filter_type != "all":
            if filter_type == "自选":
                filtered = [f for f in filtered if f.get("is_custom") == 1]
            else:
                filtered = [f for f in filtered if f.get("index_type") == filter_type]
            
        # 应用交易状态筛选
        status_filter = self.toolbar.get_status_filter()
        if status_filter != "全部状态":
            if status_filter == "可买入 (开放+限额)":
                filtered = [f for f in filtered if "开放申购" in f.get("purchase_limit", "") or "限大额" in f.get("purchase_limit", "")]
            elif status_filter == "完全开放申购":
                filtered = [f for f in filtered if "开放申购" in f.get("purchase_limit", "") and "限大额" not in f.get("purchase_limit", "")]
            elif status_filter == "限大额":
                filtered = [f for f in filtered if "限大额" in f.get("purchase_limit", "")]
            elif status_filter == "暂停申购":
                filtered = [f for f in filtered if "暂停申购" in f.get("purchase_limit", "")]
            elif status_filter == "暂停赎回":
                filtered = [f for f in filtered if "暂停赎回" in f.get("purchase_limit", "")]

        # 应用搜索文本过滤
        search_text = self.toolbar.get_search_text().lower().strip()
        if search_text:
            search_terms = search_text.split()
            new_filtered = []
            for f in filtered:
                name = str(f.get("name", "")).lower()
                code = str(f.get("code", "")).lower()
                
                # 判断是否所有搜索词都在名称或代码中
                match = True
                for term in search_terms:
                    if term not in name and term not in code:
                        match = False
                        break
                if match:
                    new_filtered.append(f)
            filtered = new_filtered

        # 更新表格
        self.table_view.load_data(filtered)

        # 更新统计（基于过滤后的数据）
        self.status_bar.set_fund_count(len(filtered))

    # ============================
    # 导出功能
    # ============================

    def _export_excel(self):
        """导出当前数据到 Excel"""
        funds = self.table_view.get_all_data()
        if not funds:
            messagebox.showwarning("导出提示", "当前没有可导出的数据。", parent=self.root)
            return

        filepath = filedialog.asksaveasfilename(
            title="导出到 Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
            initialfile=f"基金数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            parent=self.root,
        )

        if not filepath:
            return

        try:
            success = export_to_excel(funds, filepath)
            if success:
                self.status_bar.set_status("Excel 导出成功", "success")
                messagebox.showinfo("导出成功", f"数据已成功导出到：\n{filepath}", parent=self.root)
            else:
                self.status_bar.set_status("Excel 导出失败", "error")
                messagebox.showerror("导出失败", "导出过程中发生错误。", parent=self.root)
        except ImportError as e:
            messagebox.showerror("缺少依赖", str(e), parent=self.root)
        except Exception as e:
            self.status_bar.set_status("Excel 导出失败", "error")
            messagebox.showerror("导出失败", f"导出过程中发生错误：\n{e}", parent=self.root)

    def _export_csv(self):
        """导出当前数据到 CSV"""
        funds = self.table_view.get_all_data()
        if not funds:
            messagebox.showwarning("导出提示", "当前没有可导出的数据。", parent=self.root)
            return

        filepath = filedialog.asksaveasfilename(
            title="导出到 CSV",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
            initialfile=f"基金数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            parent=self.root,
        )

        if not filepath:
            return

        try:
            success = export_to_csv(funds, filepath)
            if success:
                self.status_bar.set_status("CSV 导出成功", "success")
                messagebox.showinfo("导出成功", f"数据已成功导出到：\n{filepath}", parent=self.root)
            else:
                self.status_bar.set_status("CSV 导出失败", "error")
                messagebox.showerror("导出失败", "导出过程中发生错误。", parent=self.root)
        except Exception as e:
            self.status_bar.set_status("CSV 导出失败", "error")
            messagebox.showerror("导出失败", f"导出过程中发生错误：\n{e}", parent=self.root)

    # ============================
    # 主题切换
    # ============================

    def _toggle_theme(self):
        """切换亮色/暗色主题"""
        if self.is_dark_theme:
            self.root.style.theme_use(self.LIGHT_THEME)
            self.is_dark_theme = False
        else:
            self.root.style.theme_use(self.DARK_THEME)
            self.is_dark_theme = True

        # 更新工具栏按钮显示
        self.toolbar.set_theme_button(self.is_dark_theme)

        # 更新表格主题
        self.table_view.update_theme(self.is_dark_theme)

    # ============================
    # 数据源切换
    # ============================

    def _change_source(self):
        """切换数据源"""
        new_source = self.toolbar.get_selected_source()
        self.current_source = new_source
        self.status_bar.set_source(new_source)
        self.status_bar.set_status(f"已切换到数据源: {new_source}", "info")

    # ============================
    # 自动刷新
    # ============================

    def _setup_auto_refresh(self):
        """设置自动刷新定时任务"""
        # 取消之前的定时任务
        if self.auto_refresh_job is not None:
            self.root.after_cancel(self.auto_refresh_job)
            self.auto_refresh_job = None

        interval_min = self.toolbar.get_refresh_interval()

        if interval_min <= 0:
            self.status_bar.set_status("自动刷新已关闭", "info")
            return

        interval_ms = interval_min * 60 * 1000

        def auto_fetch():
            self._fetch_data(is_auto=True)
            # 设置下一次定时
            self.auto_refresh_job = self.root.after(interval_ms, auto_fetch)

        # 设置首次定时
        self.auto_refresh_job = self.root.after(interval_ms, auto_fetch)
        self.status_bar.set_status(f"自动刷新已开启: 每 {interval_min} 分钟", "info")

    # ============================
    # 历史净值查询
    # ============================

    def _show_add_fund_dialog(self):
        """显示添加自选基金弹窗"""
        from gui.dialogs import AddFundDialog
        
        source_name = self.toolbar.get_selected_source()
        source = self.data_sources.get(source_name)
        
        dialog = AddFundDialog(self.root, source)
        self.root.wait_window(dialog)
        
        result = dialog.get_result()
        if result:
            added_funds = []
            # 从数据库获取现有的自选基金代码
            existing_custom = self.db.get_funds(index_type="自选")
            existing_codes = {f["code"] for f in existing_custom}
            
            for fund in result:
                if fund["code"] not in existing_codes:
                    fund["is_custom"] = 1
                    added_funds.append(fund)
                    
            if added_funds:
                messagebox.showinfo("成功", f"成功添加 {len(added_funds)} 只自选基金，正在获取数据...", parent=self.root)
                self._fetch_custom_funds(added_funds, source)
            else:
                messagebox.showinfo("提示", "所选基金已在自选列表中，未重复添加。", parent=self.root)

    def _fetch_custom_funds(self, new_funds, source):
        """后台获取新添加的自选基金数据，并合并到现有列表"""
        self.status_bar.set_status("正在获取自选基金数据...", "info")

        def progress_callback(current, total, message):
            self.root.after(0, self.status_bar.show_progress, current, total, message)

        def fetch_task():
            try:
                custom_funds_data = source.fetch_specific_funds(new_funds, progress_callback=progress_callback)
                if custom_funds_data:
                    for cf in custom_funds_data:
                        cf["is_custom"] = 1
                self.root.after(0, self._on_custom_funds_fetched, custom_funds_data, new_funds)
            except Exception as e:
                self.root.after(0, self.status_bar.set_status, f"获取自选基金失败: {e}", "error")

        thread = threading.Thread(target=fetch_task, daemon=True)
        thread.start()

    def _on_custom_funds_fetched(self, fetched_data, original_funds):
        """自选基金数据获取完成回调（主线程）"""
        existing_codes = {f["code"]: i for i, f in enumerate(self.all_funds)}

        if fetched_data:
            for cf in fetched_data:
                cf["is_custom"] = 1
                if cf["code"] in existing_codes:
                    # 替换已存在的占位记录
                    self.all_funds[existing_codes[cf["code"]]] = cf
                else:
                    self.all_funds.append(cf)
        else:
            # API获取失败，用占位记录填充
            for fund in original_funds:
                if fund["code"] not in existing_codes:
                    self.all_funds.append({
                        "code": fund["code"],
                        "name": fund.get("name", ""),
                        "index_type": fund.get("index_type", ""),
                        "nav": None, "nav_date": "", "acc_nav": None,
                        "daily_change": None, "daily_change_pct": None,
                        "since_inception": None, "purchase_limit": "",
                        "purchase_status": "", "data_source": "",
                        "is_custom": 1,
                    })

        # 保存到数据库
        try:
            self.db.save_funds(self.all_funds)
        except Exception as e:
            print(f"保存数据库失败: {e}")

        # 刷新显示
        self._apply_filter_and_search()
        count = len(fetched_data) if fetched_data else 0
        self.status_bar.set_status(f"已获取 {count} 只自选基金数据", "success")
                
    def _delete_custom_fund(self, fund):
        """删除自选基金"""
        if not fund:
            return
            
        code = fund.get("code")
        name = fund.get("name")
        
        if messagebox.askyesno("删除自选", f"确定要从自选列表中删除 {name} ({code}) 吗？", parent=self.root):
            has_index = False
            for f in self.all_funds:
                if f.get("code") == code:
                    f["is_custom"] = 0
                    if f.get("index_type") and f.get("index_type") != "自选":
                        has_index = True
                    break
            
            # 从数据库中删除或取消自选标记
            try:
                conn = self.db._get_conn()
                cursor = conn.cursor()
                if has_index:
                    cursor.execute("UPDATE funds SET is_custom = 0 WHERE code = ?", (code,))
                else:
                    cursor.execute("DELETE FROM funds WHERE code = ?", (code,))
                    self.all_funds = [f for f in self.all_funds if f.get("code") != code]
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"从数据库删除失败: {e}")
            
            # 刷新显示
            self._apply_filter_and_search()
            messagebox.showinfo("成功", f"已删除自选基金 {name}", parent=self.root)
                    
    def _show_fund_history(self, fund):
        """显示基金历史净值"""
        if not fund:
            return

        code = fund.get("code", "")
        name = fund.get("name", "")

        try:
            history = self.db.get_history(code, limit=30)
        except Exception as e:
            messagebox.showerror(
                "查询失败",
                f"获取历史净值失败：\n{e}",
                parent=self.root,
            )
            return

        if not history:
            messagebox.showinfo(
                "无历史数据",
                f"基金 {code} ({name}) 暂无历史净值数据。\n\n多次获取数据后将自动积累历史记录。",
                parent=self.root,
            )
            return

        HistoryDialog(self.root, code, name, history)
        
    def _show_fund_webview(self, fund):
        """显示基金详情网页弹窗"""
        if not fund:
            return
            
        code = fund.get("code", "")
        name = fund.get("name", "")
        if not code:
            return
            
        url = f"https://fund.eastmoney.com/{code}.html"
        
        # 启动单独的 Python 进程来运行 pywebview，避免阻塞 Tkinter 主循环
        import subprocess
        script = f'''
import webview
import sys
try:
    webview.create_window("{name} ({code}) - 详情", "{url}", width=1280, height=800)
    webview.start()
except Exception as e:
    print(e)
'''
        # CREATE_NO_WINDOW = 0x08000000 避免在 Windows 上弹出黑框命令行
        try:
            subprocess.Popen(["python", "-c", script], creationflags=0x08000000)
        except Exception as e:
            messagebox.showerror("打开网页失败", str(e), parent=self.root)

    # ============================
    # 缓存数据加载
    # ============================

    def _load_cached_data(self):
        """启动时加载本地缓存的数据"""
        try:
            funds = self.db.get_funds(index_type="all")
            if funds:
                self.all_funds = funds
                self.table_view.load_data(funds)
                self._update_stats(funds)

                # 显示上次更新时间
                update_time = self.db.get_last_update_time()
                if update_time:
                    self.status_bar.set_update_time(update_time)

                self.status_bar.set_status(f"已加载缓存数据 ({len(funds)} 只基金)", "success")
            else:
                self.status_bar.set_status("就绪 - 点击「获取数据」开始", "info")
        except Exception as e:
            self.status_bar.set_status(f"加载缓存失败: {e}", "warning")

    # ============================
    # 统计信息更新
    # ============================

    def _update_stats(self, funds):
        """更新统计信息（基金数量、平均日增长率）"""
        self.status_bar.set_fund_count(len(funds))

        # 计算平均日增长率
        pct_values = []
        for f in funds:
            pct = f.get("daily_change_pct")
            if pct is not None:
                try:
                    pct_values.append(float(pct))
                except (ValueError, TypeError):
                    pass

        if pct_values:
            avg_pct = sum(pct_values) / len(pct_values)
            self.status_bar.set_avg_change(avg_pct)
        else:
            self.status_bar.set_avg_change(None)

    # ============================
    # 其他功能
    # ============================

    def _clear_data(self):
        """清空所有数据"""
        if not messagebox.askyesno(
            "确认清空",
            "确定要清空所有基金数据吗？\n\n此操作将清除数据库中的所有记录。",
            parent=self.root,
        ):
            return

        try:
            self.db.clear_funds()
            self.all_funds = []
            self.table_view.load_data([])
            self.status_bar.set_fund_count(0)
            self.status_bar.set_avg_change(None)
            self.status_bar.set_update_time("--")
            self.status_bar.set_status("数据已清空", "success")
        except Exception as e:
            messagebox.showerror("清空失败", f"清空数据时发生错误：\n{e}", parent=self.root)

    def _show_about(self):
        """显示关于对话框"""
        AboutDialog(self.root)

    def _show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self.root)
        self.root.wait_window(dialog)
        result = dialog.get_result()
        if result:
            self.status_bar.set_status("设置已保存", "success")
            # 刷新工具栏过滤按钮
            self.toolbar.rebuild_filters()
            self._apply_filter_and_search()

    def _on_close(self):
        """窗口关闭事件"""
        # 取消自动刷新任务
        if self.auto_refresh_job is not None:
            self.root.after_cancel(self.auto_refresh_job)

        self.root.destroy()

    # ============================
    # 启动
    # ============================

    def run(self):
        """启动应用主循环"""
        self.root.mainloop()
