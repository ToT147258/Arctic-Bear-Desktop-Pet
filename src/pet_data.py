import json
from copy import deepcopy
from datetime import datetime
from datetime import time as datetime_time
from datetime import timedelta
from pathlib import Path

from PySide6.QtCore import QObject, Signal


WEEKDAY_ORDER = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEKDAY_INDEX = {name: index for index, name in enumerate(WEEKDAY_ORDER)}


ITEM_CATALOG = {
    "fish": {
        "name": "极地鱼干",
        "type": "food",
        "price": 48,
        "effects": {"hunger": 16, "mood": 2},
        "image": "assets/shop/items/fish.png",
        "description": "低温风干的基础补给，口感清爽，主要恢复饱食度。",
    },
    "milk": {
        "name": "暖绒热牛奶",
        "type": "food",
        "price": 52,
        "effects": {"hunger": 8, "energy": 7},
        "image": "assets/shop/items/milk.png",
        "buff": {
            "effect": "hunger_stop",
            "expiration": 300,
            "description": "5 分钟内饱食度不会自然下降。",
        },
        "description": "带一点奶香的热饮，温和恢复体力，适合睡醒后补充。",
    },
    "berry_cake": {
        "name": "蓝莓冰雪蛋糕",
        "type": "food",
        "price": 88,
        "effects": {"hunger": 10, "mood": 10, "affection": 1},
        "image": "assets/shop/items/berry_cake.png",
        "buff": {
            "effect": "mood_guard",
            "expiration": 240,
            "description": "4 分钟内心情不会自然下降。",
        },
        "description": "柔软的甜点奖励，提升心情和好感。",
    },
    "snowball": {
        "name": "绒绒雪球",
        "type": "toy",
        "price": 120,
        "effects": {"mood": 12, "affection": 1, "energy": -4},
        "image": "assets/shop/items/snowball.png",
        "buff": {
            "effect": "coin",
            "interval": 70,
            "value": 1,
            "expiration": 210,
            "description": "3 分半内每 70 秒获得 1 金币。",
        },
        "description": "轻软的互动玩具，适合触发玩耍动作。",
    },
    "scarf": {
        "name": "雪花围巾",
        "type": "gift",
        "price": 180,
        "effects": {"affection": 4, "mood": 3},
        "image": "assets/shop/items/scarf.png",
        "description": "柔软的珍贵礼物，适合用在好感阶段推进时。",
    },
    "ice": {
        "name": "晶透冰块",
        "type": "food",
        "price": 26,
        "effects": {"hunger": 3, "mood": 1},
        "image": "assets/shop/items/ice.png",
        "description": "清爽的小零食，适合轻量投喂和低成本补给。",
    },
}


TASK_CATALOG = {
    "daily_login": {"title": "今日签到", "reward": 0, "exp": 1, "requirement": {"type": "login", "target": 1}},
    "companion": {"title": "陪伴 45 分钟", "reward": 2, "exp": 8, "requirement": {"type": "companion_minutes", "target": 45}},
    "feed_once": {"title": "合理投喂 2 次", "reward": 1, "exp": 3, "requirement": {"type": "count", "key": "feed", "target": 2}},
    "touch_once": {"title": "温柔互动 5 次", "reward": 0, "exp": 1, "requirement": {"type": "count", "key": "touch", "target": 5}},
    "sleep_once": {"title": "安排 1 次休息", "reward": 1, "exp": 3, "requirement": {"type": "count", "key": "rest", "target": 1}},
    "walk_once": {"title": "散步 3 次", "reward": 1, "exp": 3, "requirement": {"type": "count", "key": "walk", "target": 3}},
    "focus_once": {"title": "专注累计 25 分钟", "reward": 3, "exp": 8, "requirement": {"type": "count", "key": "focus_minutes", "target": 25}},
    "care_plan": {"title": "完成完整关怀", "reward": 2, "exp": 5, "requirement": {"type": "count", "key": "care", "target": 1}},
    "wellness": {"title": "四项状态 90+", "reward": 5, "exp": 12, "requirement": {"type": "wellness", "target": 90}},
    "bond_breakthrough": {"title": "好感阶段突破", "reward": 2, "exp": 5, "requirement": {"type": "count", "key": "bond_breakthrough", "target": 1}},
}


LEVEL_MILESTONES = [
    {"level": 1, "title": "新手饲养员", "affection_ceiling": 24, "daily_affection_cap": 1},
    {"level": 4, "title": "稳定陪伴", "affection_ceiling": 38, "daily_affection_cap": 1},
    {"level": 8, "title": "默契伙伴", "affection_ceiling": 55, "daily_affection_cap": 2},
    {"level": 14, "title": "极地守护者", "affection_ceiling": 75, "daily_affection_cap": 2},
    {"level": 22, "title": "冰原传说", "affection_ceiling": 100, "daily_affection_cap": 3},
]


AFFECTION_TIERS = [
    {"min": 0, "title": "初见", "description": "还在观察你，普通触摸只会提升心情，不能直接刷好感。"},
    {"min": 30, "title": "熟悉", "description": "开始记住你的陪伴，好感主要来自完整关怀和稳定专注。"},
    {"min": 60, "title": "亲近", "description": "愿意主动回应，礼物依然有效，但会受到等级和每日上限限制。"},
    {"min": 85, "title": "信赖", "description": "已经很安心，阶段突破奖励很少，重点变成长期陪伴。"},
    {"min": 100, "title": "挚友", "description": "好感已满，后续重点转为保持状态和连续陪伴。"},
]


DEFAULT_DAILY_COUNTS = {
    "touch": 0,
    "feed": 0,
    "walk": 0,
    "rest": 0,
    "focus": 0,
    "focus_minutes": 0,
    "care": 0,
    "affection_gain": 0,
    "bond_breakthrough": 0,
}


DEFAULT_DATA = {
    "stats": {
        "hunger": 72,
        "mood": 78,
        "energy": 68,
        "affection": 18,
        "level": 1,
        "exp": 0,
        "coins": 32,
    },
    "inventory": {
        "fish": 1,
        "milk": 0,
        "berry_cake": 0,
        "snowball": 0,
        "scarf": 0,
        "ice": 2,
    },
    "tasks": {task_id: False for task_id in TASK_CATALOG},
    "settings": {
        "opacity": 1.0,
        "always_on_top": True,
        "auto_feed": False,
        "bubble_on": True,
        "status_decay": True,
        "edge_snap_enabled": True,
        "edge_snap_threshold": 48,
        "pet_toggle_hotkey": "Ctrl+Alt+B",
        "companion_goal_minutes": 45,
        "pat_multi_click_talk_threshold": 6,
    },
    "active_buffs": {},
    "save_version": 3,
    "created_at": "",
    "updated_at": "",
    "today": "",
    "days": 0,
    "streak": 0,
    "daily_counts": deepcopy(DEFAULT_DAILY_COUNTS),
    "growth": {
        "affection_rewards": [],
    },
    "companion_seconds": 0,
    "last_tick": 0,
    "focus_session": {
        "active": False,
        "paused": False,
        "mode": "focus",
        "title": "",
        "total_seconds": 0,
        "remaining_seconds": 0,
        "ends_at": 0,
    },
    "course_reminders": [
        {
            "title": "项目完善 / 自习",
            "time": "19:30",
            "location": "桌面工作区",
            "note": "整理北极熊桌宠功能与素材",
            "day": "每天",
            "source": "default",
        },
        {
            "title": "课程提醒示例",
            "time": "08:30",
            "location": "教学楼",
            "note": "可在课程提醒页修改或删除",
            "day": "周一",
            "source": "default",
        },
    ],
    "chat_history": [],
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
        self._rollover_today()
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

    @property
    def course_reminders(self):
        return self.data["course_reminders"]

    @property
    def chat_history(self):
        return self.data["chat_history"]

    @property
    def active_buffs(self):
        return self.data["active_buffs"]

    @property
    def focus_session(self):
        return self.data["focus_session"]

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
        self.data["save_version"] = 3
        self.data.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
        self.data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        temp_path = self.save_path.with_name(f"{self.save_path.name}.tmp")
        temp_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            temp_path.replace(self.save_path)
        except PermissionError:
            self.save_path.write_text(temp_path.read_text(encoding="utf-8"), encoding="utf-8")
            try:
                temp_path.unlink()
            except OSError:
                pass

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
        for key in ("hunger", "mood", "energy", "affection"):
            self.data["stats"][key] = self._clamp_percent(self.data["stats"].get(key, DEFAULT_DATA["stats"][key]))
        self.data["stats"]["level"] = max(1, self._safe_int(self.data["stats"].get("level", 1), 1))
        self.data["stats"]["exp"] = max(0, self._safe_int(self.data["stats"].get("exp", 0), 0))
        self.data["stats"]["coins"] = max(0, self._safe_int(self.data["stats"].get("coins", 0), 0))
        for key, value in DEFAULT_DATA["inventory"].items():
            self.data["inventory"].setdefault(key, value)
        for key, value in list(self.data["inventory"].items()):
            self.data["inventory"][key] = max(0, self._safe_int(value, 0))
        for key in TASK_CATALOG:
            self.data["tasks"].setdefault(key, False)
        for key, value in DEFAULT_DATA["settings"].items():
            self.data["settings"].setdefault(key, value)
        self.data["settings"]["companion_goal_minutes"] = max(
            45, self._safe_int(self.data["settings"].get("companion_goal_minutes", 45), 45)
        )
        if "auto_feed" not in self.data["settings"]:
            self.data["settings"]["auto_feed"] = False
        self.data.setdefault("active_buffs", {})
        self.data.setdefault("save_version", 3)
        now_text = datetime.now().isoformat(timespec="seconds")
        self.data.setdefault("created_at", now_text)
        self.data.setdefault("updated_at", now_text)
        self.data.setdefault("today", "")
        self.data.setdefault("days", 0)
        self.data.setdefault("streak", 0)
        if not isinstance(self.data.get("daily_counts"), dict):
            self.data["daily_counts"] = deepcopy(DEFAULT_DAILY_COUNTS)
        self.data.setdefault("daily_counts", deepcopy(DEFAULT_DAILY_COUNTS))
        for key, value in DEFAULT_DAILY_COUNTS.items():
            self.data["daily_counts"].setdefault(key, value)
        for key, value in list(self.data["daily_counts"].items()):
            self.data["daily_counts"][key] = max(0, self._safe_int(value, 0))
        if not isinstance(self.data.get("growth"), dict):
            self.data["growth"] = deepcopy(DEFAULT_DATA["growth"])
        self.data.setdefault("growth", deepcopy(DEFAULT_DATA["growth"]))
        self.data["growth"].setdefault("affection_rewards", [])
        self.data.setdefault("companion_seconds", 0)
        self.data.setdefault("last_tick", 0)
        now_ts = int(datetime.now().timestamp())
        self.data["companion_seconds"] = max(0, self._safe_int(self.data.get("companion_seconds", 0), 0))
        self.data["last_tick"] = max(0, self._safe_int(self.data.get("last_tick", 0), 0))
        if self.data["last_tick"] > now_ts + 300:
            self.data["last_tick"] = now_ts
        if not isinstance(self.data.get("focus_session"), dict):
            self.data["focus_session"] = deepcopy(DEFAULT_DATA["focus_session"])
        self.data.setdefault("focus_session", deepcopy(DEFAULT_DATA["focus_session"]))
        for key, value in DEFAULT_DATA["focus_session"].items():
            self.data["focus_session"].setdefault(key, value)
        if not isinstance(self.data.get("course_reminders"), list):
            self.data["course_reminders"] = deepcopy(DEFAULT_DATA["course_reminders"])
        cleaned_courses = []
        for course in self.data.get("course_reminders", []):
            if not isinstance(course, dict):
                continue
            cleaned_courses.append(
                {
                    "title": str(course.get("title") or "未命名课程")[:40],
                    "time": str(course.get("time") or "00:00")[:8],
                    "location": str(course.get("location") or "未设置地点")[:40],
                    "note": str(course.get("note") or "提前准备一下")[:80],
                    "day": self._normalize_course_day(course.get("day", "每天")),
                    "source": str(course.get("source") or "manual")[:20],
                }
            )
        self.data["course_reminders"] = cleaned_courses[:40]
        if not isinstance(self.data.get("chat_history"), list):
            self.data["chat_history"] = []
        self.data["chat_history"] = [
            item
            for item in self.data.get("chat_history", [])
            if isinstance(item, dict) and item.get("role") and item.get("text")
        ][:60]
        self.data.setdefault("logs", [])

    def _today(self):
        return datetime.now().strftime("%Y-%m-%d")

    def _rollover_today(self):
        today = self._today()
        if self.data.get("today") == today:
            return
        old_today = self.data.get("today")
        self.data["today"] = today
        self.data["companion_seconds"] = 0
        self.data["daily_counts"] = deepcopy(DEFAULT_DAILY_COUNTS)
        for key in TASK_CATALOG:
            self.data["tasks"][key] = False
        if old_today:
            self.data["days"] = self._safe_int(self.data.get("days", 0), 0) + 1
            self.data["streak"] = self._safe_int(self.data.get("streak", 0), 0) + 1
        else:
            self.data["days"] = max(1, self._safe_int(self.data.get("days", 0) or 1, 1))
            self.data["streak"] = max(1, self._safe_int(self.data.get("streak", 0) or 1, 1))
        self.data["last_tick"] = int(datetime.now().timestamp())
        self.save()

    def _commit(self):
        self.save()
        self.changed.emit()

    def _clamp_percent(self, value):
        return max(0, min(100, self._safe_int(value, 0)))

    def _safe_int(self, value, default=0):
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return default

    def level_exp_required(self, level=None):
        level = max(1, self._safe_int(level or self.stats.get("level", 1), 1))
        return 260 + (level - 1) * 140 + max(0, level - 8) * 80 + max(0, level - 18) * 120

    def level_progress(self):
        required = self.level_exp_required()
        exp = max(0, self._safe_int(self.stats.get("exp", 0), 0))
        return min(exp, required), required

    def level_info(self):
        level = max(1, self._safe_int(self.stats.get("level", 1), 1))
        milestone = self._level_milestone(level)
        next_milestone = next((item for item in LEVEL_MILESTONES if item["level"] > level), None)
        return {
            "level": level,
            "title": milestone["title"],
            "affection_cap": milestone["daily_affection_cap"],
            "affection_ceiling": milestone["affection_ceiling"],
            "next_milestone": next_milestone,
            "next_exp": self.level_exp_required(level),
        }

    def _level_milestone(self, level=None):
        level = max(1, self._safe_int(level or self.stats.get("level", 1), 1))
        current = LEVEL_MILESTONES[0]
        for milestone in LEVEL_MILESTONES:
            if level >= milestone["level"]:
                current = milestone
        return current

    def affection_level_ceiling(self, level=None):
        return self._level_milestone(level)["affection_ceiling"]

    def daily_affection_cap(self, level=None):
        return self._level_milestone(level)["daily_affection_cap"]

    def affection_tier(self, value=None):
        value = self._clamp_percent(self.stats.get("affection", 0) if value is None else value)
        tier = AFFECTION_TIERS[0]
        for candidate in AFFECTION_TIERS:
            if value >= candidate["min"]:
                tier = candidate
        return tier

    def affection_info(self):
        value = self._clamp_percent(self.stats.get("affection", 0))
        tier = self.affection_tier(value)
        next_tier = None
        for candidate in AFFECTION_TIERS:
            if candidate["min"] > value:
                next_tier = candidate
                break
        return {
            "value": value,
            "title": tier["title"],
            "description": tier["description"],
            "next_title": next_tier["title"] if next_tier else "已满级",
            "next_at": next_tier["min"] if next_tier else 100,
            "to_next": max(0, (next_tier["min"] - value) if next_tier else 0),
        }

    def growth_summary(self):
        exp, required = self.level_progress()
        affection = self.affection_info()
        level = self.level_info()
        return (
            f"Lv.{level['level']}「{level['title']}」经验 {exp}/{required}，"
            f"好感「{affection['title']}」{affection['value']}%，"
            f"等级好感上限 {level['affection_ceiling']}%，今日可提升 {level['affection_cap']}。"
        )

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

    def _normalize_course_day(self, day):
        text = str(day or "每天").strip()
        aliases = {
            "星期一": "周一",
            "礼拜一": "周一",
            "一": "周一",
            "1": "周一",
            "星期二": "周二",
            "礼拜二": "周二",
            "二": "周二",
            "2": "周二",
            "星期三": "周三",
            "礼拜三": "周三",
            "三": "周三",
            "3": "周三",
            "星期四": "周四",
            "礼拜四": "周四",
            "四": "周四",
            "4": "周四",
            "星期五": "周五",
            "礼拜五": "周五",
            "五": "周五",
            "5": "周五",
            "星期六": "周六",
            "礼拜六": "周六",
            "六": "周六",
            "6": "周六",
            "星期日": "周日",
            "星期天": "周日",
            "礼拜日": "周日",
            "礼拜天": "周日",
            "日": "周日",
            "天": "周日",
            "7": "周日",
        }
        if text in WEEKDAY_INDEX or text == "每天":
            return text
        return aliases.get(text, "每天")

    def add_course_reminder(self, title, time_text, location, note, day="每天", source="manual"):
        title = (title or "").strip()[:40] or "未命名课程"
        time_text = (time_text or "00:00").strip()[:8]
        location = (location or "").strip()[:40] or "未设置地点"
        note = (note or "").strip()[:80] or "提前准备一下"
        day = self._normalize_course_day(day)
        self.data.setdefault("course_reminders", [])
        self.data["course_reminders"].append(
            {
                "title": title,
                "time": time_text,
                "location": location,
                "note": note,
                "day": day,
                "source": str(source or "manual")[:20],
            }
        )
        self.data["course_reminders"] = sorted(
            self.data["course_reminders"],
            key=lambda item: (self._course_day_sort(item.get("day")), str(item.get("time", "99:99"))),
        )[:40]
        self.add_log("课程", f"已添加《{title}》提醒，{day} {time_text}。")

    def import_course_reminders(self, courses, replace=False):
        incoming = courses or []
        if replace:
            self.data["course_reminders"] = []
        existing = {
            (
                self._normalize_course_day(course.get("day", "每天")),
                str(course.get("time", "00:00")),
                str(course.get("title", "")),
                str(course.get("location", "")),
            )
            for course in self.data.get("course_reminders", [])
        }
        added = 0
        for course in incoming:
            title = str(course.get("title") or "").strip()[:40]
            if not title:
                continue
            day = self._normalize_course_day(course.get("day", "每天"))
            time_text = str(course.get("time") or "00:00")[:8]
            location = str(course.get("location") or "待确认地点")[:40]
            key = (day, time_text, title, location)
            if key in existing:
                continue
            self.data.setdefault("course_reminders", []).append(
                {
                    "title": title,
                    "time": time_text,
                    "location": location,
                    "note": str(course.get("note") or "课表识别导入")[:80],
                    "day": day,
                    "source": str(course.get("source") or "ocr")[:20],
                }
            )
            existing.add(key)
            added += 1
        self.data["course_reminders"] = sorted(
            self.data.get("course_reminders", []),
            key=lambda item: (self._course_day_sort(item.get("day")), str(item.get("time", "99:99"))),
        )[:40]
        if added:
            self.add_log("课程", f"从课表识别导入 {added} 条课程提醒。")
        else:
            self.add_log("课程", "没有导入新的课程，可能是没有识别到有效课程或内容已存在。")
        return added

    def clear_course_reminders(self):
        self.data["course_reminders"] = []
        self.add_log("课程", "已清空课程提醒。")

    def remove_course_reminder(self, index):
        courses = self.data.setdefault("course_reminders", [])
        if index < 0 or index >= len(courses):
            return False
        course = courses.pop(index)
        self.add_log("课程", f"已删除《{course.get('title', '课程')}》提醒。")
        return True

    def _course_day_sort(self, day):
        normalized = self._normalize_course_day(day)
        return -1 if normalized == "每天" else WEEKDAY_INDEX.get(normalized, 8)

    def _parse_course_time(self, time_text):
        try:
            hour, minute = str(time_text or "00:00")[:5].split(":")
            return datetime_time(max(0, min(23, int(hour))), max(0, min(59, int(minute))))
        except (TypeError, ValueError):
            return datetime_time(0, 0)

    def _next_course_datetime(self, course, now=None):
        now = now or datetime.now()
        course_time = self._parse_course_time(course.get("time", "00:00"))
        day = self._normalize_course_day(course.get("day", "每天"))
        if day == "每天":
            target_date = now.date()
            candidate = datetime.combine(target_date, course_time)
            if candidate < now:
                candidate += timedelta(days=1)
            return candidate
        target_index = WEEKDAY_INDEX.get(day, now.weekday())
        days_delta = (target_index - now.weekday()) % 7
        candidate = datetime.combine(now.date() + timedelta(days=days_delta), course_time)
        if candidate < now:
            candidate += timedelta(days=7)
        return candidate

    def next_course_reminder(self, now=None):
        courses = list(self.data.get("course_reminders", []))
        if not courses:
            return None
        now = now or datetime.now()
        ordered = sorted(courses, key=lambda course: self._next_course_datetime(course, now))
        if not ordered:
            return None
        course = dict(ordered[0])
        next_at = self._next_course_datetime(course, now)
        course["next_at_text"] = self._format_course_next_at(next_at, now)
        course["minutes_left"] = max(0, int((next_at - now).total_seconds() // 60))
        course["day"] = self._normalize_course_day(course.get("day", "每天"))
        return course

    def _format_course_next_at(self, next_at, now=None):
        now = now or datetime.now()
        if next_at.date() == now.date():
            return f"今天 {next_at.strftime('%H:%M')}"
        if next_at.date() == (now + timedelta(days=1)).date():
            return f"明天 {next_at.strftime('%H:%M')}"
        return f"{WEEKDAY_ORDER[next_at.weekday()]} {next_at.strftime('%H:%M')}"

    def course_summary(self):
        course = self.next_course_reminder()
        if not course:
            return "暂无课程提醒", "时间待同步", "地点未设置"
        title = course.get("title", "未命名课程")
        time_text = course.get("next_at_text") or f"{course.get('day', '每天')} {course.get('time', '00:00')}"
        location = course.get("location", "未设置地点")
        return title, time_text, location

    def trigger_course_bubble(self):
        course = self.next_course_reminder()
        if not course:
            self.add_log("课程", "暂无可提醒课程。")
            return "暂无课程提醒。"
        minutes_left = int(course.get("minutes_left", 0))
        countdown = f"{minutes_left} 分钟后" if minutes_left < 180 else course.get("next_at_text", course.get("time", "00:00"))
        message = f"{countdown}《{course.get('title', '课程')}》@ {course.get('location', '未设置地点')}"
        self.add_log("课程", f"触发课程提醒：{message}")
        return message

    def add_chat_message(self, role, text):
        role = "bear" if role == "bear" else "user"
        text = str(text or "").strip()
        if not text:
            return
        self.data.setdefault("chat_history", [])
        self.data["chat_history"].insert(
            0,
            {
                "role": role,
                "text": text[:160],
                "time": datetime.now().strftime("%H:%M"),
            },
        )
        self.data["chat_history"] = self.data["chat_history"][:60]
        self._commit()

    def task_progress(self, task_id):
        task = TASK_CATALOG.get(task_id, {})
        requirement = task.get("requirement", {})
        target = max(1, self._safe_int(requirement.get("target", 1), 1))
        kind = requirement.get("type", "login")
        if kind == "login":
            current = 1
            label = "今日已登录"
        elif kind == "count":
            key = requirement.get("key", "")
            current = self._safe_int(self.data.get("daily_counts", {}).get(key, 0), 0)
            label = f"{current}/{target} 分钟" if key == "focus_minutes" else f"{current}/{target}"
        elif kind == "companion_minutes":
            current = self._safe_int(self.data.get("companion_seconds", 0), 0) // 60
            label = f"{current}/{target} 分钟"
        elif kind == "wellness":
            current = min(self._safe_int(self.stats.get(key, 0), 0) for key in ("hunger", "mood", "energy", "affection"))
            label = f"最低状态 {current}/{target}"
        else:
            current = 0
            label = "等待完成"
        return min(current, target), target, label

    def task_claimable(self, task_id):
        if self.tasks.get(task_id):
            return False
        current, target, _ = self.task_progress(task_id)
        return current >= target

    def _apply_affection_gain(self, amount):
        amount = max(0, self._safe_int(amount, 0))
        if amount <= 0:
            return 0
        current_value = self._safe_int(self.stats.get("affection", 0), 0)
        if current_value >= 85:
            amount = min(amount, 1)
        elif current_value >= 60:
            amount = min(amount, 2)
        cap = self.daily_affection_cap()
        level_ceiling = self.affection_level_ceiling()
        gained_today = self._safe_int(self.data.setdefault("daily_counts", {}).get("affection_gain", 0), 0)
        allowed = max(0, cap - gained_today)
        allowed_by_level = max(0, level_ceiling - current_value)
        gained = min(amount, allowed, allowed_by_level, 100 - current_value)
        if gained <= 0:
            return 0
        before = current_value
        self.stats["affection"] = self._clamp_percent(current_value + gained)
        self.data["daily_counts"]["affection_gain"] = gained_today + gained
        self._check_affection_breakthrough(before, self._safe_int(self.stats.get("affection", 0), 0))
        return gained

    def adjust_stats(self, effects):
        old_affection = self._safe_int(self.stats.get("affection", 0), 0)
        for key, delta in effects.items():
            if key in {"hunger", "mood", "energy"}:
                self.stats[key] = self._clamp_percent(self.stats.get(key, 0) + delta)
            elif key == "affection":
                if delta >= 0:
                    self._apply_affection_gain(delta)
                else:
                    self.stats["affection"] = self._clamp_percent(self.stats.get("affection", 0) + delta)
        if self.stats.get("affection", 0) > old_affection:
            self._check_affection_breakthrough(old_affection, self._safe_int(self.stats.get("affection", 0), 0))
        self._check_wellness_task()

    def _check_wellness_task(self):
        if all(self._safe_int(self.stats.get(key, 0), 0) >= 90 for key in ("hunger", "mood", "energy", "affection")):
            self.complete_task("wellness", silent=True)

    def _check_affection_breakthrough(self, before, after):
        old_tier = self.affection_tier(before)
        new_tier = self.affection_tier(after)
        if new_tier["min"] <= old_tier["min"]:
            return
        claimed = self.data["growth"].setdefault("affection_rewards", [])
        tier_key = str(new_tier["min"])
        if tier_key in claimed:
            return
        claimed.append(tier_key)
        self.data["daily_counts"]["bond_breakthrough"] = self._safe_int(
            self.data["daily_counts"].get("bond_breakthrough", 0), 0
        ) + 1
        bonus = 1 + AFFECTION_TIERS.index(new_tier)
        self.stats["coins"] = self._safe_int(self.stats.get("coins", 0), 0) + bonus
        self.complete_task("bond_breakthrough", silent=True)
        self.add_log("好感", f"好感进入「{new_tier['title']}」，额外获得 {bonus} 金币。")

    def _has_buff(self, effect_name):
        now_ts = int(datetime.now().timestamp())
        for buff in self.active_buffs.values():
            if buff.get("effect") == effect_name and int(buff.get("expires_at", 0)) > now_ts:
                return True
        return False

    def _activate_buff(self, item_id):
        item = ITEM_CATALOG.get(item_id, {})
        buff = item.get("buff")
        if not buff:
            return
        now_ts = int(datetime.now().timestamp())
        expiration = int(buff.get("expiration", 0))
        if expiration <= 0:
            return
        self.active_buffs[item_id] = {
            "name": item.get("name", item_id),
            "effect": buff.get("effect", ""),
            "value": int(buff.get("value", 0)),
            "interval": int(buff.get("interval", 0)),
            "expires_at": now_ts + expiration,
            "next_tick_at": now_ts + int(buff.get("interval", expiration)),
            "description": buff.get("description", ""),
        }
        self.add_log("增益", f"{item.get('name', item_id)}效果已生效：{buff.get('description', '')}")

    def _tick_buffs(self, now_ts):
        messages = []
        for item_id, buff in list(self.active_buffs.items()):
            expires_at = int(buff.get("expires_at", 0))
            if expires_at <= now_ts:
                self.active_buffs.pop(item_id, None)
                messages.append(f"{buff.get('name', item_id)}的增益已结束。")
                continue

            effect = buff.get("effect")
            interval = int(buff.get("interval", 0))
            if effect == "coin" and interval > 0:
                next_tick_at = int(buff.get("next_tick_at", now_ts + interval))
                gained = 0
                while next_tick_at <= now_ts and next_tick_at <= expires_at:
                    gained += int(buff.get("value", 0))
                    next_tick_at += interval
                if gained:
                    self.stats["coins"] = int(self.stats.get("coins", 0)) + gained
                    buff["next_tick_at"] = next_tick_at
                    messages.append(f"{buff.get('name', item_id)}带来了 {gained} 金币。")
        return messages

    def gain_exp(self, amount):
        amount = max(0, self._safe_int(amount, 0))
        if amount <= 0:
            return
        self.stats["exp"] = self._safe_int(self.stats.get("exp", 0), 0) + amount
        while self.stats["exp"] >= self.level_exp_required():
            required = self.level_exp_required()
            self.stats["exp"] -= required
            self.stats["level"] = self._safe_int(self.stats.get("level", 1), 1) + 1
            reward = 2 + self._safe_int(self.stats.get("level", 1), 1) // 5
            self.stats["coins"] = self._safe_int(self.stats.get("coins", 0), 0) + reward
            self.add_log(
                "成长",
                f"等级提升到 Lv.{self.stats['level']}，下一级需要 {self.level_exp_required()} 经验，获得 {reward} 金币。",
            )

    def feed(self, item_id):
        item = ITEM_CATALOG.get(item_id)
        if not item or item["type"] != "food":
            return False, "这个物品不能投喂。"
        if self.inventory.get(item_id, 0) <= 0:
            return False, f"{item['name']}数量不足。"
        self.inventory[item_id] -= 1
        self.data["daily_counts"]["feed"] = self._safe_int(self.data["daily_counts"].get("feed", 0), 0) + 1
        self.adjust_stats(item["effects"])
        self._activate_buff(item_id)
        self.gain_exp(2)
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
        self._activate_buff(item_id)
        self.gain_exp(3)
        self.add_log("背包", f"使用了{item['name']}。")
        return True, f"使用了{item['name']}。"

    def buy_item(self, item_id):
        item = ITEM_CATALOG.get(item_id)
        if not item:
            return False, "商品不存在。"
        price = int(item["price"])
        if self._safe_int(self.stats.get("coins", 0), 0) < price:
            return False, "金币不足。"
        self.stats["coins"] = self._safe_int(self.stats.get("coins", 0), 0) - price
        self.inventory[item_id] = self.inventory.get(item_id, 0) + 1
        self.add_log("商店", f"购买了{item['name']}，花费 {price} 金币。")
        return True, f"购买了{item['name']}。"

    def complete_task(self, task_id, silent=False):
        task = TASK_CATALOG.get(task_id)
        if not task or self.tasks.get(task_id):
            return False
        if not self.task_claimable(task_id):
            if not silent:
                self.add_log("任务", f"「{task['title']}」还没有达到领取条件。")
            return False
        self.tasks[task_id] = True
        self.stats["coins"] = self._safe_int(self.stats.get("coins", 0), 0) + self._safe_int(task["reward"], 0)
        self.gain_exp(task["exp"])
        if not silent:
            self.add_log("任务", f"完成「{task['title']}」，获得 {task['reward']} 金币和 {task['exp']} 经验。")
        else:
            self._commit()
        return True

    def rest(self):
        self.data["daily_counts"]["rest"] = self._safe_int(self.data["daily_counts"].get("rest", 0), 0) + 1
        self.adjust_stats({"energy": 16, "mood": 3, "hunger": -6})
        self.complete_task("sleep_once", silent=True)
        self.add_log("休息", "安排了一次休息，体力恢复。")

    def walk(self):
        self.data["daily_counts"]["walk"] = self._safe_int(self.data["daily_counts"].get("walk", 0), 0) + 1
        self.adjust_stats({"energy": -5, "mood": 2})
        self.complete_task("walk_once", silent=True)
        self.add_log("互动", "让桌宠走动了一小段。")

    def touch(self):
        touches = self._safe_int(self.data["daily_counts"].get("touch", 0), 0)
        self.data["daily_counts"]["touch"] = touches + 1
        if touches < 5:
            mood_gain = 2
        else:
            mood_gain = 1
        effects = {"mood": mood_gain, "energy": -1}
        self.adjust_stats(effects)
        self.complete_task("touch_once", silent=True)
        self.add_log("互动", "温柔互动只提升心情；好感需要通过完整关怀、专注或礼物慢慢建立。")

    def daily_care(self):
        if self.tasks.get("care_plan"):
            return False, "今天已经完成过关怀计划。"
        counts = self.data.get("daily_counts", {})
        if (
            self._safe_int(counts.get("feed", 0), 0) < 2
            or self._safe_int(counts.get("touch", 0), 0) < 5
            or self._safe_int(counts.get("walk", 0), 0) < 1
            or self._safe_int(counts.get("rest", 0), 0) < 1
            or self._safe_int(self.data.get("companion_seconds", 0), 0) < 1200
        ):
            return False, "完整关怀需要先完成 2 次投喂、5 次温柔互动、1 次散步、1 次休息，并陪伴至少 20 分钟。"
        self.data["daily_counts"]["care"] = 1
        self.adjust_stats({"hunger": 2, "mood": 2, "energy": 1, "affection": 1})
        self.complete_task("care_plan", silent=True)
        self.add_log("关怀", "完成今日关怀计划，四项状态都获得了照顾。")
        return True, "完成今日关怀，状态和好感都提升了。"

    def reset_daily_tasks(self):
        for key in TASK_CATALOG:
            self.tasks[key] = False
        self.data["daily_counts"] = deepcopy(DEFAULT_DAILY_COUNTS)
        self.add_log("任务", "每日任务已重置。")

    def set_setting(self, key, value):
        self.settings[key] = value
        labels = {
            "opacity": "透明度",
            "always_on_top": "置顶",
            "auto_feed": "自动投喂",
            "bubble_on": "气泡提示",
            "status_decay": "状态自然变化",
            "edge_snap_enabled": "贴边吸附",
            "edge_snap_threshold": "贴边距离",
            "pet_toggle_hotkey": "桌宠快捷键",
            "pat_multi_click_talk_threshold": "连续互动阈值",
        }
        self.add_log("设置", f"{labels.get(key, key)}已更新。")

    def reset_all(self):
        self.data = deepcopy(DEFAULT_DATA)
        self._rollover_today()
        self.complete_task("daily_login", silent=True)
        self.add_log("系统", "已恢复默认存档。")

    def tick(self):
        self._rollover_today()
        now_ts = int(datetime.now().timestamp())
        last_tick = self._safe_int(self.data.get("last_tick") or now_ts, now_ts)
        elapsed = max(0, min(now_ts - last_tick, 7200))
        self.data["last_tick"] = now_ts
        messages = []

        if elapsed <= 0:
            return messages

        messages.extend(self._tick_buffs(now_ts))

        if self.settings.get("status_decay", True):
            effects = {}
            hunger_drop = int(elapsed // 300)
            energy_drop = int(elapsed // 600)
            mood_drop = int(elapsed // 900)
            if hunger_drop and not self._has_buff("hunger_stop"):
                effects["hunger"] = -hunger_drop
            if energy_drop:
                effects["energy"] = -energy_drop
            if mood_drop and not self._has_buff("mood_guard"):
                effects["mood"] = -mood_drop
            if effects:
                self.adjust_stats(effects)

        self.data["companion_seconds"] = self._safe_int(self.data.get("companion_seconds", 0), 0) + elapsed
        goal_seconds = max(45, self._safe_int(self.settings.get("companion_goal_minutes", 45), 45)) * 60
        if self.data["companion_seconds"] >= goal_seconds:
            if self.complete_task("companion", silent=True):
                messages.append("陪伴任务完成，奖励已到账。")

        if self.settings.get("auto_feed", True) and self.stats.get("hunger", 0) < 40:
            auto_message = self._try_auto_feed()
            if auto_message:
                messages.append(auto_message)

        if self.stats.get("hunger", 0) <= 25:
            messages.append("我有点饿了，可以投喂一点食物。")
        elif self.stats.get("energy", 0) <= 25:
            messages.append("体力有些低，适合休息一会儿。")

        self._commit()
        for message in messages:
            if "增益已结束" in message or "金币" in message or "任务完成" in message:
                self.add_log("系统", message)
        return messages

    def _try_auto_feed(self):
        for item_id in ("fish", "milk", "ice"):
            if self.inventory.get(item_id, 0) > 0:
                ok, message = self.feed(item_id)
                if ok:
                    return f"自动投喂：{message}"
        return None

    def companion_progress(self):
        goal_seconds = max(45, self._safe_int(self.settings.get("companion_goal_minutes", 45), 45)) * 60
        seconds = self._safe_int(self.data.get("companion_seconds", 0), 0)
        return seconds, max(1, goal_seconds)

    def start_focus(self, minutes=25, title="专注时间", mode="focus"):
        minutes = max(1, int(minutes))
        now_ts = int(datetime.now().timestamp())
        total_seconds = minutes * 60
        self.data["focus_session"] = {
            "active": True,
            "paused": False,
            "mode": mode,
            "title": title,
            "total_seconds": total_seconds,
            "remaining_seconds": total_seconds,
            "ends_at": now_ts + total_seconds,
        }
        self.add_log("专注", f"开始「{title}」，预计 {minutes} 分钟。")

    def _sync_focus_remaining(self):
        session = self.focus_session
        if not session.get("active") or session.get("paused"):
            return int(session.get("remaining_seconds", 0))
        now_ts = int(datetime.now().timestamp())
        remaining = max(0, int(session.get("ends_at", 0)) - now_ts)
        session["remaining_seconds"] = remaining
        return remaining

    def pause_focus(self):
        session = self.focus_session
        if not session.get("active") or session.get("paused"):
            return
        self._sync_focus_remaining()
        session["paused"] = True
        self.add_log("专注", "专注计时已暂停。")

    def resume_focus(self):
        session = self.focus_session
        if not session.get("active") or not session.get("paused"):
            return
        now_ts = int(datetime.now().timestamp())
        session["paused"] = False
        session["ends_at"] = now_ts + int(session.get("remaining_seconds", 0))
        self.add_log("专注", "专注计时已继续。")

    def cancel_focus(self):
        session = self.focus_session
        if not session.get("active"):
            return
        title = session.get("title") or "专注"
        self.data["focus_session"] = deepcopy(DEFAULT_DATA["focus_session"])
        self.add_log("专注", f"已取消「{title}」。")

    def tick_focus(self):
        session = self.focus_session
        if not session.get("active"):
            return None
        remaining = self._sync_focus_remaining()
        if remaining > 0:
            self._commit()
            return None

        title = session.get("title") or "专注"
        mode = session.get("mode", "focus")
        total_minutes = max(1, self._safe_int(session.get("total_seconds", 0), 0) // 60)
        self.data["focus_session"] = deepcopy(DEFAULT_DATA["focus_session"])
        if mode == "focus":
            self.data["daily_counts"]["focus"] = self._safe_int(self.data["daily_counts"].get("focus", 0), 0) + 1
            self.data["daily_counts"]["focus_minutes"] = (
                self._safe_int(self.data["daily_counts"].get("focus_minutes", 0), 0) + total_minutes
            )
            effects = {"mood": 3, "energy": -6}
            if total_minutes >= 25:
                effects["affection"] = 1
            self.adjust_stats(effects)
            self.complete_task("focus_once", silent=True)
            self.stats["coins"] = self._safe_int(self.stats.get("coins", 0), 0) + 1
            self.gain_exp(2)
            message = f"「{title}」完成，奖励已到账。"
        else:
            self.adjust_stats({"energy": 8, "mood": 4})
            message = f"「{title}」结束，可以继续安排任务。"
        self.add_log("专注", message)
        return message

    def focus_progress(self):
        session = self.focus_session
        if not session.get("active"):
            return 0, 0, "暂无专注计时"
        remaining = self._sync_focus_remaining()
        total = max(1, int(session.get("total_seconds", 0)))
        title = session.get("title") or "专注"
        state = "已暂停" if session.get("paused") else "进行中"
        return total - remaining, total, f"{title} · {state} · {remaining // 60:02d}:{remaining % 60:02d}"

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
