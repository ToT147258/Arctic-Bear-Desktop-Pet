from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from src.pet_data import TASK_CATALOG


STAT_LABELS = {
    "hunger": "饱食度",
    "mood": "心情值",
    "energy": "体力值",
    "affection": "好感度",
}


class StatusPage(QWidget):
    def __init__(self, store, play_action):
        super().__init__()
        self.store = store
        self.play_action = play_action
        self.progress_bars = {}
        self.task_buttons = {}
        self.level_label = None
        self._build_ui()
        self.store.changed.connect(self.refresh)
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(16)

        title = QLabel("宠物状态与成长任务模块")
        title.setObjectName("pageTitle")
        desc = QLabel("状态会随投喂、互动、睡觉、走路和任务完成而变化，并自动保存到本地存档。")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(desc)

        self.level_label = QLabel()
        self.level_label.setObjectName("levelText")
        layout.addWidget(self.level_label)

        stat_grid = QGridLayout()
        stat_grid.setSpacing(12)
        for index, (key, label) in enumerate(STAT_LABELS.items()):
            stat_grid.addWidget(self._stat_card(key, label), index // 2, index % 2)
        layout.addLayout(stat_grid)

        actions = QGridLayout()
        actions.setSpacing(10)
        action_items = [
            ("完成陪伴任务", self._complete_companion),
            ("恢复体力", self._rest),
            ("增加好感", self._touch),
            ("重置每日任务", self.store.reset_daily_tasks),
        ]
        for index, (label, callback) in enumerate(action_items):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("moduleAction")
            button.clicked.connect(callback)
            actions.addWidget(button, 0, index)
        layout.addLayout(actions)

        section = QLabel("每日任务")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)

        task_grid = QGridLayout()
        task_grid.setSpacing(12)
        for index, (task_id, task) in enumerate(TASK_CATALOG.items()):
            task_grid.addWidget(self._task_card(task_id, task), index // 3, index % 3)
        layout.addLayout(task_grid)
        layout.addStretch()
        self.setStyleSheet(PAGE_STYLE)

    def _stat_card(self, key, label):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        title = QLabel(label)
        title.setObjectName("cardTitle")
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setTextVisible(True)
        bar.setObjectName("statBar")
        self.progress_bars[key] = bar
        layout.addWidget(title)
        layout.addWidget(bar)
        return card

    def _task_card(self, task_id, task):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        title = QLabel(task["title"])
        title.setObjectName("cardTitle")
        reward = QLabel(f"奖励：{task['reward']} 金币 / {task['exp']} 经验")
        reward.setObjectName("taskItem")
        button = QPushButton("完成任务")
        button.setCursor(Qt.PointingHandCursor)
        button.setObjectName("moduleAction")
        button.clicked.connect(lambda checked=False, key=task_id: self.store.complete_task(key))
        self.task_buttons[task_id] = button
        layout.addWidget(title)
        layout.addWidget(reward)
        layout.addWidget(button)
        return card

    def refresh(self):
        stats = self.store.stats
        for key, bar in self.progress_bars.items():
            value = int(stats.get(key, 0))
            bar.setValue(value)
            bar.setFormat(f"{value}%")
        self.level_label.setText(
            f"Lv.{stats.get('level', 1)}  经验 {stats.get('exp', 0)}/100  金币 {stats.get('coins', 0)}"
        )
        for task_id, button in self.task_buttons.items():
            done = bool(self.store.tasks.get(task_id))
            button.setEnabled(not done)
            button.setText("已完成" if done else "完成任务")

    def _complete_companion(self):
        self.store.complete_task("companion")

    def _rest(self):
        self.store.rest()
        self.play_action("sleep", "休息一下，体力恢复。")

    def _touch(self):
        self.store.touch()
        self.play_action("touch", "好感度提升。")


PAGE_STYLE = """
#pageTitle {
    color: #ffffff;
    font-size: 30px;
    font-weight: 800;
}
#pageDescription, #taskItem {
    color: #b8cbda;
    font-size: 14px;
}
#levelText {
    color: #ffffff;
    font-size: 22px;
    font-weight: 900;
}
#sectionTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
}
#moduleCard {
    background: #122237;
    border: 1px solid #2a4c68;
    border-radius: 10px;
    padding: 12px;
}
#cardTitle {
    color: #7ee8ff;
    font-size: 17px;
    font-weight: 800;
}
QProgressBar {
    min-height: 22px;
    color: #ffffff;
    background: #07111f;
    border: 1px solid #284961;
    border-radius: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background: #8df3c8;
    border-radius: 7px;
}
#moduleAction {
    min-height: 38px;
    color: #06111f;
    background: #8df3c8;
    border: 1px solid #8df3c8;
    border-radius: 8px;
    font-weight: 800;
    text-align: center;
}
#moduleAction:disabled {
    color: #6f8793;
    background: #1b2c3d;
    border-color: #284961;
}
QLabel {
    color: #d7e7f3;
}
"""
