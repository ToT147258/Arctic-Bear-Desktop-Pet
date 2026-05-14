import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal


ITEM_CATALOG = {
    "fish": {
        "name": "小鱼",
        "type": "food",
        "price": 28,
        "effects": {"hunger": 18, "mood": 4, "affection": 1},
        "description": "最喜欢的基础食物，恢复饱食度。",
    },
    "milk": {
        "name": "牛奶",
        "type": "food",
        "price": 24,
        "effects": {"hunger": 10, "energy": 8},
        "description": "温和恢复体力，适合睡醒后补充。",
    },
    "berry_cake": {
        "name": "蓝莓蛋糕",
        "type": "food",
        "price": 42,
        "effects": {"hunger": 12, "mood": 12, "affection": 3},
        "description": "小奖励食物，提升心情和好感。",
    },
    "snowball": {
        "name": "雪球玩具",
        "type": "toy",
        "price": 36,
        "effects": {"mood": 16, "affection": 2, "energy": -3},
        "description": "互动玩具，适合触发玩耍动作。",
    },
    "scarf": {
        "name": "围巾",
        "type": "gift",
        "price": 64,
        "effects": {"affection": 8, "mood": 4},
        "description": "一次性礼物，明显提升好感。",
    },
    "ice": {
        "name": "冰块",
        "type": "food",
        "price": 12,
        "effects": {"hunger": 4, "mood": 2},
        "description": "便宜的小零食，适合轻量投喂。",
    },
}


TASK_CATALOG = {
    "daily_login": {"title": "今日登录", "reward": 12, "exp": 8},
    "companion": {"title": "陪伴 10 分钟", "reward": 18, "exp": 12},
    "feed_once": {"title": "完成一次投喂", "reward": 16, "exp": 10},
    "touch_once": {"title": "触发一次互动", "reward": 14, "exp": 10},
    "sleep_once": {"title": "安排一次休息", "reward": 20, "exp": 12},
    "walk_once": {"title": "让桌宠走动一次", "reward": 14, "exp": 8},
}


DEFAULT_DATA = {
    "stats": {
        "hunger": 82,
        "mood": 88,
        "energy": 76,
        "affection": 64,
        "level": 1,
        "exp": 35,
        "coins": 120,
    },
    "inventory": {
        "fish": 3,
        "milk": 2,
        "berry_cake": 1,
        "snowball": 1,
        "scarf": 0,
        "ice": 5,
    },
    "tasks": {task_id: False for task_id in TASK_CATALOG},
    "settings": {
        "opacity": 1.0,
        "always_on_top": True,
    },
    "logs": [],
}


class PetDataStore(QObject):
    changed = Signal()
    log_added = Signal(str)

    def __init__(self, save_path=None):
        super().__init__()
        root = Path(__file__).resolve().parents[1]
        self.save_path = Path(save_path) if save_path else root / "data" / "save.json"
        self.data = deepcopy(DEFAULT_DATA)
        self.load()
        if not self.data["tasks"].get("daily_login"):
            self.complete_task("daily_login", silent=True)
            self.add_log("系统", "欢迎回来，今日登录任务已完成。")

    @property
    def stats(self):
        return self.data["stats"]

    @property
    def inventory(self):
        return self.data["inventory"]

    @property
    def tasks(self):
        return self.data["tasks"]

    @property
    def settings(self):
        return self.data["settings"]

    @property
    def logs(self):
        return self.data["logs"]

    def load(self):
        if not self.save_path.exists():
            self._normalize()
            return
        try:
            loaded = json.loads(self.save_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, TypeError):
            loaded = {}
        self.data = self._merged(DEFAULT_DATA, loaded)
        self._normalize()

    def save(self):
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.save_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _merged(self, base, override):
        result = deepcopy(base)
        if not isinstance(override, dict):
            return result
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self._merged(result[key], value)
            else:
                result[key] = value
        return result

    def _normalize(self):
        for key, value in DEFAULT_DATA["stats"].items():
            self.data["stats"].setdefault(key, value)
        for key, value in DEFAULT_DATA["inventory"].items():
            self.data["inventory"].setdefault(key, value)
        for key in TASK_CATALOG:
            self.data["tasks"].setdefault(key, False)
        for key, value in DEFAULT_DATA["settings"].items():
            self.data["settings"].setdefault(key, value)
        self.data.setdefault("logs", [])

    def _commit(self):
        self.save()
        self.changed.emit()

    def _clamp_percent(self, value):
        return max(0, min(100, int(round(value))))

    def add_log(self, category, message):
        now = datetime.now().strftime("%H:%M:%S")
        entry = f"[{now}] {category}：{message}"
        self.data["logs"].insert(0, entry)
        self.data["logs"] = self.data["logs"][:80]
        self.save()
        self.log_added.emit(entry)
        self.changed.emit()

    def clear_logs(self):
        self.data["logs"] = []
        self._commit()

    def adjust_stats(self, effects):
        for key, delta in effects.items():
            if key in {"hunger", "mood", "energy", "affection"}:
                self.stats[key] = self._clamp_percent(self.stats.get(key, 0) + delta)

    def gain_exp(self, amount):
        self.stats["exp"] = int(self.stats.get("exp", 0)) + int(amount)
        while self.stats["exp"] >= 100:
            self.stats["exp"] -= 100
            self.stats["level"] = int(self.stats.get("level", 1)) + 1
            self.stats["coins"] = int(self.stats.get("coins", 0)) + 30
            self.add_log("成长", f"等级提升到 Lv.{self.stats['level']}，获得 30 金币。")

    def feed(self, item_id):
        item = ITEM_CATALOG.get(item_id)
        if not item or item["type"] != "food":
            return False, "这个物品不能投喂。"
        if self.inventory.get(item_id, 0) <= 0:
            return False, f"{item['name']}数量不足。"
        self.inventory[item_id] -= 1
        self.adjust_stats(item["effects"])
        self.gain_exp(4)
        self.complete_task("feed_once", silent=True)
        self.add_log("投喂", f"投喂了{item['name']}，状态已更新。")
        return True, f"投喂了{item['name']}。"

    def use_item(self, item_id):
        item = ITEM_CATALOG.get(item_id)
        if not item:
            return False, "物品不存在。"
        if item["type"] == "food":
            return self.feed(item_id)
        if self.inventory.get(item_id, 0) <= 0:
            return False, f"{item['name']}数量不足。"
        self.inventory[item_id] -= 1
        self.adjust_stats(item["effects"])
        self.gain_exp(5)
        self.add_log("背包", f"使用了{item['name']}。")
        return True, f"使用了{item['name']}。"

    def buy_item(self, item_id):
        item = ITEM_CATALOG.get(item_id)
        if not item:
            return False, "商品不存在。"
        price = int(item["price"])
        if self.stats.get("coins", 0) < price:
            return False, "金币不足。"
        self.stats["coins"] -= price
        self.inventory[item_id] = self.inventory.get(item_id, 0) + 1
        self.add_log("商店", f"购买了{item['name']}，花费 {price} 金币。")
        return True, f"购买了{item['name']}。"

    def complete_task(self, task_id, silent=False):
        task = TASK_CATALOG.get(task_id)
        if not task or self.tasks.get(task_id):
            return False
        self.tasks[task_id] = True
        self.stats["coins"] = int(self.stats.get("coins", 0)) + int(task["reward"])
        self.gain_exp(task["exp"])
        if not silent:
            self.add_log("任务", f"完成「{task['title']}」，获得 {task['reward']} 金币。")
        else:
            self._commit()
        return True

    def rest(self):
        self.adjust_stats({"energy": 20, "mood": 4, "hunger": -5})
        self.complete_task("sleep_once", silent=True)
        self.add_log("休息", "安排了一次休息，体力恢复。")

    def walk(self):
        self.adjust_stats({"energy": -3, "mood": 3})
        self.complete_task("walk_once", silent=True)
        self.add_log("互动", "让桌宠走动了一小段。")

    def touch(self):
        self.adjust_stats({"mood": 8, "affection": 3})
        self.complete_task("touch_once", silent=True)
        self.add_log("互动", "触发了一次亲近互动。")

    def reset_daily_tasks(self):
        for key in TASK_CATALOG:
            self.tasks[key] = False
        self.add_log("任务", "每日任务已重置。")

    def set_setting(self, key, value):
        self.settings[key] = value
        self.add_log("设置", f"{key} 已更新。")

    def reset_all(self):
        self.data = deepcopy(DEFAULT_DATA)
        self.add_log("系统", "已恢复默认存档。")

    def export_to(self, path):
        export_path = Path(path)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.add_log("系统", f"存档已导出到 {export_path.name}。")

    def import_from(self, path):
        import_path = Path(path)
        if not import_path.exists():
            self.add_log("系统", f"没有找到 {import_path.name}。")
            return False
        try:
            loaded = json.loads(import_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, TypeError):
            self.add_log("系统", "导入失败，存档文件无法读取。")
            return False
        self.data = self._merged(DEFAULT_DATA, loaded)
        self._normalize()
        self.add_log("系统", f"已导入 {import_path.name}。")
        return True
