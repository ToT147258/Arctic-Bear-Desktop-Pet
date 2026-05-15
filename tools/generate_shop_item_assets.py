from pathlib import Path
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "shop" / "items"
SIZE = 1024
SCALE = 3


def px(value):
    return int(round(value * SCALE))


def box(values):
    return tuple(px(value) for value in values)


def points(values):
    return [(px(x), px(y)) for x, y in values]


def color(values):
    if len(values) == 4:
        return values
    return (*values, 255)


def font(size, bold=False):
    candidates = []
    if bold:
        candidates.extend(
            [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/msyhbd.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/msyh.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, px(size))
    return ImageFont.load_default()


def new_layer():
    return Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))


def add_canvas_shadow(canvas, alpha, offset=(0, 34), blur=28, opacity=0.34):
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_alpha = alpha.filter(ImageFilter.GaussianBlur(px(blur))).point(lambda value: int(value * opacity))
    shadow.putalpha(shadow_alpha)
    canvas.alpha_composite(shadow, (px(offset[0]), px(offset[1])))


def soft_highlight(draw, xy, fill=(255, 255, 255, 90), width=5):
    draw.arc(box(xy), 205, 330, fill=color(fill), width=px(width))


def draw_face(draw, center, scale=1.0, smile=True, wink=False):
    cx, cy = center
    eye_r = 17 * scale
    gap = 48 * scale
    if wink:
        draw.arc(box((cx - gap - 16 * scale, cy - 8 * scale, cx - gap + 20 * scale, cy + 14 * scale)), 190, 345, fill=(41, 39, 58, 255), width=px(5 * scale))
    else:
        for ex in (cx - gap, cx + gap):
            draw.ellipse(box((ex - eye_r, cy - eye_r, ex + eye_r, cy + eye_r)), fill=(38, 35, 52, 255))
            draw.ellipse(box((ex - eye_r * 0.45, cy - eye_r * 0.62, ex + eye_r * 0.05, cy - eye_r * 0.1)), fill=(255, 255, 255, 230))
            draw.ellipse(box((ex + eye_r * 0.3, cy + eye_r * 0.2, ex + eye_r * 0.55, cy + eye_r * 0.45)), fill=(255, 255, 255, 170))
    blush = (255, 143, 158, 140)
    draw.ellipse(box((cx - 92 * scale, cy + 16 * scale, cx - 48 * scale, cy + 43 * scale)), fill=blush)
    draw.ellipse(box((cx + 48 * scale, cy + 16 * scale, cx + 92 * scale, cy + 43 * scale)), fill=blush)
    if smile:
        draw.arc(box((cx - 22 * scale, cy + 5 * scale, cx + 4 * scale, cy + 36 * scale)), 10, 112, fill=(70, 35, 55, 255), width=px(4 * scale))
        draw.arc(box((cx - 4 * scale, cy + 5 * scale, cx + 22 * scale, cy + 36 * scale)), 68, 170, fill=(70, 35, 55, 255), width=px(4 * scale))
    else:
        draw.arc(box((cx - 20 * scale, cy + 10 * scale, cx + 20 * scale, cy + 44 * scale)), 200, 340, fill=(70, 35, 55, 255), width=px(4 * scale))


def paste_rotated(canvas, item, angle, center):
    item = item.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    item = trim(item)
    x = px(center[0]) - item.width // 2
    y = px(center[1]) - item.height // 2
    canvas.alpha_composite(item, (x, y))


def trim(image):
    bbox = image.getbbox()
    return image.crop(bbox) if bbox else image


def finish(item):
    item = trim(item)
    canvas = new_layer()
    alpha = item.getchannel("A")
    shadow = Image.new("RGBA", item.size, (0, 0, 0, 0))
    shadow_alpha = alpha.filter(ImageFilter.GaussianBlur(px(34))).point(lambda value: int(value * 0.34))
    shadow.putalpha(shadow_alpha)
    x = (canvas.width - item.width) // 2
    y = (canvas.height - item.height) // 2
    canvas.alpha_composite(shadow, (x, y + px(42)))
    canvas.alpha_composite(item, (x, y))
    output = canvas.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    bbox = output.getchannel("A").getbbox()
    if not bbox:
        return output
    padding = 34
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(output.width, bbox[2] + padding)
    bottom = min(output.height, bbox[3] + padding)
    return output.crop((left, top, right, bottom))


def draw_fish():
    layer = new_layer()
    item = Image.new("RGBA", (px(430), px(780)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(item)
    rng = random.Random(5)

    outline = [(204, 40), (286, 80), (330, 156), (310, 276), (282, 430), (224, 638), (128, 716), (82, 666), (122, 486), (152, 300), (166, 132)]
    body = [(208, 70), (276, 104), (302, 170), (284, 282), (256, 430), (200, 606), (132, 668), (104, 636), (142, 480), (172, 300), (184, 142)]
    inner = [(212, 102), (260, 134), (276, 192), (258, 300), (230, 430), (184, 580), (138, 624), (124, 606), (160, 456), (186, 302), (198, 156)]

    draw.polygon(points(outline), fill=(161, 95, 48, 255))
    draw.polygon(points(body), fill=(235, 184, 128, 255))
    draw.polygon(points(inner), fill=(255, 232, 198, 255))
    draw.line(points([(204, 56), (282, 96), (322, 158)]), fill=(248, 215, 171, 230), width=px(11), joint="curve")
    draw.line(points([(108, 638), (140, 678), (202, 610)]), fill=(140, 80, 42, 180), width=px(8), joint="curve")
    draw.line(points([(188, 96), (160, 270), (134, 466), (104, 638)]), fill=(129, 74, 38, 150), width=px(9))
    draw.line(points([(282, 122), (260, 286), (232, 438), (190, 606)]), fill=(171, 100, 50, 150), width=px(7))

    for index in range(34):
        y = 116 + index * 15 + rng.randint(-4, 5)
        x0 = 178 + rng.randint(-8, 8)
        x1 = 266 + rng.randint(-15, 8) - index * 1.5
        if y > 600:
            x1 -= 28
        if x1 > x0 + 10:
            draw.arc(box((x0, y, x1, y + 24)), 190, 340, fill=(201, 139, 86, 80), width=px(2))

    for y in (142, 188, 238, 292, 350, 410, 472, 536):
        draw.line(points([(204, y), (258, y + 15)]), fill=(255, 247, 226, 160), width=px(3))

    draw_face(draw, (182, 536), scale=0.72)
    draw.ellipse(box((168, 518, 178, 528)), fill=(255, 255, 255, 255))
    draw.ellipse(box((216, 518, 226, 528)), fill=(255, 255, 255, 255))
    paste_rotated(layer, item, -11, (512, 506))
    return finish(layer)


def draw_milk():
    item = new_layer()
    draw = ImageDraw.Draw(item)
    cx, cy = 512, 500

    front = [(354, 284), (640, 322), (642, 710), (376, 760), (334, 360)]
    side = [(640, 322), (728, 270), (734, 656), (642, 710)]
    top = [(354, 284), (450, 210), (728, 270), (640, 322)]
    top_face = [(450, 210), (574, 158), (728, 270), (640, 322)]
    draw.polygon(points(side), fill=(200, 221, 255, 255))
    draw.polygon(points(front), fill=(250, 253, 255, 255))
    draw.polygon(points(top), fill=(69, 144, 226, 255))
    draw.polygon(points(top_face), fill=(112, 181, 243, 255))
    draw.line(points(front + [front[0]]), fill=(80, 132, 197, 255), width=px(9), joint="curve")
    draw.line(points(side + [side[0]]), fill=(80, 132, 197, 230), width=px(7), joint="curve")
    draw.line(points(top + [top[0]]), fill=(80, 132, 197, 250), width=px(8), joint="curve")

    draw.ellipse(box((496, 192, 604, 252)), fill=(245, 250, 255, 255), outline=(84, 135, 198, 255), width=px(6))
    draw.ellipse(box((510, 206, 590, 246)), fill=(255, 255, 255, 255))

    draw.rounded_rectangle(box((390, 470, 604, 604)), radius=px(34), fill=(77, 157, 239, 235))
    draw.text((px(407), px(480)), "MILK", fill=(255, 255, 255, 255), font=font(49, True))
    draw.ellipse(box((438, 622, 532, 702)), fill=(255, 245, 239, 255), outline=(81, 133, 199, 230), width=px(4))
    draw.ellipse(box((440, 596, 488, 636)), fill=(250, 246, 235, 255), outline=(70, 90, 120, 150), width=px(3))
    draw.ellipse(box((488, 596, 536, 638)), fill=(67, 58, 63, 255))
    draw.polygon(points([(460, 592), (438, 560), (484, 586)]), fill=(239, 177, 97, 255))
    draw.polygon(points([(504, 594), (540, 566), (522, 606)]), fill=(239, 177, 97, 255))
    draw.ellipse(box((448, 662, 476, 684)), fill=(255, 143, 158, 180))
    draw.ellipse(box((496, 662, 524, 684)), fill=(255, 143, 158, 180))

    draw_face(draw, (492, 418), scale=0.82)
    soft_highlight(draw, (374, 306, 610, 710), fill=(255, 255, 255, 110), width=7)
    return finish(item)


def draw_berry_cake():
    item = new_layer()
    draw = ImageDraw.Draw(item)
    cx = 512

    draw.ellipse(box((304, 286, 720, 506)), fill=(177, 93, 208, 255))
    draw.rounded_rectangle(box((304, 380, 720, 690)), radius=px(68), fill=(242, 207, 235, 255))
    draw.ellipse(box((304, 284, 720, 504)), fill=(157, 73, 197, 255))
    draw.ellipse(box((336, 320, 688, 470)), fill=(214, 154, 235, 255))
    draw.rectangle(box((320, 454, 704, 620)), fill=(246, 226, 242, 255))
    draw.rectangle(box((320, 620, 704, 696)), fill=(193, 128, 79, 255))
    draw.ellipse(box((304, 598, 720, 720)), fill=(196, 128, 79, 255))
    draw.ellipse(box((326, 614, 698, 700)), fill=(226, 171, 111, 255))

    drip_color = (126, 49, 175, 255)
    draw.rounded_rectangle(box((330, 384, 698, 476)), radius=px(34), fill=drip_color)
    for x, y, h, w in [(360, 430, 98, 50), (442, 434, 62, 44), (552, 426, 120, 62), (644, 438, 78, 44)]:
        draw.ellipse(box((x - w / 2, y, x + w / 2, y + h)), fill=drip_color)

    for x, y, w, h in [(362, 516, 64, 60), (480, 538, 62, 58), (598, 510, 68, 62)]:
        draw.ellipse(box((x, y, x + w, y + h)), fill=(105, 48, 154, 255))
        draw.ellipse(box((x + 9, y + 9, x + w - 12, y + h - 10)), fill=(80, 42, 126, 255))

    for angle in range(0, 360, 24):
        ox = math.cos(math.radians(angle)) * 62
        oy = math.sin(math.radians(angle)) * 32
        draw.ellipse(box((cx - 48 + ox, 278 + oy, cx + 58 + ox, 390 + oy)), fill=(255, 246, 242, 230))
    draw.ellipse(box((462, 262, 594, 398)), fill=(255, 248, 244, 255))

    for x, y, radius in [(580, 212, 56), (654, 266, 44), (514, 244, 38)]:
        draw.ellipse(box((x - radius, y - radius, x + radius, y + radius)), fill=(39, 75, 164, 255))
        draw.ellipse(box((x - radius + 11, y - radius + 10, x + radius - 14, y + radius - 13)), fill=(59, 95, 189, 255))
        draw.ellipse(box((x - radius * 0.34, y - radius * 0.45, x + radius * 0.02, y - radius * 0.08)), fill=(255, 255, 255, 180))
        draw.polygon(points([(x - 9, y - radius + 10), (x + 9, y - radius + 10), (x + 2, y - radius + 24), (x - 12, y - radius + 20)]), fill=(28, 45, 109, 255))
    draw.ellipse(box((666, 206, 746, 286)), fill=(105, 186, 98, 255))
    draw.arc(box((668, 220, 742, 282)), 200, 340, fill=(53, 121, 63, 255), width=px(5))

    draw_face(draw, (512, 548), scale=0.82)
    soft_highlight(draw, (338, 302, 692, 492), fill=(255, 255, 255, 120), width=6)
    return finish(item)


def draw_scarf():
    item = new_layer()
    draw = ImageDraw.Draw(item)
    blue = (126, 178, 236, 255)
    deep = (75, 126, 199, 255)

    draw.rounded_rectangle(box((300, 372, 724, 548)), radius=px(88), fill=deep)
    draw.rounded_rectangle(box((318, 338, 692, 500)), radius=px(80), fill=blue)
    draw.rounded_rectangle(box((390, 276, 646, 444)), radius=px(82), fill=(150, 195, 246, 255))
    draw.rounded_rectangle(box((430, 300, 608, 420)), radius=px(54), fill=(186, 217, 255, 255))
    draw.ellipse(box((326, 350, 536, 548)), fill=(126, 178, 236, 255))
    draw.ellipse(box((396, 380, 556, 520)), fill=(229, 244, 255, 205))

    tails = [
        ((294, 500, 430, 782), blue),
        ((420, 508, 558, 822), (105, 160, 224, 255)),
        ((548, 488, 704, 790), (141, 193, 246, 255)),
    ]
    for rect, fill in tails:
        draw.rounded_rectangle(box(rect), radius=px(34), fill=fill)
        x0, y0, x1, y1 = rect
        draw.line(points([(x0 + 20, y0 + 20), (x1 - 20, y1 - 38)]), fill=(236, 248, 255, 105), width=px(5))
        draw.line(points([(x1 - 28, y0 + 20), (x0 + 34, y1 - 46)]), fill=(64, 111, 185, 70), width=px(4))
        for y in range(int(y0 + 54), int(y1 - 36), 70):
            draw.line(points([(x0 + 16, y), (x1 - 14, y + 8)]), fill=(232, 246, 255, 135), width=px(5))

    for x in range(330, 686, 70):
        draw.line(points([(x, 360), (x + 32, 492)]), fill=(236, 248, 255, 115), width=px(5))
        draw.line(points([(x + 38, 354), (x, 486)]), fill=(64, 111, 185, 65), width=px(4))

    for x in (318, 354, 394, 438, 458, 504, 574, 616, 660, 696):
        draw.line(points([(x, 780), (x - 8, 838)]), fill=deep, width=px(7))

    for sx, sy in [(454, 360), (584, 394), (360, 578), (616, 610)]:
        draw.line(points([(sx - 24, sy), (sx + 24, sy)]), fill=(255, 255, 255, 180), width=px(4))
        draw.line(points([(sx, sy - 24), (sx, sy + 24)]), fill=(255, 255, 255, 180), width=px(4))
        draw.line(points([(sx - 16, sy - 16), (sx + 16, sy + 16)]), fill=(255, 255, 255, 140), width=px(3))
        draw.line(points([(sx - 16, sy + 16), (sx + 16, sy - 16)]), fill=(255, 255, 255, 140), width=px(3))

    draw_face(draw, (512, 468), scale=0.65)
    return finish(item)


def draw_snowball():
    item = new_layer()
    draw = ImageDraw.Draw(item)

    draw.ellipse(box((300, 300, 724, 760)), fill=(244, 250, 255, 255))
    draw.ellipse(box((328, 334, 696, 726)), fill=(255, 255, 255, 255))
    for i in range(70):
        rng = random.Random(17 + i)
        x = rng.randint(330, 690)
        y = rng.randint(350, 718)
        face_zone = 430 < x < 602 and 498 < y < 610
        if not face_zone and ((x - 512) / 198) ** 2 + ((y - 530) / 196) ** 2 < 1:
            tone = rng.randint(218, 240)
            draw.ellipse(box((x, y, x + rng.randint(4, 9), y + rng.randint(4, 9))), fill=(tone, min(255, tone + rng.randint(6, 12)), 255, rng.randint(35, 75)))

    draw.rounded_rectangle(box((356, 258, 682, 404)), radius=px(58), fill=(91, 151, 224, 255))
    draw.ellipse(box((372, 214, 652, 384)), fill=(133, 184, 240, 255))
    draw.rectangle(box((374, 328, 660, 420)), fill=(91, 151, 224, 255))
    draw.rounded_rectangle(box((352, 350, 684, 434)), radius=px(42), fill=(77, 132, 205, 255))
    draw.ellipse(box((632, 176, 744, 288)), fill=(250, 253, 255, 255))
    for a in range(0, 360, 35):
        x = 688 + math.cos(math.radians(a)) * 34
        y = 232 + math.sin(math.radians(a)) * 34
        draw.ellipse(box((x - 18, y - 18, x + 18, y + 18)), fill=(238, 247, 255, 230))

    for sx, sy in [(438, 314), (546, 356), (606, 296)]:
        draw.line(points([(sx - 22, sy), (sx + 22, sy)]), fill=(255, 255, 255, 180), width=px(4))
        draw.line(points([(sx, sy - 22), (sx, sy + 22)]), fill=(255, 255, 255, 180), width=px(4))
        draw.line(points([(sx - 15, sy - 15), (sx + 15, sy + 15)]), fill=(255, 255, 255, 140), width=px(3))
        draw.line(points([(sx - 15, sy + 15), (sx + 15, sy - 15)]), fill=(255, 255, 255, 140), width=px(3))

    draw_face(draw, (512, 548), scale=0.92, wink=True)
    return finish(item)


def draw_ice():
    item = new_layer()
    draw = ImageDraw.Draw(item)

    front = [(318, 350), (592, 306), (724, 444), (674, 712), (390, 772), (282, 596)]
    top = [(318, 350), (456, 230), (724, 278), (592, 306)]
    side = [(592, 306), (724, 278), (802, 438), (724, 444)]
    draw.polygon(points(front), fill=(129, 213, 249, 218))
    draw.polygon(points(top), fill=(184, 236, 255, 230))
    draw.polygon(points(side), fill=(93, 182, 233, 210))
    draw.line(points(front + [front[0]]), fill=(215, 248, 255, 250), width=px(10), joint="curve")
    draw.line(points(top + [top[0]]), fill=(239, 254, 255, 250), width=px(8), joint="curve")
    draw.line(points(side + [side[0]]), fill=(195, 235, 255, 230), width=px(8), joint="curve")

    draw.line(points([(388, 398), (600, 360), (686, 454)]), fill=(255, 255, 255, 130), width=px(9))
    draw.line(points([(350, 572), (430, 688), (640, 642)]), fill=(72, 156, 222, 85), width=px(7))
    draw.ellipse(box((324, 708, 736, 828)), fill=(91, 188, 239, 92))
    draw.ellipse(box((724, 708, 808, 770)), fill=(99, 195, 244, 80))

    for x, y, r in [(438, 274, 20), (656, 348, 16), (382, 672, 18), (650, 584, 14)]:
        draw.ellipse(box((x - r, y - r, x + r, y + r)), fill=(255, 255, 255, 120))

    draw_face(draw, (512, 552), scale=0.86)
    return finish(item)


DRAWERS = {
    "fish": draw_fish,
    "milk": draw_milk,
    "berry_cake": draw_berry_cake,
    "scarf": draw_scarf,
    "snowball": draw_snowball,
    "ice": draw_ice,
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, drawer in DRAWERS.items():
        drawer().save(OUT_DIR / f"{name}.png")
    print(f"generated {len(DRAWERS)} transparent shop item illustrations in {OUT_DIR}")


if __name__ == "__main__":
    main()
