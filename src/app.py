from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
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
        self.nav_buttons = []
        self.metric_value_labels = {}
        self._build_ui()
        self.store.changed.connect(self._refresh_overview)
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
        status = QLabel("中期原型 · PySide6")
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

        actions = QVBoxLayout()
        show_pet = QPushButton("唤出桌宠")
        show_pet.clicked.connect(self.toggle_pet_window)
        show_pet.setObjectName("primaryAction")
        interact = QPushButton("触发互动")
        interact.clicked.connect(self._trigger_pet_interaction)
        actions.addWidget(show_pet)
        actions.addWidget(interact)
        actions.addStretch()

        hero_layout.addLayout(hero_text, 1)
        hero_layout.addLayout(actions, 0)
        layout.addWidget(hero)

        metrics = QGridLayout()
        metrics.setSpacing(14)
        metric_data = [
            ("hunger", "饱食度", "0%", "投喂食物可恢复"),
            ("mood", "心情值", "0%", "互动和玩具会提升"),
            ("affection", "好感度", "0%", "陪伴与礼物会提升"),
            ("tasks", "任务进度", "0 / 0", "每日任务与奖励"),
        ]
        for index, item in enumerate(metric_data):
            metrics.addWidget(self._metric_card(*item), index // 4, index % 4)
        layout.addLayout(metrics)

        content = QHBoxLayout()
        content.setSpacing(16)
        content.addWidget(self._info_panel("中期已完成", [
            "完成 PySide6 控制台与悬浮桌宠",
            "接入真实北极熊 PNG 序列帧动作",
            "完成缩放、拖拽、右键菜单和动作过渡",
            "整理五大模块文档和 UML 图讲解",
        ]), 1)
        content.addWidget(self._info_panel("当前功能重点", [
            "状态、背包、任务和日志已联动",
            "设置页可控制缩放、透明度和置顶",
            "投喂、互动、睡觉会影响状态",
            "数据会保存到本地 JSON 存档",
        ]), 1)
        content.addWidget(self._info_panel("最近事件", [
            "桌宠窗口已启动",
            "待机眨眼微动持续运行",
            "动作按钮可直接触发桌宠",
            "通知页可查看操作日志",
        ]), 1)
        layout.addLayout(content)
        layout.addStretch()
        return page

    def _metric_card(self, key, name, value, note):
        card = QFrame()
        card.setObjectName("metricCard")
        layout = QVBoxLayout(card)
        title = QLabel(name)
        title.setObjectName("metricName")
        number = QLabel(value)
        number.setObjectName("metricValue")
        self.metric_value_labels[key] = number
        desc = QLabel(note)
        desc.setObjectName("metricNote")
        desc.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(number)
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
            label = QLabel(f"• {row}")
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
        self._play_pet_action("touch", "触发互动，心情和好感都提升了。")

    def _play_pet_action(self, action_name, bubble=None):
        if not self.pet_window.isVisible():
            self.pet_window.show()
        self.pet_window.raise_()
        self.pet_window.play_action(action_name)
        if bubble:
            self.pet_window.show_bubble(bubble)
        self.pet_window.update()

    def _refresh_overview(self):
        stats = self.store.stats
        for key in ("hunger", "mood", "affection"):
            label = self.metric_value_labels.get(key)
            if label:
                label.setText(f"{stats.get(key, 0)}%")
        task_label = self.metric_value_labels.get("tasks")
        if task_label:
            done = sum(1 for value in self.store.tasks.values() if value)
            total = len(self.store.tasks)
            task_label.setText(f"{done} / {total}")

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
    background: #07111f;
}
#sidebar {
    min-width: 232px;
    max-width: 232px;
    background: #0f1d2f;
    border-right: 1px solid #25425d;
}
#brandTitle {
    color: #f7fbff;
    font-size: 29px;
    font-weight: 900;
}
#brandSubTitle {
    color: #9edff0;
    font-size: 14px;
}
#brandStatus {
    color: #89f3c6;
    background: #132b38;
    border: 1px solid #2f6f77;
    border-radius: 8px;
    padding: 7px 10px;
    margin-bottom: 10px;
}
QPushButton {
    min-height: 42px;
    color: #dcefff;
    background: #17283c;
    border: 1px solid #2c4c68;
    border-radius: 8px;
    text-align: left;
    padding-left: 14px;
}
QPushButton:hover {
    background: #1d3853;
    border-color: #62dff5;
}
QPushButton[active="true"] {
    color: #06111f;
    background: #83eaff;
    border-color: #83eaff;
    font-weight: 800;
}
#petToggleButton, #primaryAction {
    color: #06111f;
    background: #8df3c8;
    border-color: #8df3c8;
    font-weight: 800;
}
#heroPanel, #metricCard, #infoPanel {
    background: #102238;
    border: 1px solid #2b4f6c;
    border-radius: 12px;
}
#eyebrow {
    color: #83eaff;
    font-size: 12px;
    font-weight: 800;
}
#heroTitle {
    color: #ffffff;
    font-size: 34px;
    font-weight: 900;
}
#heroDesc, #panelText, #metricNote {
    color: #b9ccdc;
    font-size: 14px;
}
#metricName {
    color: #9edff0;
    font-size: 13px;
    font-weight: 800;
}
#metricValue {
    color: #ffffff;
    font-size: 28px;
    font-weight: 900;
}
#panelTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
}
QLabel {
    color: #ecf7ff;
}
"""
