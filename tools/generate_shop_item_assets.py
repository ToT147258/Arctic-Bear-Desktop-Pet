from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "assets" / "shop" / "reference" / "kawaii_item_grid.png"
OUT_DIR = ROOT / "assets" / "shop" / "items"
SIZE = 1024


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
        "fit": (600, 860),
        "mask": [
            ("polygon", [(222, 42), (352, 112), (326, 262), (288, 420), (220, 548), (90, 544), (126, 390), (164, 218), (188, 78)]),
            ("ellipse", (178, 46, 340, 166)),
            ("ellipse", (74, 426, 220, 566)),
        ],
        "rotate": -4,
        "shadow": 0.48,
    },
    "milk": {
        "panel": "milk",
        "fit": (690, 790),
        "mask": [
            ("polygon", [(80, 156), (130, 104), (294, 104), (332, 148), (334, 496), (262, 556), (100, 506)]),
            ("rounded", (86, 214, 332, 532), 42),
            ("rounded", (116, 96, 304, 180), 24),
            ("ellipse", (162, 88, 244, 166)),
        ],
        "rotate": 0,
        "shadow": 0.45,
    },
    "berry_cake": {
        "panel": "berry_cake",
        "fit": (760, 760),
        "mask": [
            ("ellipse", (58, 150, 354, 522)),
            ("rounded", (70, 255, 352, 518), 76),
            ("ellipse", (104, 142, 238, 278)),
            ("ellipse", (210, 110, 328, 242)),
            ("ellipse", (260, 190, 372, 292)),
        ],
        "rotate": 0,
        "shadow": 0.45,
    },
    "scarf": {
        "panel": "scarf",
        "fit": (820, 820),
        "mask": [
            ("ellipse", (54, 110, 354, 316)),
            ("ellipse_cut", (134, 152, 286, 240)),
            ("rounded", (46, 238, 364, 426), 52),
            ("polygon", [(54, 330), (140, 340), (126, 526), (12, 492)]),
            ("polygon", [(240, 338), (360, 342), (362, 542), (256, 520)]),
            ("ellipse", (64, 184, 350, 372)),
        ],
        "rotate": 0,
        "shadow": 0.44,
    },
    "snowball": {
        "panel": "snowball",
        "fit": (740, 800),
        "mask": [
            ("ellipse", (82, 166, 324, 520)),
            ("ellipse", (108, 90, 300, 214)),
            ("rounded", (112, 78, 300, 172), 42),
            ("ellipse", (236, 48, 332, 136)),
        ],
        "rotate": 0,
        "shadow": 0.46,
    },
    "ice": {
        "panel": "ice",
        "fit": (720, 760),
        "mask": [
            ("polygon", [(74, 174), (188, 96), (314, 142), (356, 292), (304, 454), (142, 500), (58, 390)]),
            ("polygon", [(84, 210), (190, 112), (324, 156), (358, 294), (300, 444), (150, 486), (76, 366)]),
            ("ellipse", (60, 430, 360, 536)),
        ],
        "rotate": 0,
        "shadow": 0.42,
    },
}


def build_mask(size, shapes):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for shape in shapes:
        kind = shape[0]
        if kind == "polygon":
            draw.polygon(shape[1], fill=255)
        elif kind == "ellipse":
            draw.ellipse(shape[1], fill=255)
        elif kind == "ellipse_cut":
            draw.ellipse(shape[1], fill=0)
        elif kind == "rounded":
            draw.rounded_rectangle(shape[1], radius=shape[2], fill=255)
    return mask.filter(ImageFilter.GaussianBlur(3))


def trim_alpha(image):
    bbox = image.getbbox()
    return image.crop(bbox) if bbox else image


def fit_to_canvas(image, max_width, max_height):
    width, height = image.size
    scale = min(max_width / width, max_height / height)
    target = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(target, Image.Resampling.LANCZOS)


def add_shadow(canvas, item, strength):
    alpha = item.getchannel("A")
    shadow = Image.new("RGBA", item.size, (0, 0, 0, 0))
    shadow_alpha = alpha.filter(ImageFilter.GaussianBlur(22)).point(lambda value: int(value * strength))
    shadow.putalpha(shadow_alpha)
    x = (SIZE - item.width) // 2
    y = (SIZE - item.height) // 2 + 36
    canvas.alpha_composite(shadow, (x, y))


def build_asset(name, source):
    spec = ASSETS[name]
    panel = source.crop(PANELS[spec["panel"]]).convert("RGBA")
    mask = build_mask(panel.size, spec["mask"])
    panel.putalpha(mask)
    item = trim_alpha(panel)
    if spec.get("rotate"):
        item = item.rotate(spec["rotate"], resample=Image.Resampling.BICUBIC, expand=True)
        item = trim_alpha(item)
    item = fit_to_canvas(item, *spec["fit"])

    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    add_shadow(canvas, item, spec["shadow"])
    x = (SIZE - item.width) // 2
    y = (SIZE - item.height) // 2
    canvas.alpha_composite(item, (x, y))
    canvas.save(OUT_DIR / f"{name}.png")


def main():
    if not REFERENCE.exists():
        raise FileNotFoundError(f"Missing reference image: {REFERENCE}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = Image.open(REFERENCE)
    for name in ASSETS:
        build_asset(name, source)
    print(f"generated {len(ASSETS)} kawaii shop item cutouts in {OUT_DIR}")


if __name__ == "__main__":
    main()
