import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget

from src.pet_data import LEVEL_MILESTONES, TASK_CATALOG


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
        self.task_progress_labels = {}
        self.level_label = None
        self.exp_bar = None
        self.sidebar_affection_bar = None
        self.daily_affection_bar = None
        self.next_unlock_label = None
        self.growth_route_label = None
        self.companion_bar = None
        self.buff_label = None
        self.level_profile_label = None
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

        body = QHBoxLayout()
        body.setSpacing(18)
        main_column = QVBoxLayout()
        main_column.setSpacing(16)

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
        main_column.addWidget(companion_card)

        profile_grid = QGridLayout()
        profile_grid.setSpacing(12)
        profile_grid.addWidget(self._profile_card("好感档案"), 0, 0)
        profile_grid.addWidget(self._daily_card("今日行为"), 0, 1)
        main_column.addLayout(profile_grid)

        stat_grid = QGridLayout()
        stat_grid.setSpacing(12)
        for index, (key, label) in enumerate(STAT_LABELS.items()):
            stat_grid.addWidget(self._stat_card(key, label), index // 2, index % 2)
        main_column.addLayout(stat_grid)

        actions = QGridLayout()
        actions.setSpacing(10)
        action_items = [
            ("完成陪伴任务", self._complete_companion),
            ("恢复体力", self._rest),
            ("今日关怀", self._daily_care),
            ("温柔互动", self._touch),
        ]
        for index, (label, callback) in enumerate(action_items):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("moduleAction")
            button.clicked.connect(callback)
            actions.addWidget(button, index // 5, index % 5)
        main_column.addLayout(actions)

        self.buff_label = QLabel()
        self.buff_label.setWordWrap(True)
        self.buff_label.setObjectName("buffText")
        main_column.addWidget(self.buff_label)

        section = QLabel("每日任务")
        section.setObjectName("sectionTitle")
        main_column.addWidget(section)

        task_grid = QGridLayout()
        task_grid.setSpacing(12)
        for index, (task_id, task) in enumerate(TASK_CATALOG.items()):
            task_grid.addWidget(self._task_card(task_id, task), index // 3, index % 3)
        main_column.addLayout(task_grid)
        main_column.addStretch()
        body.addLayout(main_column, 1)
        body.addWidget(self._growth_sidebar())
        layout.addLayout(body)
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

    def _growth_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("growthSidebar")
        sidebar.setMinimumWidth(280)
        sidebar.setMaximumWidth(330)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        heading = QLabel("成长侧栏")
        heading.setObjectName("growthTitle")
        self.level_label = QLabel()
        self.level_label.setWordWrap(True)
        self.level_label.setObjectName("levelHeroText")

        self.exp_bar = QProgressBar()
        self.exp_bar.setRange(0, 100)
        self.exp_bar.setTextVisible(True)
        self.exp_bar.setObjectName("growthBar")

        self.sidebar_affection_bar = QProgressBar()
        self.sidebar_affection_bar.setRange(0, 100)
        self.sidebar_affection_bar.setTextVisible(True)
        self.sidebar_affection_bar.setObjectName("growthBar")

        self.daily_affection_bar = QProgressBar()
        self.daily_affection_bar.setRange(0, 100)
        self.daily_affection_bar.setTextVisible(True)
        self.daily_affection_bar.setObjectName("growthBar")

        self.level_profile_label = QLabel()
        self.level_profile_label.setWordWrap(True)
        self.level_profile_label.setObjectName("sideLabel")

        self.next_unlock_label = QLabel()
        self.next_unlock_label.setWordWrap(True)
        self.next_unlock_label.setObjectName("unlockPill")

        route_title = QLabel("等级路线")
        route_title.setObjectName("sideSectionTitle")
        self.growth_route_label = QLabel()
        self.growth_route_label.setWordWrap(True)
        self.growth_route_label.setObjectName("routeText")

        layout.addWidget(heading)
        layout.addWidget(self.level_label)
        layout.addWidget(self.exp_bar)
        layout.addWidget(self.sidebar_affection_bar)
        layout.addWidget(self.daily_affection_bar)
        layout.addWidget(self.level_profile_label)
        layout.addWidget(self.next_unlock_label)
        layout.addWidget(route_title)
        layout.addWidget(self.growth_route_label)
        layout.addStretch()
        return sidebar

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
        progress = QLabel()
        progress.setObjectName("taskItem")
        button = QPushButton("领取奖励")
        button.setCursor(Qt.PointingHandCursor)
        button.setObjectName("moduleAction")
        button.clicked.connect(lambda checked=False, key=task_id: self.store.complete_task(key))
        self.task_buttons[task_id] = button
        self.task_progress_labels[task_id] = progress
        layout.addWidget(title)
        layout.addWidget(reward)
        layout.addWidget(progress)
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
        level = self.store.level_info()
        self.level_label.setText(
            f"Lv.{level['level']}\n「{level['title']}」\n金币 {stats.get('coins', 0)} · 陪伴 {self.store.data.get('days', 1)} 天"
        )
        exp_percent = min(100, int(exp / max(1, required) * 100))
        self.exp_bar.setValue(exp_percent)
        self.exp_bar.setFormat(f"升级 {exp}/{required} EXP")
        seconds, goal = self.store.companion_progress()
        percent = min(100, int(seconds / goal * 100))
        self.companion_bar.setValue(percent)
        self.companion_bar.setFormat(f"{seconds // 60}/{max(1, goal // 60)} 分钟")
        self._refresh_growth_profile()
        self._refresh_buffs()
        for task_id, button in self.task_buttons.items():
            done = bool(self.store.tasks.get(task_id))
            claimable = self.store.task_claimable(task_id)
            button.setEnabled(claimable and not done)
            button.setText("已领取" if done else ("领取奖励" if claimable else "未达成"))
            if task_id in self.task_progress_labels:
                _, _, label = self.store.task_progress(task_id)
                self.task_progress_labels[task_id].setText(f"进度：{label}")

    def _refresh_growth_profile(self):
        level = self.store.level_info()
        exp, required = self.store.level_progress()
        if level.get("next_milestone"):
            next_unlock = (
                f"Lv.{level['next_milestone']['level']} 解锁 "
                f"{level['next_milestone']['affection_ceiling']}% 好感上限。"
            )
        else:
            next_unlock = "等级称号已达到最高档。"
        affection = self.store.affection_info()
        cap = self.store.daily_affection_cap()
        gained = int(self.store.data.get("daily_counts", {}).get("affection_gain", 0))
        ceiling = max(1, int(level["affection_ceiling"]))
        affection_percent = min(100, int(affection["value"] / ceiling * 100))
        daily_percent = min(100, int(gained / max(1, cap) * 100))
        self.sidebar_affection_bar.setValue(affection_percent)
        self.sidebar_affection_bar.setFormat(f"好感上限 {affection['value']}/{ceiling}%")
        self.daily_affection_bar.setValue(daily_percent)
        self.daily_affection_bar.setFormat(f"今日好感 {gained}/{cap}")
        self.level_profile_label.setText(
            "普通触摸只提升心情；好感需要完整关怀、专注或礼物慢慢建立。"
        )
        self.next_unlock_label.setText(next_unlock)
        route_lines = []
        for milestone in LEVEL_MILESTONES:
            marker = "●" if level["level"] >= milestone["level"] else "○"
            route_lines.append(
                f"{marker} Lv.{milestone['level']} {milestone['title']} · "
                f"好感上限 {milestone['affection_ceiling']}% · 日上限 {milestone['daily_affection_cap']}"
            )
        self.growth_route_label.setText("\n".join(route_lines))
        if affection["to_next"]:
            next_text = f"距离「{affection['next_title']}」还差 {affection['to_next']} 点。"
        else:
            next_text = "好感已经达到最高阶段，继续保持陪伴即可。"
        self.affection_profile_label.setText(
            f"当前阶段：{affection['title']}（{affection['value']}%）。{next_text}\n"
            f"{affection['description']}\n今日好感：{gained}/{cap}。普通触摸不直接增加好感，需要完整关怀、专注或礼物。"
        )
        counts = self.store.data.get("daily_counts", {})
        self.daily_counts_label.setText(
            "今日互动："
            f"摸摸 {counts.get('touch', 0)} 次 / "
            f"投喂 {counts.get('feed', 0)} 次 / "
            f"散步 {counts.get('walk', 0)} 次 / "
            f"休息 {counts.get('rest', 0)} 次 / "
            f"专注 {counts.get('focus_minutes', 0)} 分钟 / "
            f"完整关怀 {counts.get('care', 0)} 次"
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
        self.play_action("touch", "温柔互动只提升心情；好感需要通过完整关怀、专注或礼物慢慢建立。")


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
#levelHeroText {
    color: #284f66;
    font-size: 27px;
    font-weight: 900;
    line-height: 1.25;
}
#growthTitle {
    color: #54c3e3;
    font-size: 15px;
    font-weight: 900;
    letter-spacing: 0px;
}
#sideLabel, #routeText {
    color: #567386;
    font-size: 13px;
    line-height: 1.35;
}
#sideSectionTitle {
    color: #ff8ebc;
    font-size: 16px;
    font-weight: 900;
}
#unlockPill {
    color: #284f66;
    background: rgba(255, 255, 255, 180);
    border: 1px solid #bde8f4;
    border-radius: 8px;
    padding: 10px;
    font-size: 13px;
    font-weight: 800;
}
#sectionTitle {
    color: #2d566d;
    font-size: 18px;
    font-weight: 900;
}
#growthSidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f5fdff, stop:0.48 #ffffff, stop:1 #f4edff);
    border: 1px solid #aee6f4;
    border-radius: 10px;
    padding: 12px;
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
#growthBar {
    min-height: 24px;
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
