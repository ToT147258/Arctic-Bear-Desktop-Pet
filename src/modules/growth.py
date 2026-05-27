from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from src.pet_data import LEVEL_MILESTONES, TASK_CATALOG


class GrowthPage(QWidget):
    def __init__(self, store, play_action):
        super().__init__()
        self.store = store
        self.play_action = play_action
        self.level_label = None
        self.title_label = None
        self.exp_bar = None
        self.affection_bar = None
        self.daily_affection_bar = None
        self.companion_bar = None
        self.rule_label = None
        self.next_unlock_label = None
        self.daily_counts_label = None
        self.route_cards = []
        self.task_rows = {}
        self._build_ui()
        self.store.changed.connect(self.refresh)
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(16)

        title = QLabel("成长等级中心")
        title.setObjectName("pageTitle")
        desc = QLabel("等级、经验、好感上限、每日好感额度和任务奖励都在这里单独管理。普通摸摸不会刷好感，成长需要长期陪伴、完整关怀和任务完成。")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(desc)

        hero = QFrame()
        hero.setObjectName("growthHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(18)

        level_block = QVBoxLayout()
        kicker = QLabel("ARCTIC GROWTH CORE")
        kicker.setObjectName("kicker")
        self.level_label = QLabel()
        self.level_label.setObjectName("heroLevel")
        self.level_label.setWordWrap(True)
        self.title_label = QLabel()
        self.title_label.setObjectName("heroTitleText")
        self.title_label.setWordWrap(True)
        level_block.addWidget(kicker)
        level_block.addWidget(self.level_label)
        level_block.addWidget(self.title_label)
        level_block.addStretch()

        bar_block = QVBoxLayout()
        bar_block.setSpacing(11)
        self.exp_bar = self._progress("升级经验")
        self.affection_bar = self._progress("好感上限")
        self.daily_affection_bar = self._progress("今日好感额度")
        self.companion_bar = self._progress("今日陪伴")
        bar_block.addWidget(self.exp_bar)
        bar_block.addWidget(self.affection_bar)
        bar_block.addWidget(self.daily_affection_bar)
        bar_block.addWidget(self.companion_bar)

        hero_layout.addLayout(level_block, 1)
        hero_layout.addLayout(bar_block, 1)
        layout.addWidget(hero)

        quick_grid = QGridLayout()
        quick_grid.setSpacing(10)
        actions = [
            ("完整关怀", self._daily_care),
            ("领取可领任务", self._claim_ready_tasks),
            ("25 分钟专注", self._start_focus),
            ("安排休息", self._rest),
        ]
        for index, (text, callback) in enumerate(actions):
            button = QPushButton(text)
            button.setObjectName("moduleAction")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(callback)
            quick_grid.addWidget(button, index // 4, index % 4)
        layout.addLayout(quick_grid)

        info_grid = QGridLayout()
        info_grid.setSpacing(12)
        self.rule_label = self._text_card("困难成长规则")
        self.next_unlock_label = self._text_card("下一阶段")
        self.daily_counts_label = self._text_card("今日行为记录")
        info_grid.addWidget(self.rule_label["card"], 0, 0)
        info_grid.addWidget(self.next_unlock_label["card"], 0, 1)
        info_grid.addWidget(self.daily_counts_label["card"], 0, 2)
        layout.addLayout(info_grid)

        route_title = QLabel("等级路线")
        route_title.setObjectName("sectionTitle")
        layout.addWidget(route_title)

        route_grid = QGridLayout()
        route_grid.setSpacing(12)
        for index, milestone in enumerate(LEVEL_MILESTONES):
            card = self._route_card(milestone)
            self.route_cards.append((card, milestone))
            route_grid.addWidget(card, index // 3, index % 3)
        layout.addLayout(route_grid)

        task_title = QLabel("每日成长任务")
        task_title.setObjectName("sectionTitle")
        layout.addWidget(task_title)

        task_grid = QGridLayout()
        task_grid.setSpacing(12)
        for index, (task_id, task) in enumerate(TASK_CATALOG.items()):
            row = self._task_card(task_id, task)
            self.task_rows[task_id] = row
            task_grid.addWidget(row["card"], index // 2, index % 2)
        layout.addLayout(task_grid)
        layout.addStretch()
        self.setStyleSheet(PAGE_STYLE)

    def _progress(self, label):
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setTextVisible(True)
        bar.setObjectName("growthBar")
        bar.setFormat(label)
        return bar

    def _text_card(self, title):
        card = QFrame()
        card.setObjectName("growthCard")
        box = QVBoxLayout(card)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        body = QLabel()
        body.setWordWrap(True)
        body.setObjectName("cardText")
        box.addWidget(heading)
        box.addWidget(body)
        return {"card": card, "body": body}

    def _route_card(self, milestone):
        card = QFrame()
        card.setObjectName("routeCard")
        box = QVBoxLayout(card)
        box.setSpacing(8)
        level = QLabel(f"Lv.{milestone['level']}")
        level.setObjectName("routeLevel")
        title = QLabel(milestone["title"])
        title.setObjectName("routeTitle")
        meta = QLabel(
            f"好感上限 {milestone['affection_ceiling']}%\n每日好感 +{milestone['daily_affection_cap']}"
        )
        meta.setWordWrap(True)
        meta.setObjectName("routeMeta")
        state = QLabel()
        state.setObjectName("routeState")
        card._state_label = state
        box.addWidget(level)
        box.addWidget(title)
        box.addWidget(meta)
        box.addWidget(state)
        return card

    def _task_card(self, task_id, task):
        card = QFrame()
        card.setObjectName("taskCard")
        box = QVBoxLayout(card)
        box.setSpacing(8)
        header = QHBoxLayout()
        title = QLabel(task["title"])
        title.setObjectName("taskTitle")
        badge = QLabel()
        badge.setObjectName("taskBadge")
        header.addWidget(title, 1)
        header.addWidget(badge, 0)
        reward = QLabel(f"奖励 {task['reward']} 金币 / {task['exp']} EXP")
        reward.setObjectName("taskReward")
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setTextVisible(True)
        progress.setObjectName("taskProgress")
        button = QPushButton("领取")
        button.setObjectName("taskButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda checked=False, key=task_id: self._claim_task(key))
        box.addLayout(header)
        box.addWidget(reward)
        box.addWidget(progress)
        box.addWidget(button)
        return {"card": card, "badge": badge, "progress": progress, "button": button}

    def refresh(self):
        stats = self.store.stats
        level = self.store.level_info()
        exp, required = self.store.level_progress()
        affection = self.store.affection_info()
        daily_cap = self.store.daily_affection_cap()
        daily_gain = int(self.store.data.get("daily_counts", {}).get("affection_gain", 0))
        ceiling = max(1, int(level["affection_ceiling"]))
        companion_seconds, companion_goal = self.store.companion_progress()

        self.level_label.setText(f"Lv.{level['level']}")
        self.title_label.setText(
            f"「{level['title']}」\n金币 {stats.get('coins', 0)} · 好感 {affection['value']}% · 陪伴 {self.store.data.get('days', 1)} 天"
        )
        self._set_bar(self.exp_bar, exp, required, f"升级经验 {exp}/{required} EXP")
        self._set_bar(self.affection_bar, affection["value"], ceiling, f"好感上限 {affection['value']}/{ceiling}%")
        self._set_bar(self.daily_affection_bar, daily_gain, daily_cap, f"今日好感 {daily_gain}/{daily_cap}")
        self._set_bar(
            self.companion_bar,
            companion_seconds // 60,
            max(1, companion_goal // 60),
            f"今日陪伴 {companion_seconds // 60}/{max(1, companion_goal // 60)} 分钟",
        )

        self.rule_label["body"].setText(
            "普通触摸只提升心情，不直接增加好感。\n"
            "好感受等级上限和每日上限双重限制。\n"
            "金币主要来自高门槛任务和少量升级奖励，不能快速刷。"
        )
        if level.get("next_milestone"):
            next_item = level["next_milestone"]
            self.next_unlock_label["body"].setText(
                f"Lv.{next_item['level']} 解锁「{next_item['title']}」。\n"
                f"好感上限提升到 {next_item['affection_ceiling']}%，每日好感额度 {next_item['daily_affection_cap']}。"
            )
        else:
            self.next_unlock_label["body"].setText("已经达到当前最高成长档位，继续保持每日陪伴。")
        counts = self.store.data.get("daily_counts", {})
        self.daily_counts_label["body"].setText(
            f"投喂 {counts.get('feed', 0)} 次 / 摸摸 {counts.get('touch', 0)} 次 / 散步 {counts.get('walk', 0)} 次\n"
            f"休息 {counts.get('rest', 0)} 次 / 专注 {counts.get('focus_minutes', 0)} 分钟 / 完整关怀 {counts.get('care', 0)} 次"
        )

        for card, milestone in self.route_cards:
            reached = level["level"] >= milestone["level"]
            card.setProperty("reached", reached)
            card._state_label.setText("已解锁" if reached else "未解锁")
            card.style().unpolish(card)
            card.style().polish(card)

        for task_id, row in self.task_rows.items():
            current, target, label = self.store.task_progress(task_id)
            done = bool(self.store.tasks.get(task_id))
            claimable = self.store.task_claimable(task_id)
            self._set_bar(row["progress"], current, target, label)
            row["badge"].setText("已完成" if done else ("可领取" if claimable else "进行中"))
            row["button"].setEnabled(claimable and not done)
            row["button"].setText("已领取" if done else ("领取奖励" if claimable else "未达成"))

    def _set_bar(self, bar, current, target, text):
        target = max(1, int(target))
        current = max(0, int(current))
        bar.setValue(min(100, int(current / target * 100)))
        bar.setFormat(text)

    def _claim_task(self, task_id):
        ok = self.store.complete_task(task_id)
        message = "奖励已领取。" if ok else "这个任务还没达到领取条件。"
        self.play_action("wave" if ok else "idle", message)

    def _claim_ready_tasks(self):
        claimed = 0
        for task_id in TASK_CATALOG:
            if self.store.task_claimable(task_id) and not self.store.tasks.get(task_id):
                if self.store.complete_task(task_id):
                    claimed += 1
        if claimed:
            self.play_action("wave", f"已领取 {claimed} 个成长任务奖励。")
        else:
            self.play_action("idle", "暂时没有可领取的成长任务。")

    def _daily_care(self):
        ok, message = self.store.daily_care()
        self.play_action("touch" if ok else "idle", message)

    def _start_focus(self):
        self.store.start_focus(25, "成长专注", "focus")
        self.play_action("idle", "25 分钟成长专注已经开始。")

    def _rest(self):
        self.store.rest()
        self.play_action("sleep", "安排一次休息，体力恢复。")


PAGE_STYLE = """
#pageTitle {
    color: #284f66;
    font-size: 30px;
    font-weight: 900;
}
#pageDescription {
    color: #5f7c8d;
    font-size: 15px;
}
#growthHero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f6fdff, stop:0.42 #ffffff, stop:1 #fff0f7);
    border: 1px solid #ace6f4;
    border-radius: 12px;
}
#kicker {
    color: #4cc0dd;
    font-size: 14px;
    font-weight: 900;
}
#heroLevel {
    color: #204c64;
    font-size: 54px;
    font-weight: 900;
}
#heroTitleText {
    color: #315d75;
    font-size: 18px;
    font-weight: 800;
}
#growthCard, #routeCard, #taskCard {
    background: rgba(255, 255, 255, 220);
    border: 1px solid #bde8f4;
    border-radius: 10px;
    padding: 12px;
}
#routeCard[reached="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #effdff, stop:1 #fff5fb);
    border: 1px solid #79d8ec;
}
#cardTitle, #sectionTitle {
    color: #ff8ebc;
    font-size: 18px;
    font-weight: 900;
}
#cardText {
    color: #58788a;
    font-size: 13px;
}
#routeLevel {
    color: #55c0dd;
    font-size: 18px;
    font-weight: 900;
}
#routeTitle {
    color: #254f66;
    font-size: 17px;
    font-weight: 900;
}
#routeMeta, #routeState, #taskReward {
    color: #5d7b8d;
    font-size: 13px;
}
#taskTitle {
    color: #284f66;
    font-size: 16px;
    font-weight: 900;
}
#taskBadge {
    color: #ffffff;
    background: #7fd8cd;
    border-radius: 9px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 900;
}
QProgressBar {
    min-height: 23px;
    color: #284f66;
    background: #e4f5fa;
    border: 1px solid #caeaf3;
    border-radius: 11px;
    text-align: center;
    font-weight: 900;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #62c8e7, stop:0.5 #89dfd1, stop:1 #ffabc8);
    border-radius: 10px;
}
#moduleAction, #taskButton {
    min-height: 38px;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #62c8e7, stop:0.55 #88ddcf, stop:1 #ffabc8);
    border: 1px solid #ffffff;
    border-radius: 14px;
    font-weight: 900;
}
#moduleAction:hover, #taskButton:hover {
    background: #ffd374;
}
#taskButton:disabled {
    color: #88a3b2;
    background: #e9f4f8;
    border-color: #d3e9f0;
}
QLabel {
    color: #31556b;
}
"""
