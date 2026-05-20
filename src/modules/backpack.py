from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from src.pet_data import ITEM_CATALOG


TYPE_LABELS = {
    "food": "食物",
    "toy": "玩具",
    "gift": "礼物",
}


class BackpackPage(QWidget):
    def __init__(self, store, play_action):
        super().__init__()
        self.store = store
        self.play_action = play_action
        self.project_root = Path(__file__).resolve().parents[2]
        self.coin_label = None
        self.count_labels = {}
        self.selected_item_id = None
        self.showcase_image = None
        self.showcase_name = None
        self.showcase_meta = None
        self.showcase_stock = None
        self.showcase_effects = None
        self.showcase_insight = None
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

        title = QLabel("背包、商店与喂养模块")
        title.setObjectName("pageTitle")
        desc = QLabel("背包现在使用透明背景拟 3D 道具图，支持商品展台、状态洞察、智能配餐、购买和投喂联动。")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(desc)

        self.coin_label = QLabel()
        self.coin_label.setObjectName("coinText")
        layout.addWidget(self.coin_label)
        layout.addWidget(self._build_showcase())

        grid = QGridLayout()
        grid.setSpacing(12)
        for index, (item_id, item) in enumerate(ITEM_CATALOG.items()):
            grid.addWidget(self._item_card(item_id, item), index // 3, index % 3)
        layout.addLayout(grid)
        layout.addStretch()
        self._select_item(next(iter(ITEM_CATALOG)))
        scroll.setWidget(content)
        root_layout.addWidget(scroll)
        self.setStyleSheet(PAGE_STYLE)

    def _build_showcase(self):
        showcase = QFrame()
        showcase.setObjectName("showcasePanel")
        layout = QHBoxLayout(showcase)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        self.showcase_image = QLabel()
        self.showcase_image.setObjectName("showcaseImage")
        self.showcase_image.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.showcase_image, 0)

        details = QVBoxLayout()
        details.setSpacing(8)
        kicker = QLabel("ARCTIC KITCHEN LAB")
        kicker.setObjectName("showcaseKicker")
        self.showcase_name = QLabel()
        self.showcase_name.setObjectName("showcaseName")
        self.showcase_meta = QLabel()
        self.showcase_meta.setObjectName("showcaseMeta")
        self.showcase_stock = QLabel()
        self.showcase_stock.setObjectName("showcaseStock")
        self.showcase_effects = QLabel()
        self.showcase_effects.setObjectName("showcaseText")
        self.showcase_effects.setWordWrap(True)
        self.showcase_insight = QLabel()
        self.showcase_insight.setObjectName("showcaseInsight")
        self.showcase_insight.setWordWrap(True)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        recommend = QPushButton("按状态推荐")
        recommend.setCursor(Qt.PointingHandCursor)
        recommend.setObjectName("secondaryAction")
        recommend.clicked.connect(self._select_recommended_item)
        smart_serve = QPushButton("智能配餐")
        smart_serve.setCursor(Qt.PointingHandCursor)
        smart_serve.setObjectName("moduleAction")
        smart_serve.clicked.connect(self._smart_serve_recommended_item)
        use_current = QPushButton("使用当前")
        use_current.setCursor(Qt.PointingHandCursor)
        use_current.setObjectName("moduleAction")
        use_current.clicked.connect(self._use_selected_item)
        buy_current = QPushButton("购买当前")
        buy_current.setCursor(Qt.PointingHandCursor)
        buy_current.setObjectName("secondaryAction")
        buy_current.clicked.connect(self._buy_selected_item)
        action_row.addWidget(recommend)
        action_row.addWidget(smart_serve)
        action_row.addWidget(use_current)
        action_row.addWidget(buy_current)

        details.addWidget(kicker)
        details.addWidget(self.showcase_name)
        details.addWidget(self.showcase_meta)
        details.addWidget(self.showcase_stock)
        details.addWidget(self.showcase_effects)
        details.addWidget(self.showcase_insight)
        details.addLayout(action_row)
        details.addStretch()
        layout.addLayout(details, 1)
        return showcase

    def _item_card(self, item_id, item):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        image = QLabel()
        image.setObjectName("itemImage")
        image.setAlignment(Qt.AlignCenter)
        pixmap = self._item_pixmap(item, 188, 128)
        if not pixmap.isNull():
            image.setPixmap(pixmap)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        title = QLabel(item["name"])
        title.setObjectName("cardTitle")
        type_label = QLabel(TYPE_LABELS.get(item["type"], item["type"]))
        type_label.setObjectName(f"typeBadge-{item['type']}")
        count = QLabel()
        count.setObjectName("countText")
        self.count_labels[item_id] = count
        meta_row.addWidget(title, 1)
        meta_row.addWidget(type_label, 0)

        price = QLabel(f"{item['price']} 金币")
        price.setObjectName("priceText")
        desc = QLabel(item["description"])
        desc.setWordWrap(True)
        desc.setObjectName("taskItem")
        effects = QLabel(self._format_effects(item["effects"]))
        effects.setWordWrap(True)
        effects.setObjectName("taskItem")
        buff = QLabel(self._format_buff(item))
        buff.setWordWrap(True)
        buff.setObjectName("taskItem")

        use_button = QPushButton("投喂" if item["type"] == "food" else "使用")
        use_button.setCursor(Qt.PointingHandCursor)
        use_button.setObjectName("moduleAction")
        use_button.clicked.connect(lambda checked=False, key=item_id: self._use_item(key))

        buy_button = QPushButton(f"购买 {item['price']} 金币")
        buy_button.setCursor(Qt.PointingHandCursor)
        buy_button.setObjectName("secondaryAction")
        buy_button.clicked.connect(lambda checked=False, key=item_id: self._buy_item(key))

        preview_button = QPushButton("3D 展台")
        preview_button.setCursor(Qt.PointingHandCursor)
        preview_button.setObjectName("previewAction")
        preview_button.clicked.connect(lambda checked=False, key=item_id: self._select_item(key))

        layout.addWidget(image)
        layout.addLayout(meta_row)
        layout.addWidget(price)
        layout.addWidget(count)
        layout.addWidget(desc)
        layout.addWidget(effects)
        layout.addWidget(buff)
        layout.addWidget(preview_button)
        layout.addWidget(use_button)
        layout.addWidget(buy_button)
        return card

    def _item_pixmap(self, item, width, height):
        image_path = self.project_root / item.get("image", "")
        if not image_path.exists():
            return QPixmap()
        pixmap = QPixmap(str(image_path))
        return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

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

    def _format_buff(self, item):
        buff = item.get("buff")
        if not buff:
            return "增益：无"
        return "增益：" + buff.get("description", "特殊效果")

    def refresh(self):
        self.coin_label.setText(f"当前金币：{self.store.stats.get('coins', 0)}")
        for item_id, label in self.count_labels.items():
            label.setText(f"库存：{self.store.inventory.get(item_id, 0)}")
        if self.selected_item_id:
            self._sync_showcase()

    def _select_item(self, item_id):
        if item_id not in ITEM_CATALOG:
            return
        self.selected_item_id = item_id
        self._sync_showcase()

    def _sync_showcase(self):
        item = ITEM_CATALOG[self.selected_item_id]
        pixmap = self._item_pixmap(item, 292, 220)
        if not pixmap.isNull():
            self.showcase_image.setPixmap(pixmap)
        self.showcase_name.setText(item["name"])
        type_name = TYPE_LABELS.get(item["type"], item["type"])
        self.showcase_meta.setText(f"{type_name} / {item['price']} 金币 / 困难经济物资")
        self.showcase_stock.setText(f"库存 {self.store.inventory.get(self.selected_item_id, 0)} · 金币 {self.store.stats.get('coins', 0)}")
        self.showcase_effects.setText(f"{self._format_effects(item['effects'])}；{self._format_buff(item)}")
        self.showcase_insight.setText(self._item_insight(self.selected_item_id, item))

    def _item_insight(self, item_id, item):
        stats = self.store.stats
        lowest_key = min(("hunger", "mood", "energy", "affection"), key=lambda key: int(stats.get(key, 0)))
        lowest_names = {"hunger": "饱食", "mood": "心情", "energy": "体力", "affection": "好感"}
        recommended = self._recommended_item_id()
        if item_id == recommended:
            return f"推荐：当前最低状态是{lowest_names[lowest_key]}，这件物品最适合现在使用。"
        return f"状态洞察：当前最低状态是{lowest_names[lowest_key]}；可点“按状态推荐”切换到更合适的物品。"

    def _recommended_item_id(self):
        stats = self.store.stats
        lowest_key = min(("hunger", "mood", "energy", "affection"), key=lambda key: int(stats.get(key, 0)))
        if lowest_key == "hunger":
            return "fish" if self.store.stats.get("coins", 0) >= ITEM_CATALOG["fish"]["price"] else "ice"
        if lowest_key == "energy":
            return "milk"
        if lowest_key == "mood":
            return "berry_cake" if self.store.stats.get("coins", 0) >= ITEM_CATALOG["berry_cake"]["price"] else "snowball"
        return "scarf" if self.store.stats.get("coins", 0) >= ITEM_CATALOG["scarf"]["price"] else "berry_cake"

    def _select_recommended_item(self):
        self._select_item(self._recommended_item_id())

    def _smart_serve_recommended_item(self):
        item_id = self._recommended_item_id()
        self._select_item(item_id)
        if self.store.inventory.get(item_id, 0) <= 0:
            item = ITEM_CATALOG[item_id]
            if self.store.stats.get("coins", 0) < item["price"]:
                self.play_action("idle", f"金币不足，暂时无法准备{item['name']}。")
                return
            self.store.buy_item(item_id)
        self._use_item(item_id)

    def _use_selected_item(self):
        if self.selected_item_id:
            self._use_item(self.selected_item_id)

    def _buy_selected_item(self):
        if self.selected_item_id:
            self._buy_item(self.selected_item_id)

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
    color: #284f66;
    font-size: 28px;
    font-weight: 900;
}
#pageScroll {
    background: transparent;
    border: none;
}
#pageDescription, #taskItem {
    color: #5f7c8d;
    font-size: 14px;
}
#coinText {
    color: #ff8ebc;
    font-size: 22px;
    font-weight: 900;
}
#showcasePanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffffff, stop:0.48 #eaf9ff, stop:1 #fff3f8);
    border: 1px solid #b9e6f2;
    border-radius: 8px;
}
#showcaseImage {
    min-width: 320px;
    max-width: 320px;
    min-height: 236px;
    max-height: 236px;
    background: #f8fcff;
    border: 1px solid #c4e5ef;
    border-radius: 8px;
}
#showcaseKicker {
    color: #61b8d0;
    font-size: 12px;
    font-weight: 900;
}
#showcaseName {
    color: #284f66;
    font-size: 30px;
    font-weight: 900;
}
#showcaseMeta {
    color: #ff8ebc;
    font-size: 15px;
    font-weight: 800;
}
#showcaseStock, #showcaseText {
    color: #31556b;
    font-size: 14px;
}
#showcaseInsight {
    color: #5f7c8d;
    background: #ffffff;
    border: 1px solid #ffd1df;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 14px;
}
#itemImage {
    min-height: 132px;
    max-height: 132px;
    background: #f8fcff;
    border: 1px solid #c4e5ef;
    border-radius: 8px;
}
#moduleCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #edfaff);
    border: 1px solid #c4e5ef;
    border-radius: 8px;
    padding: 12px;
}
#cardTitle {
    color: #61b8d0;
    font-size: 18px;
    font-weight: 900;
}
#countText {
    color: #294f66;
    font-size: 15px;
    font-weight: 800;
}
#priceText {
    color: #ff8ebc;
    font-size: 18px;
    font-weight: 900;
}
#typeBadge-food, #typeBadge-toy, #typeBadge-gift {
    min-width: 42px;
    color: #ffffff;
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 12px;
    font-weight: 900;
}
#typeBadge-food {
    background: #85decf;
}
#typeBadge-toy {
    background: #64c9e8;
}
#typeBadge-gift {
    background: #ffadc8;
}
#moduleAction, #secondaryAction, #previewAction {
    min-height: 36px;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #64c9e8, stop:1 #ffadc8);
    border: 1px solid #ffffff;
    border-radius: 14px;
    font-weight: 900;
    text-align: center;
}
#secondaryAction {
    color: #31556b;
    background: #ffffff;
    border-color: #c7e4ef;
}
#previewAction {
    color: #ffffff;
    background: #ffd374;
    border-color: #ffffff;
}
#moduleAction:hover {
    background: #d8b45c;
}
#secondaryAction:hover {
    background: #fff4fa;
    border-color: #ffadc8;
}
#previewAction:hover {
    background: #ffadc8;
}
QLabel {
    color: #31556b;
}
"""
