from src.modules.common import ModulePage


class InteractionPage(ModulePage):
    def __init__(self):
        super().__init__(
            "桌宠形象与桌面交互模块",
            "负责北极熊桌宠窗口、动作播放、鼠标交互和右键菜单，是整个桌宠系统最靠近用户的入口。",
            highlights=[
                ("已接入动作", "8 组", "待机、眨眼、互动、挥手、走路、跳跃、拖拽、睡觉"),
                ("交互方式", "4 类", "单击、双击、拖拽、右键菜单"),
                ("素材格式", "PNG 序列", "兼容旧项目 role/action 动作包"),
            ],
            tasks=[
                {
                    "status": "已完成",
                    "title": "真实视频帧动作系统",
                    "description": "将可灵生成的视频拆为透明 PNG 序列，并接入旧项目动作配置格式。",
                    "items": ["待机读取 video2528_idle_blink", "双击触发 wave", "拖拽过程播放 drag"],
                },
                {
                    "status": "已完成",
                    "title": "点击与双击冲突处理",
                    "description": "单击延迟确认，双击时取消单击动作，避免 touch 和 wave 同时触发。",
                    "items": ["单击播放互动", "双击播放挥手", "拖动超过阈值才进入拖拽"],
                },
                {
                    "status": "待完善",
                    "title": "动作过渡与边界行为",
                    "description": "继续优化动作之间的衔接，使睡觉、走路、拖拽、回待机更自然。",
                    "items": ["增加起身动作", "增加边缘转身动作", "增加动作冷却时间"],
                },
            ],
            actions=["播放互动", "播放挥手", "播放睡觉", "显示桌宠", "隐藏桌宠"],
        )
