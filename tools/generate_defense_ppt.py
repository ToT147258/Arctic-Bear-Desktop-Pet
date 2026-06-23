from __future__ import annotations

import math
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ppt_ui_images import generate_ui_reference_images


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "deliverables"
BUILD_DIR = OUT_DIR / "ppt_render_tmp"
ASSETS = ROOT / "assets"
SCREENSHOTS = ROOT / "docs" / "screenshots"

W, H = 1920, 1080
EMU_W, EMU_H = 12192000, 6858000

INK = (30, 82, 110)
INK_2 = (69, 112, 142)
BLUE = (92, 198, 225)
CYAN = (129, 225, 216)
PINK = (255, 132, 184)
PURPLE = (182, 170, 255)
GOLD = (255, 203, 96)
GREEN = (119, 210, 176)
LINE = (152, 220, 239)


def _font_path(name: str) -> Path:
    path = Path("C:/Windows/Fonts") / name
    return path if path.exists() else Path("C:/Windows/Fonts/msyh.ttc")


FONT_REG = _font_path("msyh.ttc")
FONT_BOLD = _font_path("msyhbd.ttc")
FONT_MONO = _font_path("consola.ttf")
_FONT_CACHE: dict[tuple[int, bool, bool], ImageFont.FreeTypeFont] = {}


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold, mono)
    if key not in _FONT_CACHE:
        path = FONT_MONO if mono else (FONT_BOLD if bold else FONT_REG)
        if not path.exists():
            path = FONT_REG
        _FONT_CACHE[key] = ImageFont.truetype(str(path), size=size)
    return _FONT_CACHE[key]


def rgba(color: tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    if not text:
        return 0, 0
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for para in str(text).split("\n"):
        if not para:
            lines.append("")
            continue
        line = ""
        for ch in para:
            candidate = line + ch
            if text_size(draw, candidate, fnt)[0] <= width or not line:
                line = candidate
            else:
                lines.append(line.rstrip())
                line = ch.lstrip()
        if line:
            lines.append(line.rstrip())
    return lines


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    width: int | None = None,
    line_gap: int = 8,
    align: str = "left",
) -> int:
    x, y = xy
    lines = wrap_text(draw, text, fnt, width) if width else str(text).split("\n")
    yy = y
    for line in lines:
        tw, th = text_size(draw, line, fnt)
        xx = x
        if width and align == "center":
            xx = x + (width - tw) // 2
        elif width and align == "right":
            xx = x + width - tw
        draw.text((xx, yy), line, font=fnt, fill=fill)
        yy += th + line_gap
    return yy


def background() -> Image.Image:
    img = Image.new("RGBA", (W, H), (238, 250, 255, 255))
    pix = img.load()
    for y in range(H):
        ty = y / (H - 1)
        for x in range(W):
            tx = x / (W - 1)
            t = min(1.0, ty * 0.68 + tx * 0.32)
            c1 = (235, 250, 255)
            c2 = (255, 244, 248)
            pix[x, y] = tuple(lerp(c1[i], c2[i], t) for i in range(3)) + (255,)
    draw = ImageDraw.Draw(img, "RGBA")
    for idx, color in enumerate([(184, 235, 250, 72), (255, 184, 215, 62), (255, 226, 145, 42)]):
        y0 = 165 + idx * 210
        top = [(x, y0 + math.sin(x / 240 + idx) * 44) for x in range(-80, W + 120, 90)]
        bottom = [(x, y + 72) for x, y in reversed(top)]
        draw.polygon(top + bottom, fill=color)
    for i in range(80):
        x = (91 + i * 229) % W
        y = (57 + i * 137) % H
        if i % 6 == 0:
            draw.line((x - 12, y, x + 12, y), fill=(255, 255, 255, 140), width=3)
            draw.line((x, y - 12, x, y + 12), fill=(255, 255, 255, 140), width=3)
        else:
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255, 110))
    return img


def shadow(img: Image.Image, box: tuple[int, int, int, int], radius: int = 36) -> None:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1, y1 + 16, x2, y2 + 16), radius=radius, fill=(35, 97, 125, 52))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(26)))


def card(
    img: Image.Image,
    box: tuple[int, int, int, int],
    radius: int = 38,
    fill: tuple[int, int, int, int] = (255, 255, 255, 188),
    outline: tuple[int, int, int, int] = rgba(LINE, 210),
) -> None:
    shadow(img, box, radius)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=3)
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1 + 3, y1 + 3, x2 - 3, y1 + (y2 - y1) // 3), radius=radius, fill=(255, 255, 255, 48))


def bullet_list(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    items: list[str],
    width: int,
    fnt: ImageFont.FreeTypeFont | None = None,
    accent: tuple[int, int, int] = PINK,
) -> int:
    fnt = fnt or font(27)
    yy = y
    for item in items:
        draw.ellipse((x, yy + 14, x + 13, yy + 27), fill=rgba(accent, 255))
        yy = draw_text(draw, (x + 30, yy), item, fnt, rgba(INK_2, 255), width=width - 30, line_gap=8)
        yy += 17
    return yy


def paste_image(img: Image.Image, path: Path, box: tuple[int, int, int, int], padding: int = 0) -> None:
    draw = ImageDraw.Draw(img, "RGBA")
    x1, y1, x2, y2 = box
    if not path.exists():
        draw.rounded_rectangle(box, radius=28, outline=rgba(LINE, 220), width=3, fill=(255, 255, 255, 120))
        draw_text(draw, (x1 + 30, y1 + 30), f"缺少图片\n{path.name}", font(26), rgba(INK_2, 255), width=x2 - x1 - 60)
        return
    src = Image.open(path).convert("RGBA")
    if "chromakey" in path.name.lower():
        # Some exported bear assets keep a vivid green key background even though
        # the filename says chromakey. Remove it before resizing to avoid green
        # blocks on the final defense slides.
        pixels = src.load()
        for yy in range(src.height):
            for xx in range(src.width):
                r, g, b, a = pixels[xx, yy]
                if g > 110 and g > r * 1.28 and g > b * 1.28:
                    pixels[xx, yy] = (r, g, b, 0)
    max_w = max(1, x2 - x1 - padding * 2)
    max_h = max(1, y2 - y1 - padding * 2)
    scale = min(max_w / src.width, max_h / src.height)
    dst = src.resize((max(1, int(src.width * scale)), max(1, int(src.height * scale))), Image.Resampling.LANCZOS)
    px = x1 + padding + (max_w - dst.width) // 2
    py = y1 + padding + (max_h - dst.height) // 2
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    mask = dst.getchannel("A")
    sh = Image.new("RGBA", dst.size, (0, 0, 0, 0))
    sh.putalpha(mask.point(lambda a: min(110, int(a * 0.45))))
    layer.alpha_composite(sh, (px + 14, py + 18))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(14)))
    img.alpha_composite(dst, (px, py))


def pill(img: Image.Image, box: tuple[int, int, int, int], label: str, fnt: ImageFont.FreeTypeFont | None = None) -> None:
    fnt = fnt or font(22, True)
    draw = ImageDraw.Draw(img, "RGBA")
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=(y2 - y1) // 2, fill=rgba(BLUE, 220))
    draw.rounded_rectangle((x1 + (x2 - x1) // 2, y1, x2, y2), radius=(y2 - y1) // 2, fill=rgba(PINK, 150))
    tw, th = text_size(draw, label, fnt)
    draw.text((x1 + (x2 - x1 - tw) // 2, y1 + (y2 - y1 - th) // 2 - 2), label, font=fnt, fill=(255, 255, 255, 255))


def header(img: Image.Image, title: str, subtitle: str = "", section: str = "") -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(img, "RGBA")
    if section:
        draw.text((96, 42), section.upper(), font=font(25, True), fill=rgba(BLUE, 255))
    draw.text((96, 82), title, font=font(58, True), fill=rgba(INK, 255))
    if subtitle:
        draw_text(draw, (100, 160), subtitle, font(26), rgba(INK_2, 255), width=1300, line_gap=6)
    return draw


def footer(img: Image.Image, idx: int, total: int) -> None:
    draw = ImageDraw.Draw(img, "RGBA")
    draw.line((96, 1012, 1824, 1012), fill=rgba(LINE, 105), width=2)
    draw.text((96, 1026), "Arctic Bear Desktop Pet · 期末答辩", font=font(22), fill=rgba(INK_2, 190))
    draw.rounded_rectangle((88, 1018, 560, 1060), radius=10, fill=(242, 250, 254, 245))
    draw.text((96, 1026), "Arctic Bear Desktop Pet", font=font(22), fill=rgba(INK_2, 190))
    label = f"{idx:02d} / {total:02d}"
    tw, _ = text_size(draw, label, font(22, True))
    draw.text((1824 - tw, 1026), label, font=font(22, True), fill=rgba(INK_2, 190))


slides: list[tuple[Path, str, str]] = []
TOTAL = 18
PPT_IMAGES: dict[str, Path] = {}


def save_slide(img: Image.Image, title: str, note: str) -> None:
    idx = len(slides) + 1
    footer(img, idx, TOTAL)
    path = BUILD_DIR / f"slide_{idx:02d}.png"
    img.convert("RGB").save(path, "PNG", optimize=True)
    slides.append((path, title, note))


def make_cover() -> None:
    img = background()
    draw = ImageDraw.Draw(img, "RGBA")
    card(img, (92, 92, 1160, 710), radius=54)
    draw.text((145, 150), "北极熊桌面宠物系统", font=font(78, True), fill=rgba(INK, 255))
    draw.text((150, 255), "PolarBear Desktop Pet", font=font(38, True), fill=rgba(BLUE, 255))
    draw_text(draw, (150, 330), "集桌宠动画、课程提醒、AI 对话、背包喂养、成长任务于一体的治愈型桌面应用。", font(32), rgba(INK_2, 255), width=860, line_gap=10)
    tags = ["PySide6 桌面 GUI", "JSON 本地存档", "OCR 课表识别", "AI 大模型聊天", "成长与任务系统"]
    for i, tag in enumerate(tags):
        pill(img, (150 + (i % 2) * 360, 505 + (i // 2) * 78, 480 + (i % 2) * 360, 560 + (i // 2) * 78), tag)
    paste_image(img, ASSETS / "polar_bear" / "polar-bear-realistic-chromakey.png", (1110, 100, 1845, 980))
    save_slide(img, "封面", "开场介绍项目名称、定位和核心能力。")


def make_two_column(title: str, subtitle: str, left_title: str, left_items: list[str], right_title: str, right_items: list[str], note: str) -> None:
    img = background()
    draw = header(img, title, subtitle, "Project")
    card(img, (95, 230, 900, 860))
    draw.text((145, 280), left_title, font=font(42, True), fill=rgba(PINK, 255))
    bullet_list(draw, 145, 360, left_items, 680)
    card(img, (980, 230, 1825, 860))
    draw.text((1035, 280), right_title, font=font(42, True), fill=rgba(BLUE, 255))
    bullet_list(draw, 1035, 360, right_items, 710, accent=BLUE)
    save_slide(img, title, note)


def make_feature_grid() -> None:
    img = background()
    draw = header(img, "系统功能总览", "主线功能围绕“看得见的桌宠”和“可管理的数据系统”展开。", "Functions")
    data = [
        ("桌宠动画", "待机眨眼、行走、跳跃、睡觉、贴墙/角落隐藏"),
        ("控制面板", "状态查看、动作触发、课程、聊天、背包、设置"),
        ("课程提醒", "课表图片 OCR、文字解析、下一节课提醒"),
        ("背包投喂", "食物购买、库存管理、投喂反馈、状态推荐"),
        ("成长任务", "等级经验、好感度、金币、每日任务、难度控制"),
        ("AI 聊天", "DeepSeek / ChatGPT / 智谱等接口配置与对话"),
    ]
    colors = [BLUE, PINK, CYAN, GOLD, GREEN, PURPLE]
    for i, (name, desc) in enumerate(data):
        x, y = 110 + (i % 3) * 595, 235 + (i // 3) * 285
        card(img, (x, y, x + 520, y + 215), radius=36)
        draw.ellipse((x + 34, y + 36, x + 92, y + 94), fill=rgba(colors[i], 220))
        draw.text((x + 116, y + 34), name, font=font(34, True), fill=rgba(INK, 255))
        draw_text(draw, (x + 40, y + 118), desc, font(25), rgba(INK_2, 255), width=440, line_gap=7)
    save_slide(img, "系统功能总览", "按六个能力模块快速展示系统全貌。")


def make_tech() -> None:
    img = background()
    draw = header(img, "技术路线与运行环境", "项目以 Python 桌面端为核心，资源、配置和存档均采用本地文件管理。", "Tech")
    card(img, (95, 235, 820, 870))
    draw.text((145, 285), "技术栈", font=font(44, True), fill=rgba(PINK, 255))
    bullet_list(draw, 145, 370, [
        "Python 3.10+：主开发语言",
        "PySide6：窗口、控件、事件与定时器",
        "Pillow / 图像帧：动画资源处理与展示",
        "pytesseract：可选 OCR 课表识别",
        "requests：大模型 HTTP API 调用",
        "JSON：本地配置、课程、存档、任务数据",
    ], 620)
    card(img, (900, 235, 1825, 870))
    draw.text((950, 285), "运行方式", font=font(44, True), fill=rgba(BLUE, 255))
    code = "pip install -r requirements.txt\npython main.py\n\nlaunch_polar_bear.bat\nlaunch_polar_bear.vbs"
    draw.rounded_rectangle((950, 365, 1765, 620), radius=28, fill=(20, 70, 94, 225))
    draw_text(draw, (985, 395), code, font(30, mono=True), (230, 252, 255, 255), width=750, line_gap=12)
    bullet_list(draw, 950, 680, ["桌宠与控制面板分离，互不遮挡主流程。", "本地 JSON 存档便于演示、迁移和检查。"], 770, accent=BLUE)
    save_slide(img, "技术路线与运行环境", "讲明技术选择、运行命令和 JSON 存储方式。")


def make_structure() -> None:
    img = background()
    draw = header(img, "项目结构与五大代码模块", "按主控、桌宠、功能页面、数据、外部服务五大模块讲解。", "Structure")
    card(img, (100, 210, 1820, 890))
    cols = [
        ("core 主控模块", ["src/core/app.py", "应用启动、主窗口、页面路由", "连接桌宠、数据、功能页"]),
        ("pet 桌宠表现模块", ["src/pet/window.py", "透明窗口、帧动画、拖拽、气泡", "贴边吸附、角落休眠、快捷键"]),
        ("features 功能页面模块", ["src/features/*.py", "状态、课程、背包、聊天、设置", "控制面板各业务页面"]),
        ("data 数据成长模块", ["src/data/store.py", "save.json、config.json", "等级、好感度、金币、任务"]),
        ("services 外部服务模块", ["src/services/*.py", "OCR 识别、课程解析、LLM 客户端", "DeepSeek / ChatGPT / 智谱等"]),
    ]
    for i, (name, lines) in enumerate(cols):
        x, y = 145 + (i % 3) * 555, 275 + (i // 3) * 290
        draw.rounded_rectangle((x, y, x + 500, y + 230), radius=30, fill=(248, 254, 255, 220), outline=rgba(LINE, 220), width=2)
        draw.text((x + 32, y + 26), name, font=font(30, True), fill=rgba(INK, 255))
        yy = y + 78
        for line in lines:
            draw.text((x + 32, yy), line, font=font(23, "src/" in line), fill=rgba(INK_2, 255))
            yy += 43
    save_slide(img, "项目结构与五大代码模块", "说明代码已经分层，后面逐个模块讲解。")


def make_architecture() -> None:
    img = background()
    draw = header(img, "系统总体架构", "桌宠窗口负责表现，控制面板负责管理，数据层负责持久化，服务层负责外部能力。", "Architecture")
    layers = [
        ("用户操作层", "鼠标点击 / 拖拽 / 快捷键 / 控制面板按钮"),
        ("界面表现层", "透明桌宠窗口、可爱控制面板、聊天气泡、提醒弹窗"),
        ("业务逻辑层", "动作状态机、课程提醒、背包投喂、成长任务、聊天上下文"),
        ("数据资源层", "JSON 存档、课程表、配置、动画帧、食物图片"),
        ("外部服务层", "OCR 组件、大模型 API、Windows 桌面启动器"),
    ]
    colors = [BLUE, PINK, CYAN, GOLD, PURPLE]
    for i, (name, desc) in enumerate(layers):
        y = 220 + i * 145
        card(img, (180, y, 1740, y + 105), radius=34)
        draw.rounded_rectangle((210, y + 22, 400, y + 82), radius=30, fill=rgba(colors[i], 225))
        draw.text((240, y + 34), name, font=font(24, True), fill=(255, 255, 255, 255))
        draw.text((450, y + 32), desc, font=font(30, True), fill=rgba(INK, 255))
        if i < 4:
            draw.line((960, y + 110, 960, y + 137), fill=rgba(BLUE, 180), width=5)
            draw.polygon([(950, y + 137), (970, y + 137), (960, y + 153)], fill=rgba(BLUE, 180))
    save_slide(img, "系统总体架构", "用分层结构说明系统如何组织。")


def make_screenshot_slide(title: str, subtitle: str, shot: Path, right_title: str, points: list[str], note: str, section: str) -> None:
    img = background()
    draw = header(img, title, subtitle, section)
    card(img, (90, 215, 1120, 910))
    paste_image(img, shot, (130, 255, 1080, 870), 8)
    card(img, (1195, 215, 1825, 910))
    draw.text((1250, 270), right_title, font=font(40, True), fill=rgba(PINK, 255))
    bullet_list(draw, 1250, 350, points, 500, font(26), accent=BLUE)
    save_slide(img, title, note)


def make_pet_module() -> None:
    img = background()
    draw = header(img, "模块一：桌宠表现与动作系统", "由动作帧、状态切换、位置控制和交互气泡共同组成。", "Module Pet")
    card(img, (95, 230, 905, 890))
    draw.text((145, 280), "核心职责", font=font(42, True), fill=rgba(PINK, 255))
    bullet_list(draw, 145, 360, [
        "加载 assets/polar_bear 下的真实动作帧。",
        "使用 QTimer 驱动动画更新，维持平滑播放。",
        "处理点击、双击、拖拽、贴边、隐藏、召回等交互。",
        "聊天气泡固定在熊右上侧，避免遮挡主体动作。",
        "通过动作锁和回待机缓冲减少瞬移、抖动和重影。",
    ], 680)
    card(img, (985, 230, 1825, 890))
    paste_image(img, SCREENSHOTS / "06_edge_wall_action_frames.png", (1035, 285, 1775, 605), 12)
    paste_image(img, ASSETS / "polar_bear" / "polar-bear-realistic-chromakey.png", (1090, 600, 1710, 925))
    save_slide(img, "模块一：桌宠表现与动作系统", "重点讲桌宠窗口、动画帧、状态机、事件处理和性能优化。")


def make_shop_module() -> None:
    img = background()
    draw = header(img, "模块四：背包商店与投喂系统", "投喂系统让桌宠状态和经济系统产生联系，增强长期使用动力。", "Module Backpack")
    card(img, (90, 215, 1030, 910))
    paste_image(img, SCREENSHOTS / "03_backpack_shop_page.png", (130, 255, 990, 870), 8)
    card(img, (1095, 215, 1825, 910))
    draw.text((1150, 270), "物品体系", font=font(40, True), fill=rgba(BLUE, 255))
    items = [
        ("鱼干", ASSETS / "shop/items/fish.png"),
        ("热牛奶", ASSETS / "shop/items/milk.png"),
        ("蓝莓蛋糕", ASSETS / "shop/items/berry_cake.png"),
        ("雪球", ASSETS / "shop/items/snowball.png"),
        ("围巾", ASSETS / "shop/items/scarf.png"),
        ("冰块", ASSETS / "shop/items/ice.png"),
    ]
    for i, (label, path) in enumerate(items):
        x, y = 1160 + (i % 3) * 200, 345 + (i // 3) * 185
        draw.rounded_rectangle((x, y, x + 155, y + 140), radius=26, fill=(239, 251, 255, 220), outline=rgba(LINE, 220), width=2)
        paste_image(img, path, (x + 10, y + 5, x + 145, y + 120), 3)
        tw, _ = text_size(draw, label, font(21, True))
        draw.text((x + (155 - tw) // 2, y + 118), label, font=font(21, True), fill=rgba(INK_2, 255))
    bullet_list(draw, 1150, 740, ["购买消耗金币，投喂影响饱食、心情和好感。", "每日任务与成长系统控制奖励难度，避免数值过快增长。"], 600, font(25), accent=PINK)
    save_slide(img, "模块四：背包商店与投喂系统", "说明物品、货币、库存、投喂效果和状态推荐之间的关系。")


def make_growth_module() -> None:
    img = background()
    draw = header(img, "模块五：成长等级、每日任务与 JSON 存档", "项目使用本地 JSON 作为轻量数据层，保存状态、课程、任务、背包和设置。", "Module Data")
    card(img, (95, 220, 890, 910))
    draw.text((145, 275), "成长机制", font=font(42, True), fill=rgba(PINK, 255))
    bullet_list(draw, 145, 360, [
        "等级：经验达到阈值后升级，解锁更强陪伴反馈。",
        "好感度：结合任务、聊天、投喂和日常行为，不再靠频繁触摸轻易刷满。",
        "金币：通过每日任务、课程提醒、互动奖励少量获得。",
        "每日任务：鼓励规律互动，例如查看课程、投喂、聊天、休息建议。",
    ], 650)
    card(img, (970, 220, 1825, 910))
    draw.text((1025, 275), "JSON 数据结构", font=font(42, True), fill=rgba(BLUE, 255))
    code = "data/\n  save.json       # 状态、背包、金币、好感、等级\n  config.json     # 大小、快捷键、AI Key、显示偏好\n  courses.json    # 导入后的课程表\n  reminders.json  # 提醒记录与通知状态\n\n核心思想：本地可读、方便导出、适合答辩检查。"
    draw.rounded_rectangle((1025, 355, 1770, 760), radius=30, fill=(18, 63, 87, 225))
    draw_text(draw, (1060, 390), code, font(25), (230, 252, 255, 255), width=680, line_gap=8)
    save_slide(img, "模块五：成长等级、每日任务与 JSON 存档", "强调项目是 JSON 存档，不是 SQLite。")


def make_code_slide(title: str, subtitle: str, code: str, points: list[str], note: str) -> None:
    img = background()
    draw = header(img, title, subtitle, "Code")
    card(img, (100, 210, 1820, 900))
    draw.rounded_rectangle((145, 280, 1245, 830), radius=28, fill=(18, 63, 87, 235))
    draw_text(draw, (180, 310), code, font(19), (231, 252, 255, 255), width=1020, line_gap=4)
    draw.rounded_rectangle((1300, 280, 1770, 830), radius=34, fill=(248, 254, 255, 220), outline=rgba(LINE, 220), width=2)
    draw.text((1345, 325), "讲解要点", font=font(36, True), fill=rgba(PINK, 255))
    bullet_list(draw, 1345, 405, points, 370, font(24), accent=BLUE)
    save_slide(img, title, note)


def make_state_slide() -> None:
    img = background()
    draw = header(img, "关键代码讲解：动作调度与防瞬移", "后期重点解决点击、走路、睡觉、贴边时的卡顿、抖动和瞬移。", "Code")
    card(img, (100, 220, 900, 900))
    draw.text((150, 275), "动作状态机", font=font(42, True), fill=rgba(PINK, 255))
    states = [("idle\n眨眼微动", 470, 375), ("walk\n左右行走", 260, 590), ("action\n跳跃/挥手", 680, 590), ("sleep\n入睡/休眠", 470, 760)]
    for label, x, y in states:
        draw.rounded_rectangle((x - 115, y - 55, x + 115, y + 55), radius=28, fill=(235, 251, 255, 230), outline=rgba(LINE, 230), width=3)
        draw_text(draw, (x - 90, y - 28), label, font(24, True), rgba(INK, 255), width=180, align="center")
    for x1, y1, x2, y2 in [(470, 430, 300, 545), (470, 430, 640, 545), (300, 645, 470, 720), (640, 645, 470, 720), (470, 705, 470, 430)]:
        draw.line((x1, y1, x2, y2), fill=rgba(BLUE, 180), width=5)
    card(img, (970, 220, 1825, 900))
    draw.text((1025, 275), "优化策略", font=font(42, True), fill=rgba(BLUE, 255))
    bullet_list(draw, 1025, 360, [
        "动作开始前预加载帧，避免第一次点击时卡住。",
        "动作结束先进入缓冲帧，再回到 idle。",
        "移动位置由逻辑增量控制，避免最后一帧瞬移。",
        "聊天、选择菜单、动作按钮使用事件锁，避免双触发。",
        "贴边和角落休眠分别处理，不混成隐藏状态。",
    ], 680, font(27), accent=PINK)
    save_slide(img, "关键代码讲解：动作调度与防瞬移", "结合调试过的瞬移、重影、抖动、左走卡顿等问题讲迭代过程。")


def make_deploy() -> None:
    img = background()
    draw = header(img, "部署方式与数据文件设计", "项目可通过 Python 直接运行，也可使用 Windows 启动脚本创建桌面入口。", "Deployment")
    card(img, (100, 220, 850, 900))
    draw.text((150, 275), "部署图", font=font(42, True), fill=rgba(PINK, 255))
    for label, cy in [("Windows 桌面", 375), ("Python 运行环境", 535), ("PySide6 应用", 695), ("本地 data / assets", 835)]:
        draw.rounded_rectangle((255, cy - 45, 695, cy + 45), radius=24, fill=(237, 251, 255, 230), outline=rgba(LINE, 230), width=3)
        tw, _ = text_size(draw, label, font(26, True))
        draw.text((475 - tw // 2, cy - 18), label, font=font(26, True), fill=rgba(INK, 255))
    for y in [420, 580, 740]:
        draw.line((475, y, 475, y + 65), fill=rgba(BLUE, 180), width=5)
        draw.polygon([(463, y + 65), (487, y + 65), (475, y + 84)], fill=rgba(BLUE, 180))
    card(img, (930, 220, 1825, 900))
    draw.text((985, 275), "交付内容", font=font(42, True), fill=rgba(BLUE, 255))
    bullet_list(draw, 985, 360, [
        "系统源代码：main.py、src、tools、assets、docs。",
        "配置文件：requirements.txt、launch_polar_bear.bat/vbs。",
        "数据说明：JSON 存档结构说明、初始化脚本。",
        "界面截图：控制台、OCR、背包、聊天、设置、贴边动作。",
        "文档：系统设计文档、五大模块讲解、构建阶段交付材料。",
    ], 720, font(27), accent=PINK)
    save_slide(img, "部署方式与数据文件设计", "用于说明系统如何运行、文件如何组织、答辩提交材料有哪些。")


def make_testing() -> None:
    img = background()
    draw = header(img, "测试、问题修复与优化成果", "项目经历了大量交互细节修复，重点提升流畅度、完整显示和可用性。", "Testing")
    items = [
        ("动画流畅度", "预加载帧、缓存缩放、减少启动卡顿、动作结束缓冲"),
        ("交互稳定性", "修复点击后瞬移、双击重复触发、菜单无法取消等问题"),
        ("显示完整性", "聊天气泡时长增加、右上侧定位、避免遮挡熊身体"),
        ("贴边/休眠", "隐藏与角落休眠分离，右下角圆点可移动并支持快捷键"),
        ("课程可用性", "OCR + 文本导入双路径，导入后展示可读课程表"),
        ("界面体验", "背包素材升级、玻璃拟态控制面板、成长侧栏独立展示"),
    ]
    for i, (name, desc) in enumerate(items):
        x, y = 115 + (i % 2) * 875, 230 + (i // 2) * 220
        card(img, (x, y, x + 780, y + 165), radius=34)
        draw.text((x + 42, y + 28), name, font=font(34, True), fill=rgba(PINK if i % 2 == 0 else BLUE, 255))
        draw_text(draw, (x + 42, y + 86), desc, font(25), rgba(INK_2, 255), width=690, line_gap=7)
    save_slide(img, "测试、问题修复与优化成果", "讲项目迭代：卡顿、穿帮、遮挡、瞬移、课程导入、UI 优化。")


def make_summary() -> None:
    img = background()
    draw = header(img, "总结与展望", "最终项目从“会动的图片”升级为“有状态、有任务、有提醒、有对话”的桌面宠物系统。", "Summary")
    card(img, (110, 230, 1040, 870), radius=46)
    draw.text((165, 290), "已完成成果", font=font(44, True), fill=rgba(PINK, 255))
    bullet_list(draw, 165, 375, [
        "完成北极熊桌宠主体、控制面板和多功能页面。",
        "完成课程提醒、OCR 课表识别、聊天、背包投喂、成长等级。",
        "完成本地 JSON 存档、快捷键、启动器、截图和文档交付。",
        "围绕流畅度、显示完整性和交互体验进行了多轮优化。",
    ], 760, font(28))
    card(img, (1110, 230, 1810, 870), radius=46)
    draw.text((1165, 290), "后续展望", font=font(44, True), fill=rgba(BLUE, 255))
    bullet_list(draw, 1165, 375, [
        "打包为 exe 安装包，降低运行门槛。",
        "接入更强 OCR 或视觉模型，提高课表照片识别准确率。",
        "增加更多高质量动作和装扮系统。",
        "增加云同步和更多主动陪伴策略。",
    ], 560, font(28), accent=BLUE)
    paste_image(img, ASSETS / "polar_bear" / "polar-bear-premium-chromakey.png", (1370, 575, 1820, 970))
    save_slide(img, "总结与展望", "结尾强调项目完整性和后续可拓展性。")


def write_notes(path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("# 北极熊桌宠项目答辩讲稿提纲\n\n")
        f.write("> 与 PPT 页码一一对应，可按“作用 -> 演示 -> 代码逻辑”的顺序讲。\n\n")
        for idx, (_, title, note) in enumerate(slides, 1):
            f.write(f"## {idx:02d}. {title}\n\n{note}\n\n")


def rels_xml(rels: list[tuple[str, str, str]]) -> str:
    rows = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for rid, typ, target in rels:
        rows.append(f'<Relationship Id="{rid}" Type="{typ}" Target="{escape(target)}"/>')
    rows.append("</Relationships>")
    return "".join(rows)


def content_types(n: int) -> str:
    rows = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Default Extension="png" ContentType="image/png"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
    ]
    rows += [f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1, n + 1)]
    rows.append("</Types>")
    return "".join(rows)


def presentation_xml(n: int) -> str:
    sld_ids = "".join(f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, n + 1))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
<p:sldIdLst>{sld_ids}</p:sldIdLst><p:sldSz cx="{EMU_W}" cy="{EMU_H}" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''


def slide_xml(i: int) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{EMU_W}" cy="{EMU_H}"/><a:chOff x="0" y="0"/><a:chExt cx="{EMU_W}" cy="{EMU_H}"/></a:xfrm></p:grpSpPr>
<p:pic><p:nvPicPr><p:cNvPr id="2" name="slide_{i:02d}.png"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{EMU_W}" cy="{EMU_H}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>
</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'''


def master_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>'''


def layout_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'''


def theme_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="ArcticBear"><a:themeElements><a:clrScheme name="Arctic"><a:dk1><a:srgbClr val="1E526E"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="123C52"/></a:dk2><a:lt2><a:srgbClr val="EFFBFF"/></a:lt2><a:accent1><a:srgbClr val="5CC6E1"/></a:accent1><a:accent2><a:srgbClr val="FF84B8"/></a:accent2><a:accent3><a:srgbClr val="81E1D8"/></a:accent3><a:accent4><a:srgbClr val="FFCB60"/></a:accent4><a:accent5><a:srgbClr val="B6AAFF"/></a:accent5><a:accent6><a:srgbClr val="77D2B0"/></a:accent6><a:hlink><a:srgbClr val="5CC6E1"/></a:hlink><a:folHlink><a:srgbClr val="FF84B8"/></a:folHlink></a:clrScheme><a:fontScheme name="ArcticFonts"><a:majorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface="Microsoft YaHei"/></a:majorFont><a:minorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface="Microsoft YaHei"/></a:minorFont></a:fontScheme><a:fmtScheme name="ArcticFmt"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>'''


def build_pptx(pptx_path: Path) -> None:
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>北极熊桌宠项目期末答辩PPT</dc:title><dc:creator>Codex</dc:creator><cp:lastModifiedBy>Codex</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>'''
    app = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Codex PPT Renderer</Application><PresentationFormat>On-screen Show (16:9)</PresentationFormat><Slides>{len(slides)}</Slides></Properties>'''
    with zipfile.ZipFile(pptx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types(len(slides)))
        zf.writestr("_rels/.rels", rels_xml([
            ("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument", "ppt/presentation.xml"),
            ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
            ("rId3", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties", "docProps/app.xml"),
        ]))
        zf.writestr("docProps/core.xml", core)
        zf.writestr("docProps/app.xml", app)
        zf.writestr("ppt/presentation.xml", presentation_xml(len(slides)))
        pres_rels = [("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster", "slideMasters/slideMaster1.xml")]
        pres_rels.extend((f"rId{i + 1}", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide", f"slides/slide{i}.xml") for i in range(1, len(slides) + 1))
        zf.writestr("ppt/_rels/presentation.xml.rels", rels_xml(pres_rels))
        zf.writestr("ppt/slideMasters/slideMaster1.xml", master_xml())
        zf.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", rels_xml([
            ("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout", "../slideLayouts/slideLayout1.xml"),
            ("rId2", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme", "../theme/theme1.xml"),
        ]))
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", layout_xml())
        zf.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", rels_xml([]))
        zf.writestr("ppt/theme/theme1.xml", theme_xml())
        for i, (slide_image, _, _) in enumerate(slides, 1):
            zf.writestr(f"ppt/slides/slide{i}.xml", slide_xml(i))
            zf.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", rels_xml([
                ("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image", f"../media/slide_{i:02d}.png"),
                ("rId2", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout", "../slideLayouts/slideLayout1.xml"),
            ]))
            zf.write(slide_image, f"ppt/media/slide_{i:02d}.png")
    with zipfile.ZipFile(pptx_path) as zf:
        xml_slides = [name for name in zf.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
        if len(xml_slides) != len(slides):
            raise RuntimeError(f"slide count mismatch: {len(xml_slides)} != {len(slides)}")


def main() -> None:
    global PPT_IMAGES
    OUT_DIR.mkdir(exist_ok=True)
    BUILD_DIR.mkdir(exist_ok=True)
    PPT_IMAGES = generate_ui_reference_images(ROOT, BUILD_DIR)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pptx_path = OUT_DIR / f"北极熊桌宠项目_期末答辩PPT_{stamp}.pptx"
    notes_path = OUT_DIR / f"北极熊桌宠项目_答辩讲稿提纲_{stamp}.md"

    make_cover()
    make_two_column(
        "选题背景与项目目标",
        "从“有趣的桌宠”扩展为“陪伴 + 提醒 + 互动 + 成长”的轻量化桌面伙伴。",
        "为什么做这个项目",
        ["普通课表提醒工具缺少陪伴感，用户容易忽略通知。", "传统桌宠多数只做图片移动，缺少动作状态和长期成长反馈。", "项目希望把课程、日常互动和桌面宠物行为整合成一个完整体验。"],
        "项目目标",
        ["让北极熊在桌面上能待机、行走、跳跃、睡觉、贴边隐藏。", "支持课程表导入、下一节课提醒和桌宠气泡提示。", "加入背包、金币、好感度、等级、每日任务等可持续玩法。", "对接大模型，让桌宠具备自然聊天和主动陪伴能力。"],
        "先讲项目不是单一动画，而是一套学习提醒与陪伴体验系统。",
    )
    make_feature_grid()
    make_tech()
    make_structure()
    make_architecture()
    make_pet_module()
    make_screenshot_slide("模块二：控制面板与功能导航", "控制面板是桌宠系统的管理中心。", PPT_IMAGES["dashboard"], "界面特点", ["左侧导航栏独立划分功能入口。", "主区域使用卡片承载状态和操作。", "采用冰蓝、雪白、浅粉的玻璃拟态风格。", "增加滚动区域，解决内容显示不完整问题。", "桌宠与面板位置解耦，避免打开面板时瞬移。"], "展示界面成果，并说明缩放、遮挡、滚动、面板美化等优化。", "Module UI")
    make_screenshot_slide("模块三：课程提醒与 OCR 识别", "把课表照片或识别文字解析成结构化课程，再计算下一节课并提醒用户。", PPT_IMAGES["course"], "识别流程", ["选择课表图片。", "OCR 提取文字，或手动粘贴识别结果。", "解析星期、节次、课程名、教师和地点。", "写入本地 JSON 课程表。", "根据当前时间计算下一节课并通知。"], "讲图片识别和文字导入双通道，说明课程最终会导入本地课表。", "Module Course")
    make_shop_module()
    make_screenshot_slide("模块五：成长等级与任务系统", "等级、经验、好感上限、每日好感额度和任务奖励独立管理。", PPT_IMAGES["growth"], "成长机制", ["等级经验达到阈值后升级，解锁更强陪伴反馈。", "普通触摸不直接增加好感，好感受等级和每日额度限制。", "金币主要来自每日任务、课程提醒和少量升级奖励。", "成长侧栏独立展示，让答辩时更容易说明数值机制。"], "展示成长等级中心，强调奖励机制比普通触摸刷好感更困难。", "Module Data")
    make_screenshot_slide("AI 大模型聊天互动", "桌宠不仅能执行固定动作，还能通过大模型进行自然语言陪伴。", PPT_IMAGES["chat"], "对接能力", ["支持 DeepSeek、ChatGPT、智谱 GLM 等模型配置。", "系统设置页可填写 API Key、模型名和接口地址。", "聊天页使用顺序气泡展示，修复倒序和遮挡问题。", "桌宠头顶气泡用于短反馈，控制面板聊天窗用于完整对话。"], "讲清楚大模型接入方式，以及短气泡和完整聊天窗口的区别。", "AI Chat")
    make_code_slide(
        "关键代码讲解：桌宠窗口初始化",
        "这段代码体现透明窗口、资源路径、动作状态和定时器驱动。",
        'class PolarBearPetWindow(QWidget):\n    interaction_requested = Signal(str)\n\n    def __init__(self):\n        super().__init__()\n        self.setWindowTitle("PolarBear Pet")\n        self.setWindowFlags(Qt.FramelessWindowHint |\n                            Qt.WindowStaysOnTopHint | Qt.Tool)\n        self.setAttribute(Qt.WA_TranslucentBackground)\n\n        root = Path(__file__).resolve().parents[2]\n        self.asset_root = root / "assets" / "polar_bear"\n        self.role_root = self.asset_root / "role" / "PolarBear"\n        self.real_action_root = self.asset_root / "real_actions"\n\n        self._scale = self._load_pet_scale()\n        self._configure_geometry()\n        self._actions = {}\n        self._action_name = "idle"\n        self._frame_index = 0\n\n        self._load_actions()\n        self._timer = QTimer(self)\n        self._timer.timeout.connect(self._tick)\n        self._timer.start(16)',
        ["无边框 + 置顶 + 透明背景，形成桌宠效果。", "资源路径统一从 assets/polar_bear 加载。", "动作名、帧下标、动作字典共同构成动画状态。", "16ms 定时器约等于 60FPS，是流畅播放基础。"],
        "答辩时逐行讲窗口属性、资源路径、状态变量、定时器。",
    )
    make_state_slide()
    make_code_slide(
        "关键代码讲解：课程识别与导入逻辑",
        "OCR 结果只是原始文本，真正可用的课程表需要二次解析和结构化。",
        '识别输入：课表截图 / 手动粘贴文字\n\n处理流程：\n1. 清洗空格、换行、全角符号和节次格式\n2. 根据星期列、时间段、课程块提取候选课程\n3. 识别课程名、教师、周次、节次、地点\n4. 生成 CourseItem 并写入 JSON 存档\n5. 按当前日期和时间计算“下一节课”\n\n示例字段：\n{\n  "weekday": 4,\n  "start_time": "08:20",\n  "end_time": "10:00",\n  "name": "计算机网络",\n  "location": "2438云平台综合实训室",\n  "weeks": "2-18周"\n}',
        ["OCR 不是最终结果，只是输入来源。", "课程提醒真正依赖结构化字段。", "识别失败时保留手动粘贴文本入口，提高可用性。", "导入后能在“我的课表”中查看。"],
        "回答“课表照片如何变成提醒”的实现逻辑。",
    )
    make_deploy()
    make_testing()
    make_summary()

    write_notes(notes_path)
    build_pptx(pptx_path)
    print(f"PPTX_PATH={pptx_path}")
    print(f"NOTES_PATH={notes_path}")
    print(f"SLIDES={len(slides)}")
    print(f"SIZE_MB={pptx_path.stat().st_size / 1024 / 1024:.2f}")


if __name__ == "__main__":
    main()
