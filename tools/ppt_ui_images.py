from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


INK = (30, 82, 110)
INK_2 = (69, 112, 142)
BLUE = (92, 198, 225)
CYAN = (129, 225, 216)
PINK = (255, 132, 184)
GOLD = (255, 203, 96)
LINE = (152, 220, 239)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc")
    if not path.exists():
        path = Path("C:/Windows/Fonts/simhei.ttf")
    return ImageFont.truetype(str(path), size=size)


def rgba(color: tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for para in str(text).split("\n"):
        line = ""
        for ch in para:
            candidate = line + ch
            if not line or text_size(draw, candidate, fnt)[0] <= width:
                line = candidate
            else:
                lines.append(line)
                line = ch
        lines.append(line)
    return lines


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt: ImageFont.FreeTypeFont, fill, width: int | None = None, gap: int = 5, align: str = "left") -> int:
    x, y = xy
    lines = wrap_text(draw, text, fnt, width) if width else str(text).split("\n")
    yy = y
    for line in lines:
        tw, th = text_size(draw, line, fnt)
        xx = x + ((width - tw) // 2 if width and align == "center" else 0)
        draw.text((xx, yy), line, font=fnt, fill=fill)
        yy += th + gap
    return yy


def remove_green_key(src: Image.Image) -> Image.Image:
    image = src.convert("RGBA")
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if g > 110 and g > r * 1.28 and g > b * 1.28:
                pixels[x, y] = (r, g, b, 0)
    return image


def paste_fit(base: Image.Image, path: Path, box: tuple[int, int, int, int], padding: int = 0) -> None:
    if not path.exists():
        return
    src = Image.open(path).convert("RGBA")
    if "chromakey" in path.name.lower():
        src = remove_green_key(src)
    x1, y1, x2, y2 = box
    max_w, max_h = x2 - x1 - padding * 2, y2 - y1 - padding * 2
    scale = min(max_w / src.width, max_h / src.height)
    dst = src.resize((max(1, int(src.width * scale)), max(1, int(src.height * scale))), Image.Resampling.LANCZOS)
    px, py = x1 + padding + (max_w - dst.width) // 2, y1 + padding + (max_h - dst.height) // 2
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    mask = dst.getchannel("A")
    sh = Image.new("RGBA", dst.size, (0, 0, 0, 0))
    sh.putalpha(mask.point(lambda a: min(95, int(a * 0.42))))
    shadow.alpha_composite(sh, (px + 10, py + 14))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)))
    base.alpha_composite(dst, (px, py))


def panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill=(255, 255, 255, 210), radius: int = 14) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=rgba(LINE, 215), width=2)


def button(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str, active: bool = False) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=11, fill=rgba(BLUE, 220) if active else (255, 255, 255, 210), outline=rgba(LINE, 215), width=2)
    if active:
        draw.rounded_rectangle((x1 + (x2 - x1) // 2, y1, x2, y2), radius=11, fill=rgba(PINK, 125))
    label_font = font(17, True)
    _, th = text_size(draw, label, label_font)
    draw.text((x1 + 26, y1 + (y2 - y1 - th) // 2 - 1), label, font=label_font, fill=(255, 255, 255, 255) if active else rgba(INK, 255))


def base(root: Path, active: str) -> Image.Image:
    w, h = 1478, 989
    img = Image.new("RGBA", (w, h), (240, 252, 255, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle((0, 0, w, 38), fill=(29, 29, 29, 255))
    draw.text((16, 9), "北极熊桌面宠物系统", font=font(15), fill=(255, 255, 255, 255))
    for idx, color in enumerate([(184, 235, 250, 86), (255, 184, 215, 68), (255, 226, 145, 42)]):
        y0 = 105 + idx * 215
        top = [(x, y0 + math.sin(x / 205 + idx) * 28) for x in range(295, w + 120, 80)]
        bottom = [(x, y + 55) for x, y in reversed(top)]
        draw.polygon(top + bottom, fill=color)
    draw.rectangle((0, 38, 298, h), fill=(255, 255, 255, 230), outline=rgba(LINE, 155), width=2)
    draw.text((36, 72), "PolarBear", font=font(39, True), fill=rgba(INK, 255))
    draw.text((24, 137), "桌面宠物应用", font=font(18, True), fill=rgba(INK_2, 255))
    button(draw, (24, 180, 260, 222), "实时陪伴控制台")
    panel(draw, (24, 252, 260, 422), fill=(238, 253, 255, 208))
    draw.text((42, 280), "ARCTIC HUB", font=font(18, True), fill=rgba(BLUE, 255))
    draw.text((42, 320), "暖暖陪伴", font=font(23, True), fill=rgba(PINK, 255))
    draw.text((42, 362), "状态、动作、提醒\n一屏掌握", font=font(14, True), fill=rgba(INK_2, 255))
    paste_fit(img, root / "assets/polar_bear/polar-bear-realistic-chromakey.png", (148, 275, 232, 400))
    button(draw, (24, 438, 260, 490), "显示 / 隐藏桌宠  Ctrl+Alt+B", True)
    navs = ["宠物状态", "成长等级", "课程提醒", "动作管理", "聊天互动", "外观装扮", "系统设置"]
    y = 505
    for nav in navs:
        button(draw, (24, y, 260, y + 54), nav, nav == active)
        y += 72
    draw.line((289, 52, 289, 920), fill=rgba(INK_2, 125), width=1)
    draw.line((1468, 54, 1468, 680), fill=rgba(INK_2, 125), width=1)
    return img


def dashboard(root: Path, path: Path) -> None:
    img = base(root, "宠物状态")
    draw = ImageDraw.Draw(img, "RGBA")
    panel(draw, (328, 65, 1432, 168))
    draw.text((355, 88), "北极熊桌宠控制面板", font=font(36, True), fill=rgba(INK, 255))
    draw.text((356, 132), "Dreamy Arctic Pet Hub · 可爱桌宠管理中心", font=font(17, True), fill=rgba(INK_2, 255))
    button(draw, (1222, 84, 1410, 147), "06月23日  00:28", True)
    panel(draw, (328, 185, 1068, 718))
    draw.text((358, 255), "POLAR COMPANION CENTER", font=font(17, True), fill=rgba(BLUE, 255))
    draw.text((358, 345), "和小熊一起\n管理今天", font=font(37, True), fill=rgba(INK, 255))
    draw_text(draw, (358, 485), "明亮通透的冰雪童话控制中心，集中查看状态、课程提醒、动作触发和桌宠日志。", font(20), rgba(INK_2, 255), width=260)
    panel(draw, (603, 277, 825, 628), fill=(240, 254, 255, 210))
    paste_fit(img, root / "assets/polar_bear/polar-bear-realistic-chromakey.png", (630, 300, 790, 582))
    draw.rounded_rectangle((638, 585, 790, 612), radius=12, fill=(255, 255, 255, 215), outline=rgba(LINE, 220))
    draw.text((654, 589), "● 在线陪伴", font=font(14, True), fill=rgba(INK_2, 255))
    panel(draw, (850, 212, 1035, 492))
    draw.arc((875, 245, 1015, 385), 110, 390, fill=rgba(BLUE, 230), width=17)
    draw.text((913, 300), "43", font=font(52, True), fill=rgba(INK, 255))
    draw_text(draw, (882, 408), "需要照顾\n金币 19 / 好感 64%\n任务 1/10", font(15), rgba(INK_2, 255), width=122, align="center")
    button(draw, (850, 512, 1035, 562), "唤出桌宠  Ctrl+Alt+B", True)
    button(draw, (850, 575, 1035, 625), "互动反应")
    button(draw, (850, 640, 1035, 690), "开始专注")
    for i, (name, value, desc) in enumerate([("心情值", "100%", "轻触互动可提升心情"), ("饱食度", "0%", "投喂鱼干和热牛奶恢复"), ("活跃度", "9%", "睡觉和短休可恢复")]):
        x = 328 + i * 240
        panel(draw, (x, 738, x + 218, 892), fill=(255, 250, 252, 208) if i == 0 else (255, 254, 236, 208) if i == 2 else (252, 255, 255, 208))
        draw.text((x + 14, 756), name, font=font(17, True), fill=rgba(INK_2, 255))
        draw.text((x + 14, 790), value, font=font(34, True), fill=rgba(INK, 255))
        draw.rounded_rectangle((x + 14, 835, x + 190, 846), radius=5, fill=(211, 239, 247, 255))
        draw.rounded_rectangle((x + 14, 835, x + 14 + (175 if i == 0 else 14 if i == 2 else 1), 846), radius=5, fill=rgba(BLUE, 220))
        draw.text((x + 14, 862), desc, font=font(15), fill=rgba(INK_2, 255))
    panel(draw, (1085, 185, 1435, 735))
    draw.text((1108, 212), "今日提醒", font=font(25, True), fill=rgba(INK, 255))
    for y, name, desc in [(252, "今日课程", "专业英语"), (348, "上课时间", "今天 08:20"), (444, "地点提醒", "2419"), (540, "消息通知", "今日任务 1/10 · 课程提醒会同步到桌宠气泡")]:
        panel(draw, (1110, y, 1406, y + 78), fill=(255, 255, 255, 190))
        draw.text((1125, y + 17), name, font=font(17, True), fill=rgba(INK, 255))
        draw.text((1125, y + 47), desc, font=font(15, True), fill=rgba(INK_2, 255))
    draw.text((1110, 655), "桌宠互动日志", font=font(23, True), fill=rgba(INK, 255))
    img.convert("RGB").save(path, "PNG", optimize=True)


def course(root: Path, path: Path) -> None:
    img = base(root, "课程提醒")
    draw = ImageDraw.Draw(img, "RGBA")
    draw.text((340, 75), "课程提醒与消息中心", font=font(39, True), fill=rgba(INK, 255))
    draw.text((340, 122), "管理今日课程、地点和提醒气泡；需要专注时也可以从这里启动番茄钟。", font=font(18), fill=rgba(INK_2, 255))
    panel(draw, (340, 150, 1418, 340))
    draw.text((365, 177), "SMART COURSE ASSISTANT", font=font(17, True), fill=rgba(BLUE, 255))
    draw.text((365, 216), "下一节课智能提醒", font=font(34, True), fill=rgba(INK, 255))
    draw.text((365, 272), "今天 08:20 · 《专业英语》\n地点：2419 · 时间还充裕，我会继续帮你盯着。", font=font(20, True), fill=rgba(INK, 255))
    button(draw, (1295, 220, 1392, 272), "立即提醒", True)
    panel(draw, (340, 360, 1418, 904))
    draw.text((368, 390), "我的课表预览", font=font(25, True), fill=rgba(PINK, 255))
    x0, y0, cw, rh = 370, 430, 128, 79
    headers = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    rows = [("08:20\n第一大节", ["", "专业英语\n@ 2419", "软件工程导论\n@ 2426", "计算机网络\n@ 2438云平台\n综合实训室", "数据结构与算法\n@ 2426", "", ""]),
            ("10:20\n第二大节", ["概率论与数理统计Ⅱ\n@ 3418", "毛泽东思想和中国特色社会主义理论体系概论\n@ 3106", "概率论与数理统计Ⅱ\n@ 3614", "计算机网络\n@ 2438云平台\n综合实训室", "数据结构与算法\n@ 2526智能与分布计算实验室", "", ""]),
            ("14:10\n第三大节", ["大学体育IV（柔力球01）\n@ 综合馆", "", "软件工程导论\n@ 2426", "Java Web开发\n@ 2432", "创新创业基础\n@ 3106", "", ""]),
            ("16:00\n第四大节", ["", "形势与政策IV\n@ 3304", "", "Java Web开发\n@ 2432", "", "", ""])]
    for i, h in enumerate(headers):
        draw.rectangle((x0 + i * cw, y0, x0 + (i + 1) * cw, y0 + rh), fill=(60, 60, 60, 255) if i == 0 else (222, 244, 250, 255), outline=rgba(LINE, 220))
        draw_text(draw, (x0 + i * cw + 5, y0 + 28), h, font(17, True), rgba(INK, 255), width=cw - 10, align="center")
    for r, (time_label, cells) in enumerate(rows):
        yy = y0 + rh * (r + 1)
        draw.rectangle((x0, yy, x0 + cw, yy + rh), fill=(225, 248, 255, 255), outline=rgba(LINE, 220))
        draw_text(draw, (x0 + 10, yy + 15), time_label, font(16, True), rgba(INK, 255), width=cw - 20)
        for c, cell in enumerate(cells, 1):
            draw.rectangle((x0 + c * cw, yy, x0 + (c + 1) * cw, yy + rh), fill=(255, 255, 255, 178), outline=rgba(LINE, 185))
            draw_text(draw, (x0 + c * cw + 5, yy + 10), cell, font(14), rgba(INK, 255), width=cw - 10, gap=2, align="center")
    img.convert("RGB").save(path, "PNG", optimize=True)


def chat(root: Path, path: Path) -> None:
    img = base(root, "聊天互动")
    draw = ImageDraw.Draw(img, "RGBA")
    draw.text((340, 72), "聊天互动中心", font=font(39, True), fill=rgba(INK, 255))
    draw.text((340, 122), "一句话就能触发聊天、提醒或陪伴反馈。", font=font(18), fill=rgba(INK_2, 255))
    panel(draw, (340, 160, 1418, 300))
    draw.text((368, 190), "AI 大模型陪伴", font=font(25, True), fill=rgba(PINK, 255))
    draw.text((368, 235), "联网大模型：已启用 · 智谱 GLM · glm-4-plus · 已填写 Key，具体 API Key、模型和地址可在系统设置中修改。", font=font(17), fill=rgba(INK_2, 255))
    for i, lab in enumerate(["打招呼", "今日安排", "鼓励我", "摸摸头", "饿了吗", "休息建议"]):
        button(draw, (340 + (i % 3) * 365, 324 + (i // 3) * 68, 680 + (i % 3) * 365, 370 + (i // 3) * 68), lab, True)
    panel(draw, (340, 500, 1418, 952))
    draw.text((378, 536), "对话记录", font=font(26, True), fill=rgba(PINK, 255))
    bubbles = [("left", "17:58  北极熊", "飞流直下三千尺，疑是银河落九天。"), ("right", "18:01  你", "星期一我要上啥课"), ("left", "18:01  北极熊", "周一10:20有《概率论与数理统计Ⅱ》，地点3418，记得带课本哦~"), ("left", "18:02  北极熊", "可以喂我一点食物，我会更有精神。")]
    y = 588
    for side, meta, msg in bubbles:
        if side == "left":
            draw.ellipse((400, y + 5, 445, y + 50), fill=(221, 249, 255, 255), outline=rgba(LINE, 210))
            draw.text((417, y + 17), "熊", font=font(14, True), fill=rgba(INK, 255))
            panel(draw, (465, y, 835, y + 78), fill=(255, 255, 255, 222))
            draw.text((485, y + 12), meta, font=font(15, True), fill=rgba(BLUE, 255))
            draw_text(draw, (485, y + 38), msg, font(18), rgba(INK, 255), width=320)
        else:
            draw.rounded_rectangle((970, y, 1330, y + 78), radius=16, fill=rgba(CYAN, 210))
            draw.rounded_rectangle((1150, y, 1330, y + 78), radius=16, fill=rgba(PINK, 112))
            draw.text((990, y + 12), meta, font=font(15, True), fill=(255, 255, 255, 255))
            draw_text(draw, (990, y + 38), msg, font(18), (255, 255, 255, 255), width=300)
        y += 103
    img.convert("RGB").save(path, "PNG", optimize=True)


def growth(root: Path, path: Path) -> None:
    img = base(root, "成长等级")
    draw = ImageDraw.Draw(img, "RGBA")
    draw.text((340, 72), "成长等级中心", font=font(39, True), fill=rgba(INK, 255))
    draw.text((340, 122), "等级、经验、好感上限、每日好感额度和任务奖励都在这里单独管理。", font=font(18), fill=rgba(INK_2, 255))
    panel(draw, (340, 175, 1418, 455))
    draw.text((368, 208), "ARCTIC GROWTH CORE", font=font(20, True), fill=rgba(BLUE, 255))
    draw.text((368, 265), "Lv.2", font=font(64, True), fill=rgba(INK, 255))
    draw.text((378, 365), "「新手饲养员」\n金币 19 · 好感 64% · 陪伴 18 天", font=font(24, True), fill=rgba(INK, 255))
    for i, (label, value) in enumerate([("升级经验 292/400 EXP", .73), ("好感上限 64/24%", .64), ("今日好感 0/1", .03), ("今日陪伴 1/45 分钟", .10)]):
        x, y = 890, 213 + i * 55
        draw.rounded_rectangle((x, y, 1388, y + 28), radius=14, fill=(220, 242, 248, 255), outline=rgba(LINE, 180))
        draw.rounded_rectangle((x, y, x + int(498 * value), y + 28), radius=14, fill=rgba(BLUE, 210))
        draw.rounded_rectangle((x + int(498 * max(0, value - .24)), y, x + int(498 * value), y + 28), radius=14, fill=rgba(PINK, 120))
        draw_text(draw, (x, y + 3), label, font(16, True), rgba(INK, 255), width=498, align="center")
    for i, lab in enumerate(["完整关怀", "领取可领任务", "25 分钟专注", "安排休息"]):
        button(draw, (340 + i * 275, 480, 600 + i * 275, 530), lab, True)
    for i, (name, desc) in enumerate([("困难成长规则", "普通触摸只提升心情，不直接增加好感。\n好感受等级上限和每日上限双重限制。\n金币主要来自高门槛任务和少量升级奖励。"), ("下一阶段", "Lv.4 解锁「稳定陪伴」。\n好感上限提升到 38%，每日好感额度 1。"), ("今日行为记录", "投喂 0 次 / 摸摸 0 次 / 散步 0 次\n休息 0 次 / 专注 0 分钟 / 完整关怀 0 次")]):
        x = 340 + i * 385
        panel(draw, (x, 555, x + 360, 735))
        draw.text((x + 28, 590), name, font=font(24, True), fill=rgba(PINK, 255))
        draw_text(draw, (x + 28, 640), desc, font(17), rgba(INK_2, 255), width=300)
    draw.text((340, 765), "等级路线", font=font(25, True), fill=rgba(PINK, 255))
    for i, (lv, name, status) in enumerate([("Lv.1", "新手饲养员", "已解锁"), ("Lv.4", "稳定陪伴", "未解锁"), ("Lv.8", "默契伙伴", "未解锁")]):
        x = 340 + i * 382
        panel(draw, (x, 800, x + 348, 955))
        draw.text((x + 28, 830), lv, font=font(25, True), fill=rgba(BLUE, 255))
        draw.text((x + 28, 875), name, font=font(24, True), fill=rgba(INK, 255))
        draw.text((x + 28, 925), status, font=font(17), fill=rgba(INK_2, 255))
    img.convert("RGB").save(path, "PNG", optimize=True)


def generate_ui_reference_images(root: Path, build_dir: Path) -> dict[str, Path]:
    out = build_dir / "ui_reference"
    out.mkdir(parents=True, exist_ok=True)
    result = {
        "dashboard": out / "dashboard.png",
        "course": out / "course.png",
        "chat": out / "chat.png",
        "growth": out / "growth.png",
    }
    dashboard(root, result["dashboard"])
    course(root, result["course"])
    chat(root, result["chat"])
    growth(root, result["growth"])
    return result
