from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "shop" / "items"
CANVAS = 768


def hex_rgba(value, alpha=255):
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4)) + (alpha,)


def transparent(size=(CANVAS, CANVAS)):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def gradient(size, start, end, vertical=True):
    image = Image.new("RGBA", size)
    pixels = image.load()
    span = max(1, (size[1] if vertical else size[0]) - 1)
    for y in range(size[1]):
        for x in range(size[0]):
            position = y if vertical else x
            ratio = position / span
            color = tuple(round(start[i] * (1 - ratio) + end[i] * ratio) for i in range(4))
            pixels[x, y] = color
    return image


def add_shadow(base, layer, offset=(0, 28), blur=24, opacity=0.12):
    # The icon builders draw a compact contact shadow themselves. Avoid a
    # full silhouette shadow here, otherwise transparent cutouts look like
    # they still have a background card behind them.
    base.alpha_composite(layer)


def rounded_gradient_layer(size, radius, top, bottom, outline=None, outline_width=0):
    layer = transparent(size)
    fill = gradient(size, top, bottom)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    layer.alpha_composite(fill)
    layer.putalpha(mask)
    if outline and outline_width:
        draw = ImageDraw.Draw(layer)
        draw.rounded_rectangle(
            (outline_width // 2, outline_width // 2, size[0] - outline_width // 2 - 1, size[1] - outline_width // 2 - 1),
            radius=radius,
            outline=outline,
            width=outline_width,
        )
    return layer


def draw_sparkles(draw, points, color=(255, 255, 255, 170)):
    for x, y, radius in points:
        draw.line((x - radius, y, x + radius, y), fill=color, width=max(2, radius // 4))
        draw.line((x, y - radius, x, y + radius), fill=color, width=max(2, radius // 4))


def trim_alpha(image):
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        return image
    padding = 18
    bbox = (
        max(0, bbox[0] - padding),
        max(0, bbox[1] - padding),
        min(image.width, bbox[2] + padding),
        min(image.height, bbox[3] + padding),
    )
    return image.crop(bbox)


def save_icon(name, image):
    image = trim_alpha(image)
    image = ImageEnhance.Sharpness(image).enhance(1.08)
    image.save(OUT_DIR / f"{name}.png")


def paste_rotated(target, layer, center, angle):
    rotated = layer.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    target.alpha_composite(rotated, (round(center[0] - rotated.width / 2), round(center[1] - rotated.height / 2)))


def make_fillet(width=430, height=116, edge="#d99656", center="#fff2df"):
    layer = transparent((width + 60, height + 60))
    body = Image.new("L", layer.size, 0)
    mask = ImageDraw.Draw(body)
    top = [
        (34, 36),
        (86, 24),
        (148, 30),
        (214, 20),
        (286, 27),
        (356, 22),
        (width + 18, 38),
        (width + 42, 58),
    ]
    bottom = [
        (width + 38, height + 8),
        (width - 16, height + 28),
        (width - 90, height + 18),
        (width - 170, height + 30),
        (width - 256, height + 19),
        (width - 330, height + 27),
        (62, height + 20),
        (24, height - 2),
    ]
    mask.polygon(top + bottom, fill=255)
    body = body.filter(ImageFilter.GaussianBlur(0.8))

    fill = gradient(layer.size, hex_rgba(center), hex_rgba("#efbd82"))
    fill.putalpha(body)
    layer.alpha_composite(fill)
    draw = ImageDraw.Draw(layer)
    draw.line(top + bottom + [top[0]], fill=hex_rgba(edge, 235), width=5, joint="curve")
    for index, x in enumerate(range(76, width - 10, 44)):
        shade = hex_rgba("#c98248", 92 if index % 2 else 64)
        draw.line((x, 42, x - 20, height + 10), fill=shade, width=5)
        draw.line((x + 18, 50, x - 6, height - 4), fill=hex_rgba("#fffaf0", 150), width=4)
    draw.line((70, 46, width - 8, 52), fill=hex_rgba("#fffaf0", 170), width=5)
    draw.line((72, height - 6, width - 26, height + 2), fill=hex_rgba("#b96f3f", 70), width=4)
    return layer


def make_fish():
    icon = transparent()
    draw = ImageDraw.Draw(icon)
    draw.ellipse((142, 514, 632, 646), fill=hex_rgba("#7fcbe0", 62))
    draw.ellipse((170, 530, 608, 620), fill=hex_rgba("#ffffff", 135), outline=hex_rgba("#bdebf6", 150), width=3)

    bundle = transparent()
    for center, angle, size in [
        ((368, 286), -11, 1.0),
        ((330, 334), -16, 0.95),
        ((408, 354), -7, 0.9),
        ((292, 386), -20, 0.86),
    ]:
        fillet = make_fillet(round(430 * size), round(116 * size))
        paste_rotated(bundle, fillet, center, angle)
    ribbon = transparent()
    ribbon_draw = ImageDraw.Draw(ribbon)
    ribbon_draw.rounded_rectangle((246, 344, 520, 394), radius=24, fill=hex_rgba("#7bd5e5", 232))
    ribbon_draw.rounded_rectangle((282, 352, 486, 382), radius=15, fill=hex_rgba("#eaffff", 95))
    ribbon_draw.ellipse((350, 326, 424, 408), fill=hex_rgba("#65c7df", 255), outline=hex_rgba("#ffffff", 180), width=5)
    ribbon_draw.polygon([(360, 362), (304, 310), (304, 398)], fill=hex_rgba("#9de8ef", 230))
    ribbon_draw.polygon([(414, 362), (476, 310), (476, 398)], fill=hex_rgba("#9de8ef", 230))
    bundle.alpha_composite(ribbon)
    add_shadow(icon, bundle, offset=(0, 18), blur=26, opacity=0.18)
    draw_sparkles(draw, [(195, 238, 16), (560, 226, 14), (582, 470, 10)])
    return icon


def make_milk():
    icon = transparent()
    layer = transparent()
    draw = ImageDraw.Draw(layer)
    draw.ellipse((228, 560, 560, 648), fill=hex_rgba("#79c8dd", 70))
    bottle = rounded_gradient_layer((276, 410), 54, hex_rgba("#ffffff"), hex_rgba("#dff5ff"), hex_rgba("#8bd6ee", 180), 4)
    bottle.alpha_composite(rounded_gradient_layer((212, 118), 38, hex_rgba("#eaf9ff"), hex_rgba("#93d4f0")), (32, 42))
    bd = ImageDraw.Draw(bottle)
    bd.rounded_rectangle((48, 122, 228, 316), radius=24, fill=hex_rgba("#ffffff", 205))
    bd.arc((50, 86, 226, 170), 180, 360, fill=hex_rgba("#ffffff", 190), width=6)
    bd.rounded_rectangle((96, 6, 182, 70), radius=20, fill=hex_rgba("#ecf9ff"), outline=hex_rgba("#95d8ef", 180), width=4)
    bd.rounded_rectangle((76, 212, 204, 260), radius=24, fill=hex_rgba("#8adcee", 185))
    bd.ellipse((90, 256, 122, 288), fill=hex_rgba("#263d55", 230))
    bd.ellipse((154, 256, 186, 288), fill=hex_rgba("#263d55", 230))
    bd.ellipse((98, 260, 108, 270), fill=hex_rgba("#ffffff", 230))
    bd.ellipse((162, 260, 172, 270), fill=hex_rgba("#ffffff", 230))
    bd.arc((116, 268, 160, 304), 18, 160, fill=hex_rgba("#e37f9e", 255), width=4)
    bd.line((230, 28, 254, -50), fill=hex_rgba("#6cc8e6", 255), width=16)
    bd.line((230, 28, 254, -50), fill=hex_rgba("#ffffff", 180), width=5)
    layer.alpha_composite(bottle, (246, 118))
    add_shadow(icon, layer, offset=(0, 22), blur=24, opacity=0.2)
    return icon


def make_berry_cake():
    icon = transparent()
    layer = transparent()
    draw = ImageDraw.Draw(layer)
    draw.ellipse((120, 552, 652, 672), fill=hex_rgba("#72c5df", 58))
    draw.ellipse((156, 560, 620, 640), fill=hex_rgba("#fffaff", 185), outline=hex_rgba("#c8edf8", 180), width=4)
    draw.rounded_rectangle((190, 314, 590, 552), radius=44, fill=hex_rgba("#f9eaf4"), outline=hex_rgba("#d9b8ee", 190), width=4)
    draw.rounded_rectangle((190, 456, 590, 552), radius=38, fill=hex_rgba("#e0b472"))
    draw.rectangle((194, 412, 586, 464), fill=hex_rgba("#fff7ef"))
    draw.rectangle((194, 468, 586, 500), fill=hex_rgba("#82387e", 185))
    draw.ellipse((172, 248, 608, 392), fill=hex_rgba("#8041ba"), outline=hex_rgba("#f5dcff", 150), width=4)
    for x in range(204, 564, 58):
        draw.ellipse((x, 342, x + 70, 424), fill=hex_rgba("#8e3bc7"))
    for x, y in [(250, 244), (338, 220), (440, 236), (520, 270)]:
        draw.ellipse((x, y, x + 72, y + 72), fill=hex_rgba("#1f3f8e"), outline=hex_rgba("#d7e9ff", 180), width=4)
        draw.ellipse((x + 12, y + 10, x + 32, y + 30), fill=hex_rgba("#ffffff", 170))
    for x in [318, 372, 426]:
        draw.ellipse((x, 210, x + 70, 306), fill=hex_rgba("#fff4f1"))
        draw.arc((x, 210, x + 70, 306), 210, 40, fill=hex_rgba("#d3b0df", 120), width=4)
    draw.pieslice((438, 188, 560, 300), 115, 270, fill=hex_rgba("#58a85d"))
    draw.line((470, 244, 540, 206), fill=hex_rgba("#d7ffcf", 190), width=4)
    add_shadow(icon, layer, offset=(0, 18), blur=26, opacity=0.18)
    return icon


def make_snowball():
    icon = transparent()
    layer = transparent()
    draw = ImageDraw.Draw(layer)
    draw.ellipse((176, 522, 606, 636), fill=hex_rgba("#82cde2", 60))
    draw.ellipse((190, 250, 574, 600), fill=hex_rgba("#ffffff"), outline=hex_rgba("#bfe8f6", 220), width=7)
    for box in [(220, 286, 320, 390), (370, 280, 500, 410), (250, 430, 360, 548), (420, 420, 520, 540)]:
        draw.ellipse(box, fill=hex_rgba("#e7f7ff", 150))
    draw.ellipse((284, 388, 326, 430), fill=hex_rgba("#263d55"))
    draw.ellipse((440, 388, 482, 430), fill=hex_rgba("#263d55"))
    draw.ellipse((296, 398, 308, 410), fill=hex_rgba("#ffffff"))
    draw.ellipse((452, 398, 464, 410), fill=hex_rgba("#ffffff"))
    draw.arc((344, 408, 424, 474), 20, 160, fill=hex_rgba("#e98aad"), width=6)
    draw.rounded_rectangle((230, 188, 540, 300), radius=52, fill=hex_rgba("#7dc9ef"), outline=hex_rgba("#effcff", 170), width=6)
    draw.ellipse((250, 120, 508, 248), fill=hex_rgba("#9bdaf5"), outline=hex_rgba("#ffffff", 160), width=5)
    draw.ellipse((474, 84, 570, 176), fill=hex_rgba("#f7fbff"), outline=hex_rgba("#b7e5f5"), width=5)
    add_shadow(icon, layer, offset=(0, 22), blur=24, opacity=0.18)
    return icon


def make_scarf():
    icon = transparent()
    layer = transparent()
    draw = ImageDraw.Draw(layer)
    draw.ellipse((130, 536, 646, 650), fill=hex_rgba("#7fcbe0", 58))
    draw.rounded_rectangle((150, 220, 616, 390), radius=84, fill=hex_rgba("#9bcdf8"), outline=hex_rgba("#ffffff", 150), width=6)
    draw.rounded_rectangle((186, 306, 350, 640), radius=44, fill=hex_rgba("#82b8ee"), outline=hex_rgba("#ffffff", 110), width=4)
    draw.rounded_rectangle((404, 300, 560, 624), radius=44, fill=hex_rgba("#b7d9ff"), outline=hex_rgba("#ffffff", 110), width=4)
    draw.ellipse((274, 174, 530, 404), fill=hex_rgba("#74b4ef"), outline=hex_rgba("#effcff", 150), width=6)
    draw.ellipse((326, 224, 500, 342), fill=hex_rgba("#e7f8ff", 210))
    for x in range(208, 548, 42):
        draw.line((x, 230, x + 32, 382), fill=hex_rgba("#ffffff", 92), width=5)
    for x in range(212, 332, 28):
        draw.line((x, 586, x, 666), fill=hex_rgba("#7baeed", 230), width=8)
    for x in range(430, 548, 28):
        draw.line((x, 574, x, 650), fill=hex_rgba("#9fc9ff", 230), width=8)
    draw_sparkles(draw, [(236, 352, 18), (492, 368, 14), (320, 500, 12)], color=hex_rgba("#ffffff", 180))
    add_shadow(icon, layer, offset=(0, 20), blur=24, opacity=0.18)
    return icon


def make_ice():
    icon = transparent()
    layer = transparent()
    draw = ImageDraw.Draw(layer)
    draw.ellipse((150, 542, 638, 662), fill=hex_rgba("#6bc3df", 72))
    front = [(194, 272), (370, 198), (574, 264), (602, 500), (416, 612), (202, 520)]
    side = [(574, 264), (644, 382), (602, 500)]
    top = [(194, 272), (370, 198), (574, 264), (398, 338)]
    draw.polygon(front, fill=hex_rgba("#9be9ff", 176), outline=hex_rgba("#ffffff", 170))
    draw.polygon(side, fill=hex_rgba("#6ecfec", 132), outline=hex_rgba("#ffffff", 140))
    draw.polygon(top, fill=hex_rgba("#d7fbff", 190), outline=hex_rgba("#ffffff", 180))
    draw.line((398, 338, 416, 612), fill=hex_rgba("#ffffff", 120), width=5)
    draw.line((246, 294, 394, 238, 538, 284), fill=hex_rgba("#ffffff", 170), width=7)
    draw.arc((250, 344, 508, 520), 206, 340, fill=hex_rgba("#ffffff", 95), width=8)
    draw_sparkles(draw, [(282, 360, 14), (518, 424, 18), (438, 260, 12)], color=hex_rgba("#ffffff", 210))
    add_shadow(icon, layer, offset=(0, 24), blur=28, opacity=0.2)
    return icon


BUILDERS = {
    "fish": make_fish,
    "milk": make_milk,
    "berry_cake": make_berry_cake,
    "snowball": make_snowball,
    "scarf": make_scarf,
    "ice": make_ice,
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, builder in BUILDERS.items():
        save_icon(name, builder())
    print(f"generated {len(BUILDERS)} polished 2.5D shop item assets in {OUT_DIR}")


if __name__ == "__main__":
    main()
