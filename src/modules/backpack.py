from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.pet_data import ITEM_CATALOG


class BackpackPage(QWidget):
    def __init__(self, store, play_action):
        super().__init__()
        self.store = store
        self.play_action = play_action
        self.coin_label = None
        self.count_labels = {}
        self._build_ui()
        self.store.changed.connect(self.refresh)
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(16)

        title = QLabel("背包、商店与喂养模块")
        title.setObjectName("pageTitle")
        desc = QLabel("背包现在可以真实扣减数量、购买商品、投喂食物，并联动饱食度、心情、体力、好感和任务奖励。")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(desc)

        self.coin_label = QLabel()
        self.coin_label.setObjectName("coinText")
        layout.addWidget(self.coin_label)

        grid = QGridLayout()
        grid.setSpacing(12)
        for index, (item_id, item) in enumerate(ITEM_CATALOG.items()):
            grid.addWidget(self._item_card(item_id, item), index // 3, index % 3)
        layout.addLayout(grid)
        layout.addStretch()
        self.setStyleSheet(PAGE_STYLE)

    def _item_card(self, item_id, item):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        title = QLabel(item["name"])
        title.setObjectName("cardTitle")
        count = QLabel()
        count.setObjectName("countText")
        self.count_labels[item_id] = count
        desc = QLabel(item["description"])
        desc.setWordWrap(True)
        desc.setObjectName("taskItem")
        effects = QLabel(self._format_effects(item["effects"]))
        effects.setWordWrap(True)
        effects.setObjectName("taskItem")

        use_button = QPushButton("投喂" if item["type"] == "food" else "使用")
        use_button.setCursor(Qt.PointingHandCursor)
        use_button.setObjectName("moduleAction")
        use_button.clicked.connect(lambda checked=False, key=item_id: self._use_item(key))

        buy_button = QPushButton(f"购买 {item['price']} 金币")
        buy_button.setCursor(Qt.PointingHandCursor)
        buy_button.setObjectName("secondaryAction")
        buy_button.clicked.connect(lambda checked=False, key=item_id: self._buy_item(key))

        layout.addWidget(title)
        layout.addWidget(count)
        layout.addWidget(desc)
        layout.addWidget(effects)
        layout.addWidget(use_button)
        layout.addWidget(buy_button)
        return card

    def _format_effects(self, effects):
        names = {
            "hunger": "饱食",
            "mood": "心情",
            "energy": "体力",
            "affection": "好感",
        }
        parts = []
        for key, value in effects.items():
            sign = "+" if value >= 0 else ""
            parts.append(f"{names.get(key, key)} {sign}{value}")
        return "效果：" + " / ".join(parts)

    def refresh(self):
        self.coin_label.setText(f"当前金币：{self.store.stats.get('coins', 0)}")
        for item_id, label in self.count_labels.items():
            label.setText(f"库存：{self.store.inventory.get(item_id, 0)}")

    def _use_item(self, item_id):
        ok, message = self.store.use_item(item_id)
        if ok:
            action = "touch" if ITEM_CATALOG[item_id]["type"] == "food" else "wave"
            self.play_action(action, message)
        else:
            self.play_action("idle", message)

    def _buy_item(self, item_id):
        ok, message = self.store.buy_item(item_id)
        self.play_action("idle", message)


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
#coinText {
    color: #ffffff;
    font-size: 22px;
    font-weight: 900;
}
#moduleCard {
    background: #122237;
    border: 1px solid #2a4c68;
    border-radius: 10px;
    padding: 12px;
}
#cardTitle {
    color: #7ee8ff;
    font-size: 18px;
    font-weight: 800;
}
#countText {
    color: #ffffff;
    font-size: 15px;
    font-weight: 800;
}
#moduleAction, #secondaryAction {
    min-height: 36px;
    color: #06111f;
    background: #8df3c8;
    border: 1px solid #8df3c8;
    border-radius: 8px;
    font-weight: 800;
    text-align: center;
}
#secondaryAction {
    color: #dcefff;
    background: #17283c;
    border-color: #2c4c68;
}
#moduleAction:hover {
    background: #a9ffe0;
}
#secondaryAction:hover {
    background: #1d3853;
    border-color: #62dff5;
}
QLabel {
    color: #d7e7f3;
}
"""
