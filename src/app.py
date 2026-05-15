import random
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.modules.backpack import BackpackPage
from src.modules.interaction import InteractionPage
from src.modules.notification import NotificationPage
from src.modules.settings import SettingsPage
from src.modules.status import StatusPage
from src.pet_data import PetDataStore
from src.pet_window import PolarBearPetWindow


class PolarBearPetApp(QMainWindow):
    """北极熊桌宠桌面应用主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("北极熊桌面宠物系统")
        self.resize(1180, 760)
        self.store = PetDataStore()
        self.pet_window = PolarBearPetWindow()
        self.pet_window.setWindowOpacity(float(self.store.settings.get("opacity", 1.0)))
        self.pet_window.set_always_on_top(bool(self.store.settings.get("always_on_top", True)))
        self.pet_window.set_edge_snap(
            bool(self.store.settings.get("edge_snap_enabled", True)),
            int(self.store.settings.get("edge_snap_threshold", 48)),
        )
        self.pet_window.interaction_requested.connect(self._handle_pet_window_interaction)
        self.nav_buttons = []
        self.metric_value_labels = {}
        self.metric_bars = {}
        self.hero_status_label = None
        self.focus_summary_label = None
        self.today_summary_label = None
        self.growth_summary_label = None
        self.recent_log_labels = []
        self.tray_icon = None
        self._touch_burst_count = 0
        self._touch_burst_timer = QTimer(self)
        self._touch_burst_timer.setSingleShot(True)
        self._touch_burst_timer.timeout.connect(self._reset_touch_burst)
        self._build_ui()
        self._build_tray()
        self._life_timer = QTimer(self)
        self._life_timer.setTimerType(Qt.PreciseTimer)
        self._life_timer.timeout.connect(self._tick_pet_life)
        self._life_timer.start(60000)
        self._focus_timer = QTimer(self)
        self._focus_timer.setTimerType(Qt.PreciseTimer)
        self._focus_timer.timeout.connect(self._tick_focus_session)
        self._focus_timer.start(1000)
        self.store.changed.connect(self._refresh_overview)
        self._show_tick_messages(self.store.tick())
        self._refresh_overview()

    def _build_ui(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = self._build_sidebar()
        self.stack = QStackedWidget()
        pages = [
            ("总览工作台", self._build_overview_page()),
            ("桌宠交互", InteractionPage(self.pet_window, self.store, self._play_pet_action, self.toggle_pet_window)),
            ("状态成长", StatusPage(self.store, self._play_pet_action)),
            ("背包喂养", BackpackPage(self.store, self._play_pet_action)),
            ("系统设置", SettingsPage(self.store, self.pet_window)),
            ("通知日志", NotificationPage(self.store, self.pet_window)),
        ]

        for index, (name, page) in enumerate(pages):
            button = QPushButton(name)
            button.setCursor(Qt.PointingHandCursor)
            button.setProperty("nav", True)
            button.clicked.connect(lambda checked=False, i=index: self._switch_page(i))
            self.nav_buttons.append(button)
            sidebar.layout().addWidget(button)
            self.stack.addWidget(page)

        sidebar.layout().addStretch()
        layout.addWidget(sidebar, 0)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.setStyleSheet(APP_STYLE)
        self._switch_page(0)

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 22, 18, 22)
        sidebar_layout.setSpacing(12)

        title = QLabel("PolarBear")
        title.setObjectName("brandTitle")
        subtitle = QLabel("桌面宠物应用")
        subtitle.setObjectName("brandSubTitle")
        status = QLabel("实时陪伴控制台")
        status.setObjectName("brandStatus")
        sidebar_layout.addWidget(title)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addWidget(status)

        pet_button = QPushButton("显示 / 隐藏桌宠")
        pet_button.setCursor(Qt.PointingHandCursor)
        pet_button.setObjectName("petToggleButton")
        pet_button.clicked.connect(self.toggle_pet_window)
        sidebar_layout.addWidget(pet_button)
        return sidebar

    def _build_overview_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28, 24, 28, 24)
        hero_layout.setSpacing(20)

        hero_text = QVBoxLayout()
        eyebrow = QLabel("POLAR COMPANION")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("北极熊桌宠控制台")
        title.setObjectName("heroTitle")
        desc = QLabel("当前已经接入真实北极熊序列帧、动作控制、状态成长、背包投喂、本地存档和通知日志。主控台中的操作会直接影响桌宠表现。")
        desc.setWordWrap(True)
        desc.setObjectName("heroDesc")
        hero_text.addWidget(eyebrow)
        hero_text.addWidget(title)
        hero_text.addWidget(desc)
        self.hero_status_label = QLabel()
        self.hero_status_label.setObjectName("heroStatus")
        hero_text.addWidget(self.hero_status_label)

        actions = QVBoxLayout()
        actions.setSpacing(10)
        show_pet = QPushButton("唤出桌宠")
        show_pet.clicked.connect(self.toggle_pet_window)
        show_pet.setObjectName("primaryAction")
        interact = QPushButton("触发互动")
        interact.setObjectName("heroAction")
        interact.clicked.connect(self._trigger_pet_interaction)
        focus = QPushButton("开始专注")
        focus.setObjectName("heroAction")
        focus.clicked.connect(self._start_focus_from_tray)
        actions.addWidget(show_pet)
        actions.addWidget(interact)
        actions.addWidget(focus)
        actions.addStretch()

        hero_layout.addLayout(hero_text, 1)
        hero_layout.addLayout(actions, 0)
        layout.addWidget(hero)

        metrics = QGridLayout()
        metrics.setSpacing(14)
        metric_data = [
            ("hunger", "饱食度", "0%", "投喂食物可恢复", 0),
            ("mood", "心情值", "0%", "互动和玩具会提升", 0),
            ("energy", "体力值", "0%", "睡觉和短休可恢复", 0),
            ("affection", "好感度", "0%", "分阶段成长并解锁奖励", 0),
        ]
        for index, item in enumerate(metric_data):
            metrics.addWidget(self._metric_card(*item), index // 4, index % 4)
        layout.addLayout(metrics)

        content = QHBoxLayout()
        content.setSpacing(16)
        self.today_summary_label = QLabel()
        self.today_summary_label.setObjectName("panelText")
        self.today_summary_label.setWordWrap(True)
        self.focus_summary_label = QLabel()
        self.focus_summary_label.setObjectName("panelText")
        self.focus_summary_label.setWordWrap(True)
        self.growth_summary_label = QLabel()
        self.growth_summary_label.setObjectName("panelText")
        self.growth_summary_label.setWordWrap(True)
        content.addWidget(self._info_panel("今日概况", [
            self.today_summary_label,
            self.growth_summary_label,
            self.focus_summary_label,
            "状态、任务、背包和专注记录会自动保存",
        ]), 1)
        content.addWidget(self._info_panel("快捷入口", [
            "侧边栏可切换交互、状态、背包、设置和日志",
            "托盘菜单可快速投喂、休息和开始专注",
            "右键桌宠可切换动作与缩放",
        ]), 1)
        recent_panel = QFrame()
        recent_panel.setObjectName("infoPanel")
        recent_layout = QVBoxLayout(recent_panel)
        recent_heading = QLabel("最近日志")
        recent_heading.setObjectName("panelTitle")
        recent_layout.addWidget(recent_heading)
        for _ in range(4):
            label = QLabel()
            label.setObjectName("panelText")
            label.setWordWrap(True)
            self.recent_log_labels.append(label)
            recent_layout.addWidget(label)
        recent_layout.addStretch()
        content.addWidget(recent_panel, 1)
        layout.addLayout(content)
        layout.addStretch()
        return page

    def _metric_card(self, key, name, value, note, progress):
        card = QFrame()
        card.setObjectName("metricCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        title = QLabel(name)
        title.setObjectName("metricName")
        number = QLabel(value)
        number.setObjectName("metricValue")
        self.metric_value_labels[key] = number
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(progress)
        bar.setTextVisible(False)
        bar.setObjectName("metricBar")
        self.metric_bars[key] = bar
        desc = QLabel(note)
        desc.setObjectName("metricNote")
        desc.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(number)
        layout.addWidget(bar)
        layout.addWidget(desc)
        return card

    def _info_panel(self, title, rows):
        panel = QFrame()
        panel.setObjectName("infoPanel")
        layout = QVBoxLayout(panel)
        heading = QLabel(title)
        heading.setObjectName("panelTitle")
        layout.addWidget(heading)
        for row in rows:
            if isinstance(row, QLabel):
                layout.addWidget(row)
            else:
                label = QLabel(f"- {row}")
                label.setWordWrap(True)
                label.setObjectName("panelText")
                layout.addWidget(label)
        layout.addStretch()
        return panel

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setProperty("active", i == index)
            button.style().unpolish(button)
            button.style().polish(button)

    def _trigger_pet_interaction(self):
        self.store.touch()
        self._register_touch_burst()
        self._play_pet_action("touch", "触发互动，心情和好感都提升了。")

    def _play_pet_action(self, action_name, bubble=None):
        if not self.pet_window.isVisible():
            self.pet_window.show()
        self.pet_window.raise_()
        self.pet_window.play_action(action_name)
        if bubble and self.store.settings.get("bubble_on", True):
            self.pet_window.show_bubble(bubble)
        self.pet_window.update()

    def _handle_pet_window_interaction(self, action_name):
        if action_name == "touch":
            self.store.touch()
            self._register_touch_burst()
            self._show_bubble("摸摸头，心情变好了。")
        elif action_name == "wave":
            self.store.add_log("互动", "桌宠挥了挥手。")
            self._show_bubble("我在这里。")
        elif action_name in {"walk_left", "walk_right"}:
            self.store.walk()
            self._show_bubble("散步一小段。")
        elif action_name == "sleep":
            self.store.rest()
            self._show_bubble("准备休息一下。")
        elif action_name == "jump":
            self.store.adjust_stats({"mood": 4, "energy": -2})
            self.store.add_log("互动", "触发了跳跃动作。")
        elif action_name == "drag":
            self.store.add_log("互动", "开始拖拽桌宠。")
        elif action_name == "drag_end":
            self.store.add_log("互动", "拖拽结束，位置已更新。")

    def _register_touch_burst(self):
        self._touch_burst_count += 1
        self._touch_burst_timer.start(2500)
        threshold = int(self.store.settings.get("pat_multi_click_talk_threshold", 6))
        if self._touch_burst_count < threshold:
            return
        self._touch_burst_count = 0
        message = random.choice(
            [
                "我在，我在，别急。",
                "今天的互动量达标了。",
                "再摸就要收小鱼了。",
                "收到，陪伴信号很强。",
            ]
        )
        self.store.add_log("互动", "连续点击触发了亲近反馈。")
        self._show_bubble(message)

    def _reset_touch_burst(self):
        self._touch_burst_count = 0

    def _show_bubble(self, message):
        if message and self.store.settings.get("bubble_on", True):
            self.pet_window.show_bubble(message)

    def _tick_pet_life(self):
        self._show_tick_messages(self.store.tick())

    def _tick_focus_session(self):
        message = self.store.tick_focus()
        if message:
            self._play_pet_action("wave", message)

    def _show_tick_messages(self, messages):
        for message in messages[:1]:
            self._show_bubble(message)

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "polar_bear" / "polar-bear-realistic.png"
        self.tray_icon = QSystemTrayIcon(QIcon(str(icon_path)), self)
        self.tray_icon.setToolTip("北极熊桌面宠物")

        menu = QMenu()
        show_console = QAction("显示控制台", self)
        show_console.triggered.connect(self._show_console)
        toggle_pet = QAction("显示 / 隐藏桌宠", self)
        toggle_pet.triggered.connect(self.toggle_pet_window)
        feed = QAction("投喂小鱼", self)
        feed.triggered.connect(lambda: self._feed_from_tray("fish"))
        focus = QAction("开始 25 分钟专注", self)
        focus.triggered.connect(self._start_focus_from_tray)
        cancel_focus = QAction("取消专注", self)
        cancel_focus.triggered.connect(self._cancel_focus_from_tray)
        rest = QAction("休息一下", self)
        rest.triggered.connect(self._rest_from_tray)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)

        for action in (show_console, toggle_pet, feed, focus, cancel_focus, rest):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._handle_tray_activated)
        self.tray_icon.show()

    def _show_console(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _handle_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._show_console()

    def _feed_from_tray(self, item_id):
        ok, message = self.store.feed(item_id)
        self._play_pet_action("touch" if ok else "idle", message)

    def _rest_from_tray(self):
        self.store.rest()
        self._play_pet_action("sleep", "进入休息状态。")

    def _start_focus_from_tray(self):
        self.store.start_focus(25, "托盘专注", "focus")
        self._play_pet_action("idle", "专注计时已经开始。")

    def _cancel_focus_from_tray(self):
        self.store.cancel_focus()
        self._play_pet_action("idle", "专注计时已取消。")

    def _refresh_overview(self):
        stats = self.store.stats
        for key in ("hunger", "mood", "energy", "affection"):
            label = self.metric_value_labels.get(key)
            if label:
                label.setText(f"{stats.get(key, 0)}%")
            bar = self.metric_bars.get(key)
            if bar:
                bar.setValue(int(stats.get(key, 0)))
        done = sum(1 for value in self.store.tasks.values() if value)
        total = len(self.store.tasks)
        seconds, goal = self.store.companion_progress()
        focus_done, focus_total, focus_text = self.store.focus_progress()
        exp, required = self.store.level_progress()
        affection = self.store.affection_info()
        if self.hero_status_label:
            self.hero_status_label.setText(
                f"Lv.{stats.get('level', 1)} {exp}/{required} EXP / 好感 {affection['title']} / 金币 {stats.get('coins', 0)} / 任务 {done}/{total}"
            )
        if self.today_summary_label:
            self.today_summary_label.setText(
                f"陪伴 {seconds // 60}/{max(1, goal // 60)} 分钟，今日任务完成 {done}/{total}。"
            )
        if self.growth_summary_label:
            if affection["to_next"]:
                affection_text = f"距离「{affection['next_title']}」还差 {affection['to_next']} 点好感。"
            else:
                affection_text = "好感已达最高阶段。"
            self.growth_summary_label.setText(f"成长：{self.store.growth_summary()} {affection_text}")
        if self.focus_summary_label:
            if focus_total:
                percent = min(100, int(focus_done / focus_total * 100))
                self.focus_summary_label.setText(f"专注：{focus_text}，进度 {percent}%。")
            else:
                self.focus_summary_label.setText("专注：暂无计时，可从首页、通知页或托盘开始。")
        for index, label in enumerate(self.recent_log_labels):
            text = self.store.logs[index] if index < len(self.store.logs) else "暂无更多日志"
            label.setText(f"- {text}")

    def showEvent(self, event):
        super().showEvent(event)
        if not self.pet_window.isVisible():
            self.pet_window.move(self.x() + self.width() - self.pet_window.width() - 24, self.y() + 100)
            self.pet_window.show()

    def closeEvent(self, event):
        self.store.save()
        self.pet_window.close()
        super().closeEvent(event)

    def toggle_pet_window(self):
        if self.pet_window.isVisible():
            self.pet_window.hide()
        else:
            self.pet_window.show()
            self.pet_window.raise_()


APP_STYLE = """
QMainWindow {
    background: #081018;
}
#sidebar {
    min-width: 238px;
    max-width: 238px;
    background: #0d1824;
    border-right: 1px solid #263847;
}
#brandTitle {
    color: #f5fbff;
    font-size: 30px;
    font-weight: 900;
    margin-bottom: 2px;
}
#brandSubTitle {
    color: #9bc7d5;
    font-size: 14px;
}
#brandStatus {
    color: #0b181d;
    background: #a6f0cf;
    border: 1px solid #a6f0cf;
    border-radius: 8px;
    padding: 8px 10px;
    margin-top: 8px;
    margin-bottom: 12px;
    font-weight: 800;
}
QPushButton {
    min-height: 40px;
    color: #d8e8f0;
    background: #142333;
    border: 1px solid #294155;
    border-radius: 8px;
    text-align: left;
    padding-left: 13px;
    padding-right: 13px;
}
QPushButton:hover {
    color: #ffffff;
    background: #1c3345;
    border-color: #68d8e8;
}
QPushButton[active="true"] {
    color: #081018;
    background: #8ee6f1;
    border-color: #8ee6f1;
    font-weight: 800;
}
#petToggleButton {
    color: #081018;
    background: #a6f0cf;
    border-color: #a6f0cf;
    font-weight: 800;
}
#primaryAction {
    min-width: 156px;
    color: #081018;
    background: #f2c66d;
    border-color: #f2c66d;
    font-weight: 900;
    text-align: center;
}
#heroAction {
    min-width: 156px;
    color: #e8f5f8;
    background: #172a3a;
    border-color: #38566a;
    font-weight: 800;
    text-align: center;
}
#heroPanel {
    background: #101d29;
    border: 1px solid #2b4052;
    border-radius: 8px;
}
#metricCard, #infoPanel {
    background: #111f2b;
    border: 1px solid #2a4052;
    border-radius: 8px;
}
#eyebrow {
    color: #8ee6f1;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0px;
}
#heroTitle {
    color: #ffffff;
    font-size: 32px;
    font-weight: 900;
}
#heroDesc {
    color: #b8cbd6;
    font-size: 14px;
}
#heroStatus {
    color: #f5d88a;
    background: #201c13;
    border: 1px solid #6d5626;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 13px;
    font-weight: 800;
}
#panelText, #metricNote {
    color: #b7c8d1;
    font-size: 14px;
}
#metricName {
    color: #9bc7d5;
    font-size: 13px;
    font-weight: 800;
}
#metricValue {
    color: #ffffff;
    font-size: 27px;
    font-weight: 900;
}
#metricBar {
    min-height: 8px;
    max-height: 8px;
    background: #0a141d;
    border: 1px solid #263847;
    border-radius: 4px;
}
#metricBar::chunk {
    background: #a6f0cf;
    border-radius: 3px;
}
#panelTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
}
QStackedWidget {
    background: #081018;
}
QLabel {
    color: #ecf7ff;
}
"""
