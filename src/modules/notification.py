from src.modules.common import ModulePage


class NotificationPage(ModulePage):
    def __init__(self):
        super().__init__(
            "通知日志与应用展示模块",
            "负责气泡提示、操作日志、成长记录和应用展示材料，让用户能看到桌宠的状态变化和项目亮点。",
            highlights=[
                ("提示类型", "4 类", "状态、任务、背包、系统"),
                ("日志来源", "6 类", "点击、拖拽、睡觉、喂养、任务、设置"),
                ("展示材料", "文档", "中期答辩、UML、模块说明"),
            ],
            tasks=[
                {
                    "status": "待实现",
                    "title": "气泡提示",
                    "description": "在桌宠附近显示短提示，避免所有反馈都挤在主控台里。",
                    "items": ["饥饿提醒", "任务完成提醒", "睡醒提示"],
                },
                {
                    "status": "待实现",
                    "title": "操作日志",
                    "description": "记录用户与桌宠互动行为，便于回顾和调试。",
                    "items": ["单击互动", "双击挥手", "投喂与购买", "状态变化"],
                },
                {
                    "status": "已整理",
                    "title": "项目展示内容",
                    "description": "保留文档与 UML 作为项目答辩材料，并在主控台中展示当前完成度。",
                    "items": ["项目主题及创意", "模块说明文档", "UML 讲解材料"],
                },
            ],
            actions=["显示气泡", "写入日志", "清空日志", "打开文档"],
        )
