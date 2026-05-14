from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class InteractionPage(QWidget):
    def __init__(self, pet_window, store, play_action, toggle_pet):
        super().__init__()
        self.pet_window = pet_window
        self.store = store
        self.play_action = play_action
        self.toggle_pet = toggle_pet
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(16)

        title = QLabel("桌宠形象与桌面交互模块")
        title.setObjectName("pageTitle")
        desc = QLabel("这里负责真实动作播放、鼠标交互、右键菜单和主控台触发动作。现在这些按钮会直接驱动悬浮桌宠，并写入任务与日志。")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(desc)

        metrics = QGridLayout()
        metrics.setSpacing(12)
        for index, item in enumerate(
            [
                ("动作组", "8 组", "待机、走路、跳跃、挥手、互动、拖拽、睡觉"),
                ("点击逻辑", "已处理", "单击互动，双击挥手，拖拽不误触发"),
                ("素材来源", "PNG 序列", "兼容旧项目 role/action 动作配置"),
            ]
        ):
            metrics.addWidget(self._metric_card(*item), 0, index)
        layout.addLayout(metrics)

        section = QLabel("动作控制")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)

        grid = QGridLayout()
        grid.setSpacing(12)
        buttons = [
            ("互动", "touch", self._touch),
            ("挥手", "wave", lambda: self._play("wave", "挥手动作已触发。")),
            ("向左走", "walk_left", self._walk_left),
            ("向右走", "walk_right", self._walk_right),
            ("跳跃", "jump", lambda: self._play("jump", "跳跃动作已触发。")),
            ("睡觉", "sleep", self._sleep),
            ("显示/隐藏桌宠", "toggle", self.toggle_pet),
            ("回到待机", "idle", lambda: self._play("idle", "已回到待机状态。")),
        ]
        for index, (label, action_name, callback) in enumerate(buttons):
            grid.addWidget(self._action_card(label, action_name, callback), index // 4, index % 4)
        layout.addLayout(grid)

        note = QLabel("说明：鼠标左键可拖拽桌宠，双击桌宠会挥手，右键菜单可缩放、切换动作和设置走路是否移动窗口。")
        note.setWordWrap(True)
        note.setObjectName("pageDescription")
        layout.addWidget(note)
        layout.addStretch()
        self.setStyleSheet(PAGE_STYLE)

    def _metric_card(self, name, value, note):
        card = QFrame()
        card.setObjectName("highlightCard")
        layout = QVBoxLayout(card)
        title = QLabel(name)
        title.setObjectName("highlightName")
        number = QLabel(value)
        number.setObjectName("highlightValue")
        desc = QLabel(note)
        desc.setWordWrap(True)
        desc.setObjectName("highlightNote")
        layout.addWidget(title)
        layout.addWidget(number)
        layout.addWidget(desc)
        return card

    def _action_card(self, label, action_name, callback):
        button = QPushButton(f"{label}\n{action_name}")
        button.setCursor(Qt.PointingHandCursor)
        button.setObjectName("actionButton")
        button.clicked.connect(callback)
        return button

    def _play(self, action_name, bubble):
        self.play_action(action_name, bubble)

    def _touch(self):
        self.store.touch()
        self._play("touch", "摸摸头，心情变好了。")

    def _walk_left(self):
        self.store.walk()
        self._play("walk_left", "向左走一小段。")

    def _walk_right(self):
        self.store.walk()
        self._play("walk_right", "向右走一小段。")

    def _sleep(self):
        self.store.rest()
        self._play("sleep", "进入休息状态。")


PAGE_STYLE = """
#pageTitle {
    color: #ffffff;
    font-size: 30px;
    font-weight: 800;
}
#pageDescription {
    color: #b8cbda;
    font-size: 15px;
}
#sectionTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
    margin-top: 8px;
}
#highlightCard {
    background: #122237;
    border: 1px solid #2a4c68;
    border-radius: 10px;
    padding: 12px;
}
#highlightName {
    color: #9edff0;
    font-size: 13px;
    font-weight: 800;
}
#highlightValue {
    color: #ffffff;
    font-size: 24px;
    font-weight: 900;
}
#highlightNote {
    color: #b9ccdc;
    font-size: 13px;
}
#actionButton {
    min-height: 76px;
    color: #06111f;
    background: #8df3c8;
    border: 1px solid #8df3c8;
    border-radius: 8px;
    font-weight: 800;
    text-align: center;
}
#actionButton:hover {
    background: #a9ffe0;
}
QLabel {
    color: #d7e7f3;
    font-size: 14px;
}
"""
