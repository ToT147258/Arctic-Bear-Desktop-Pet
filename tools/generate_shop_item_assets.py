from pathlib import Path
from collections import deque

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "assets" / "shop" / "reference" / "kawaii_item_grid.png"
OUT_DIR = ROOT / "assets" / "shop" / "items"


PANELS = {
    "fish": (12, 13, 410, 620),
    "milk": (424, 13, 827, 620),
    "berry_cake": (842, 13, 1242, 620),
    "scarf": (12, 633, 410, 1242),
    "snowball": (424, 633, 827, 1242),
    "ice": (842, 633, 1242, 1242),
}


ASSETS = {
    "fish": {
        "panel": "fish",
        "max_side": 920,
        "shadow": 0.24,
        "cleanup": ["blue_card"],
        "protect": [
            (
                "polygon",
                [
                    (214, 58),
                    (330, 116),
                    (340, 170),
                    (316, 302),
                    (276, 444),
                    (218, 542),
                    (158, 582),
                    (102, 548),
                    (124, 424),
                    (145, 306),
                    (166, 178),
                    (190, 82),
                ],
            )
        ],
        "mask": [
            (
                "polygon",
                [
                    (220, 42),
                    (280, 68),
                    (340, 106),
                    (366, 154),
                    (350, 230),
                    (323, 342),
                    (287, 452),
                    (235, 544),
                    (170, 596),
                    (100, 564),
                    (83, 528),
                    (102, 464),
                    (120, 372),
                    (137, 282),
                    (154, 192),
                    (167, 118),
                    (190, 64),
                ],
            )
        ],
    },
    "milk": {
        "panel": "milk",
        "max_side": 870,
        "shadow": 0.22,
        "cleanup": ["blue_card"],
        "protect": [
            (
                "polygon",
                [
                    (132, 124),
                    (190, 92),
                    (298, 98),
                    (350, 154),
                    (354, 486),
                    (286, 548),
                    (112, 522),
                    (88, 192),
                ],
            ),
            ("ellipse", (166, 82, 276, 138)),
        ],
        "mask": [
            (
                "polygon",
                [
                    (128, 118),
                    (186, 84),
                    (300, 90),
                    (354, 150),
                    (356, 488),
                    (290, 556),
                    (108, 530),
                    (84, 190),
                ],
            ),
            ("ellipse", (154, 70, 285, 144)),
        ],
    },
    "berry_cake": {
        "panel": "berry_cake",
        "max_side": 890,
        "shadow": 0.22,
        "cleanup": ["cake_lavender"],
        "protect": [
            ("rounded", (50, 250, 364, 530), 68),
            ("ellipse", (50, 152, 364, 314)),
            ("ellipse", (90, 132, 238, 266)),
            ("ellipse", (204, 94, 330, 220)),
            ("ellipse", (258, 162, 382, 282)),
            ("polygon", [(302, 138), (376, 104), (356, 180), (310, 174)]),
        ],
        "mask": [
            ("rounded", (42, 244, 372, 536), 72),
            ("ellipse", (38, 142, 374, 322)),
            ("ellipse", (76, 122, 248, 280)),
            ("ellipse", (196, 80, 338, 226)),
            ("ellipse", (248, 154, 390, 290)),
            ("polygon", [(296, 130), (388, 92), (362, 188), (302, 182)]),
            ("ellipse", (18, 438, 390, 560)),
        ],
    },
    "scarf": {
        "panel": "scarf",
        "max_side": 900,
        "shadow": 0.22,
        "cleanup": ["pink_card"],
        "mask": [
            ("ellipse", (62, 94, 370, 326)),
            ("rounded", (56, 178, 362, 354), 66),
            ("rounded", (48, 264, 184, 552), 42),
            ("rounded", (176, 258, 318, 574), 42),
            ("rounded", (262, 260, 380, 500), 38),
            ("polygon", [(48, 390), (182, 404), (164, 574), (24, 546)]),
            ("polygon", [(252, 376), (380, 386), (378, 516), (272, 548)]),
            ("cut_ellipse", (142, 142, 314, 284)),
        ],
    },
    "snowball": {
        "panel": "snowball",
        "max_side": 880,
        "shadow": 0.22,
        "cleanup": ["mint_card"],
        "protect": [
            ("ellipse", (78, 196, 336, 532)),
            ("ellipse", (110, 108, 306, 220)),
            ("rounded", (102, 168, 320, 246), 36),
            ("ellipse", (276, 82, 336, 142)),
        ],
        "mask": [
            ("ellipse", (70, 188, 344, 540)),
            ("ellipse", (104, 102, 316, 224)),
            ("rounded", (96, 162, 328, 252), 40),
            ("ellipse", (270, 74, 342, 148)),
        ],
    },
    "ice": {
        "panel": "ice",
        "max_side": 900,
        "shadow": 0.2,
        "cleanup": ["ice_lavender"],
        "protect": [
            (
                "polygon",
                [
                    (84, 178),
                    (202, 110),
                    (322, 140),
                    (356, 278),
                    (314, 430),
                    (178, 480),
                    (74, 382),
                ],
            ),
            ("ellipse", (56, 424, 364, 540)),
            ("ellipse", (324, 466, 390, 526)),
        ],
        "mask": [
            (
                "polygon",
                [
                    (78, 170),
                    (202, 98),
                    (330, 130),
                    (364, 280),
                    (320, 440),
                    (176, 492),
                    (66, 388),
                ],
            ),
            ("ellipse", (44, 414, 372, 556)),
            ("ellipse", (316, 458, 398, 536)),
        ],
    },
}


def draw_shape(draw, shape, fill):
    kind = shape[0]
    if kind == "polygon":
        draw.polygon(shape[1], fill=fill)
    elif kind == "ellipse":
        draw.ellipse(shape[1], fill=fill)
    elif kind == "cut_ellipse":
        draw.ellipse(shape[1], fill=0)
    elif kind == "rounded":
        draw.rounded_rectangle(shape[1], radius=shape[2], fill=fill)


def build_mask(size, shapes, blur=1.15):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for shape in shapes:
        draw_shape(draw, shape, 255)
    if blur:
        return mask.filter(ImageFilter.GaussianBlur(blur))
    return mask


def is_background_pixel(rule, r, g, b, x, y):
    if rule == "blue_card":
        return b > 214 and g > 196 and r < 236 and b - r > 18 and g - r > 4
    if rule == "pink_card":
        return r > 214 and b > 186 and g < 228 and r - g > 15 and b - g > -12
    if rule == "mint_card":
        return g > 204 and r > 176 and b > 178 and g - r > 8 and g - b > 2
    if rule == "cake_lavender":
        return y < 240 and r > 198 and g > 176 and b > 212 and b - g > 16 and b - r > 2
    if rule == "ice_lavender":
        return r > 218 and g > 218 and b > 232 and b - r > 6
    return False


def cleanup_card_background(image, rules, protect_mask=None):
    if not rules:
        return image
    pixels = image.load()
    protected = protect_mask.load() if protect_mask else None
    width, height = image.size
    for y in range(height):
        for x in range(width):
            r, g, b, alpha = pixels[x, y]
            if not alpha:
                continue
            if protected and protected[x, y] > 8:
                continue
            if any(is_background_pixel(rule, r, g, b, x, y) for rule in rules):
                pixels[x, y] = (r, g, b, 0)
    return image


def keep_largest_alpha_component(image):
    width, height = image.size
    alpha = image.getchannel("A").load()
    visited = bytearray(width * height)
    best_component = []
    best_count = 0

    for start_y in range(height):
        for start_x in range(width):
            start_index = start_y * width + start_x
            if visited[start_index] or alpha[start_x, start_y] <= 8:
                continue

            component = []
            queue = deque([(start_x, start_y)])
            visited[start_index] = 1
            while queue:
                x, y = queue.popleft()
                component.append((x, y))
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    index = ny * width + nx
                    if visited[index] or alpha[nx, ny] <= 8:
                        continue
                    visited[index] = 1
                    queue.append((nx, ny))

            if len(component) > best_count:
                best_count = len(component)
                best_component = component

    keep = Image.new("L", (width, height), 0)
    keep_pixels = keep.load()
    for x, y in best_component:
        keep_pixels[x, y] = 255

    original_alpha = image.getchannel("A")
    image.putalpha(Image.composite(original_alpha, Image.new("L", (width, height), 0), keep))
    return image


def trim_alpha(image):
    bbox = image.getchannel("A").getbbox()
    return image.crop(bbox) if bbox else image


def fit_to_max_side(image, max_side):
    scale = max_side / max(image.size)
    if scale <= 1:
        return image
    target = (round(image.width * scale), round(image.height * scale))
    return image.resize(target, Image.Resampling.LANCZOS)


def add_transparent_depth(item, strength):
    padding = 48
    shadow_offset = 26
    canvas = Image.new(
        "RGBA",
        (item.width + padding * 2, item.height + padding * 2 + shadow_offset),
        (0, 0, 0, 0),
    )
    shadow = Image.new("RGBA", item.size, (0, 0, 0, 0))
    shadow_alpha = item.getchannel("A").filter(ImageFilter.GaussianBlur(18)).point(lambda value: int(value * strength))
    shadow.putalpha(shadow_alpha)
    canvas.alpha_composite(shadow, (padding, padding + shadow_offset))
    canvas.alpha_composite(item, (padding, padding))
    return trim_alpha(canvas)


def build_asset(name, source):
    spec = ASSETS[name]
    panel = source.crop(PANELS[spec["panel"]]).convert("RGBA")
    mask = build_mask(panel.size, spec["mask"])
    protect_mask = build_mask(panel.size, spec.get("protect", []), blur=0) if spec.get("protect") else None
    panel.putalpha(mask)
    panel = cleanup_card_background(panel, spec.get("cleanup", []), protect_mask)
    panel = keep_largest_alpha_component(panel)
    item = trim_alpha(panel)
    item = fit_to_max_side(item, spec["max_side"])
    item = ImageEnhance.Sharpness(item).enhance(1.08)
    item = ImageEnhance.Contrast(item).enhance(1.03)
    item = add_transparent_depth(item, spec["shadow"])
    item.save(OUT_DIR / f"{name}.png")


def main():
    if not REFERENCE.exists():
        raise FileNotFoundError(f"Missing reference image: {REFERENCE}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = Image.open(REFERENCE)
    for name in ASSETS:
        build_asset(name, source)
    print(f"generated {len(ASSETS)} source-based transparent shop items in {OUT_DIR}")


if __name__ == "__main__":
    main()
