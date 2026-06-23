# -*- coding: utf-8 -*-
"""Generate the default JSON save file for Arctic Bear Desktop Pet.

The project uses a local JSON save file as its file-based database. This script
is the database initialization script for the current implementation.

Usage:
    python docs/database/init_save_json.py
    python docs/database/init_save_json.py data/save.json
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path


TASK_IDS = [
    "daily_login",
    "companion",
    "feed_once",
    "touch_once",
    "sleep_once",
    "walk_once",
    "focus_once",
    "care_plan",
    "wellness",
    "bond_breakthrough",
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


DEFAULT_LLM_CONFIG = {
    "enabled": False,
    "provider": "deepseek",
    "model": "deepseek-chat",
    "api_url": "https://api.deepseek.com",
    "api_key": "",
    "auto_talk": True,
    "temperature": 0.72,
    "max_tokens": 320,
}


DEFAULT_SAVE = {
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
    "tasks": {task_id: False for task_id in TASK_IDS},
    "settings": {
        "opacity": 1.0,
        "always_on_top": True,
        "auto_feed": False,
        "bubble_on": True,
        "status_decay": True,
        "edge_snap_enabled": True,
        "edge_snap_threshold": 48,
        "pet_toggle_hotkey": "Ctrl+Alt+B",
        "pet_corner_hotkey": "Ctrl+Alt+M",
        "companion_goal_minutes": 45,
        "pat_multi_click_talk_threshold": 6,
        "llm": deepcopy(DEFAULT_LLM_CONFIG),
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


def build_default_save() -> dict:
    data = deepcopy(DEFAULT_SAVE)
    now = datetime.now().isoformat(timespec="seconds")
    data["created_at"] = now
    data["updated_at"] = now
    data["logs"] = [f"[{datetime.now().strftime('%H:%M:%S')}] 系统：初始化默认 JSON 存档。"]
    return data


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "data" / "save.template.json"
    if not output_path.is_absolute():
        output_path = root / output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = build_default_save()
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"JSON_SAVE_CREATED: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
