import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget

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
        self.exp_bar = None
        self.companion_bar = None
        self.buff_label = None
        self.affection_profile_label = None
        self.daily_counts_label = None
        self._build_ui()
        self.store.changed.connect(self.refresh)
        self.refresh()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScroll")
        content = QWidget()
        layout = QVBoxLayout(content)
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
        self.exp_bar = QProgressBar()
        self.exp_bar.setRange(0, 100)
        self.exp_bar.setTextVisible(True)
        self.exp_bar.setObjectName("statBar")
        layout.addWidget(self.exp_bar)

        companion_card = QFrame()
        companion_card.setObjectName("moduleCard")
        companion_layout = QVBoxLayout(companion_card)
        companion_title = QLabel("今日陪伴进度")
        companion_title.setObjectName("cardTitle")
        self.companion_bar = QProgressBar()
        self.companion_bar.setRange(0, 100)
        self.companion_bar.setTextVisible(True)
        self.companion_bar.setObjectName("statBar")
        companion_layout.addWidget(companion_title)
        companion_layout.addWidget(self.companion_bar)
        layout.addWidget(companion_card)

        profile_grid = QGridLayout()
        profile_grid.setSpacing(12)
        profile_grid.addWidget(self._profile_card("好感档案"), 0, 0)
        profile_grid.addWidget(self._daily_card("今日行为"), 0, 1)
        layout.addLayout(profile_grid)

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
            ("今日关怀", self._daily_care),
            ("亲近互动", self._touch),
            ("重置每日任务", self.store.reset_daily_tasks),
        ]
        for index, (label, callback) in enumerate(action_items):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("moduleAction")
            button.clicked.connect(callback)
            actions.addWidget(button, index // 5, index % 5)
        layout.addLayout(actions)

        self.buff_label = QLabel()
        self.buff_label.setWordWrap(True)
        self.buff_label.setObjectName("buffText")
        layout.addWidget(self.buff_label)

        section = QLabel("每日任务")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)

        task_grid = QGridLayout()
        task_grid.setSpacing(12)
        for index, (task_id, task) in enumerate(TASK_CATALOG.items()):
            task_grid.addWidget(self._task_card(task_id, task), index // 3, index % 3)
        layout.addLayout(task_grid)
        layout.addStretch()
        scroll.setWidget(content)
        root_layout.addWidget(scroll)
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

    def _profile_card(self, title):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        self.affection_profile_label = QLabel()
        self.affection_profile_label.setWordWrap(True)
        self.affection_profile_label.setObjectName("taskItem")
        layout.addWidget(heading)
        layout.addWidget(self.affection_profile_label)
        return card

    def _daily_card(self, title):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        self.daily_counts_label = QLabel()
        self.daily_counts_label.setWordWrap(True)
        self.daily_counts_label.setObjectName("taskItem")
        layout.addWidget(heading)
        layout.addWidget(self.daily_counts_label)
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
        exp, required = self.store.level_progress()
        for key, bar in self.progress_bars.items():
            value = int(stats.get(key, 0))
            bar.setValue(value)
            if key == "affection":
                bar.setFormat(f"{value}% · {self.store.affection_info()['title']}")
            else:
                bar.setFormat(f"{value}%")
        self.level_label.setText(
            f"Lv.{stats.get('level', 1)}  经验 {exp}/{required}  金币 {stats.get('coins', 0)}  陪伴 {self.store.data.get('days', 1)} 天"
        )
        exp_percent = min(100, int(exp / max(1, required) * 100))
        self.exp_bar.setValue(exp_percent)
        self.exp_bar.setFormat(f"升级进度 {exp}/{required}")
        seconds, goal = self.store.companion_progress()
        percent = min(100, int(seconds / goal * 100))
        self.companion_bar.setValue(percent)
        self.companion_bar.setFormat(f"{seconds // 60}/{max(1, goal // 60)} 分钟")
        self._refresh_growth_profile()
        self._refresh_buffs()
        for task_id, button in self.task_buttons.items():
            done = bool(self.store.tasks.get(task_id))
            button.setEnabled(not done)
            button.setText("已完成" if done else "完成任务")

    def _refresh_growth_profile(self):
        affection = self.store.affection_info()
        if affection["to_next"]:
            next_text = f"距离「{affection['next_title']}」还差 {affection['to_next']} 点。"
        else:
            next_text = "好感已经达到最高阶段，继续保持陪伴即可。"
        self.affection_profile_label.setText(
            f"当前阶段：{affection['title']}（{affection['value']}%）。{next_text}\n{affection['description']}"
        )
        counts = self.store.data.get("daily_counts", {})
        self.daily_counts_label.setText(
            "今日互动："
            f"摸摸 {counts.get('touch', 0)} 次 / "
            f"投喂 {counts.get('feed', 0)} 次 / "
            f"散步 {counts.get('walk', 0)} 次 / "
            f"休息 {counts.get('rest', 0)} 次 / "
            f"专注 {counts.get('focus', 0)} 次"
        )

    def _refresh_buffs(self):
        buffs = []
        for buff in self.store.active_buffs.values():
            remaining = max(0, int(buff.get("expires_at", 0)) - int(time.time()))
            buffs.append(f"{buff.get('name')}：{remaining // 60}分{remaining % 60}秒")
        if buffs:
            self.buff_label.setText("当前增益：" + "；".join(buffs))
        else:
            self.buff_label.setText("当前增益：暂无")

    def _complete_companion(self):
        self.store.complete_task("companion")

    def _rest(self):
        self.store.rest()
        self.play_action("sleep", "休息一下，体力恢复。")

    def _daily_care(self):
        ok, message = self.store.daily_care()
        self.play_action("touch" if ok else "idle", message)

    def _touch(self):
        self.store.touch()
        self.play_action("touch", "亲近互动已触发，今日好感收益会逐步放缓。")


PAGE_STYLE = """
#pageTitle {
    color: #284f66;
    font-size: 28px;
    font-weight: 900;
}
#pageScroll {
    background: transparent;
    border: none;
}
#pageDescription, #taskItem, #buffText {
    color: #5f7c8d;
    font-size: 14px;
}
#levelText {
    color: #294f66;
    font-size: 22px;
    font-weight: 900;
}
#sectionTitle {
    color: #2d566d;
    font-size: 18px;
    font-weight: 900;
}
#moduleCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #edfaff);
    border: 1px solid #c4e5ef;
    border-radius: 8px;
    padding: 12px;
}
#cardTitle {
    color: #ff8ebc;
    font-size: 17px;
    font-weight: 900;
}
QProgressBar {
    min-height: 22px;
    color: #294f66;
    background: #dceff5;
    border: 1px solid #c7e4ef;
    border-radius: 11px;
    text-align: center;
    font-weight: 800;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffabc8, stop:0.45 #ffd374, stop:0.72 #8de1d0, stop:1 #63c7e7);
    border-radius: 10px;
}
#moduleAction {
    min-height: 38px;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #64c9e8, stop:1 #ffadc8);
    border: 1px solid #ffffff;
    border-radius: 14px;
    font-weight: 900;
    text-align: center;
}
#moduleAction:hover {
    background: #d8b45c;
}
#moduleAction:disabled {
    color: #8fa8b7;
    background: #e9f4f8;
    border-color: #d1e7ee;
}
QLabel {
    color: #31556b;
}
"""
