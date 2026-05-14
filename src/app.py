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
from src.pet_window import PolarBearPetWindow


class PolarBearPetApp(QMainWindow):
    """北极熊桌宠桌面应用主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("北极熊桌面宠物系统")
        self.resize(1180, 760)
        self.pet_window = PolarBearPetWindow()
        self.nav_buttons = []
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = self._build_sidebar()
        self.stack = QStackedWidget()
        pages = [
            ("总览工作台", self._build_overview_page()),
            ("桌宠交互", InteractionPage()),
            ("状态成长", StatusPage()),
            ("背包喂养", BackpackPage()),
            ("系统设置", SettingsPage()),
            ("通知日志", NotificationPage()),
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
        desc = QLabel("当前已经完成桌面应用骨架、悬浮桌宠窗口、五大模块页面和中期 UML 设计说明。后续将继续接入动作系统、状态联动和大模型智能陪伴。")
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
            ("饱食度", "86%", "投喂模块后续联动"),
            ("心情值", "92%", "互动反馈已规划"),
            ("好感度", "68%", "成长系统待实现"),
            ("任务进度", "3 / 5", "中期任务原型"),
        ]
        for index, item in enumerate(metric_data):
            metrics.addWidget(self._metric_card(*item), index // 4, index % 4)
        layout.addLayout(metrics)

        content = QHBoxLayout()
        content.setSpacing(16)
        content.addWidget(self._info_panel("中期已完成", [
            "新建 PySide6 桌面应用项目",
            "完成控制台主窗口和悬浮桌宠窗口",
            "接入半扁平北极熊 PNG 素材",
            "整理五大模块文档和 UML 图讲解",
        ]), 1)
        content.addWidget(self._info_panel("后续开发重点", [
            "补充北极熊动作素材和动作播放",
            "实现状态、背包、任务的数据联动",
            "加入本地存档和系统托盘",
            "接入大模型聊天与学习陪伴",
        ]), 1)
        content.addWidget(self._info_panel("最近事件", [
            "桌宠窗口已启动",
            "呼吸动画运行中",
            "模块文档已更新",
            "等待接入更多功能逻辑",
        ]), 1)
        layout.addLayout(content)
        layout.addStretch()
        return page

    def _metric_card(self, name, value, note):
        card = QFrame()
        card.setObjectName("metricCard")
        layout = QVBoxLayout(card)
        title = QLabel(name)
        title.setObjectName("metricName")
        number = QLabel(value)
        number.setObjectName("metricValue")
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
        if not self.pet_window.isVisible():
            self.pet_window.show()
            self.pet_window.raise_()
        self.pet_window.play_action("wave")
        self.pet_window.update()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.pet_window.isVisible():
            self.pet_window.move(self.x() + self.width() - self.pet_window.width() - 24, self.y() + 100)
            self.pet_window.show()

    def closeEvent(self, event):
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
