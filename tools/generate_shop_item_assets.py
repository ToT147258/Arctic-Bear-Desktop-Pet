from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "assets" / "shop" / "reference"
OUT_DIR = ROOT / "assets" / "shop" / "items"
SIZE = 1024


REFERENCE_IMAGES = {
    "dessert": REFERENCE_DIR / "winter_dessert_set.png",
    "fish": REFERENCE_DIR / "dried_fish_set.png",
}


ASSETS = {
    "fish": {
        "source": "fish",
        "box": (50, 245, 1230, 1080),
        "fit": (910, 640),
        "mask": [
            ("polygon", [(44, 390), (145, 220), (410, 58), (1000, 38), (1165, 275), (1120, 610), (840, 826), (282, 760), (16, 570)]),
        ],
        "warm_cutout": True,
        "shadow": (0, 96, 0.74),
    },
    "milk": {
        "source": "dessert",
        "box": (34, 46, 448, 736),
        "fit": (570, 820),
        "mask": [
            ("rounded", (70, 168, 350, 682), 82),
            ("rounded", (72, 34, 346, 234), 74),
            ("polygon", [(220, 0), (308, 0), (286, 202), (210, 202)]),
            ("ellipse", (96, 126, 338, 290)),
        ],
        "shadow": (0, 80, 0.66),
    },
    "berry_cake": {
        "source": "dessert",
        "box": (220, 420, 820, 1018),
        "fit": (820, 740),
        "mask": [
            ("polygon", [(28, 238), (138, 128), (470, 92), (588, 178), (560, 476), (320, 584), (58, 520)]),
            ("ellipse", (8, 352, 564, 598)),
            ("ellipse", (165, 92, 520, 238)),
        ],
        "shadow": (0, 90, 0.72),
    },
    "snowball": {
        "source": "dessert",
        "box": (754, 560, 1216, 1116),
        "fit": (640, 780),
        "mask": [
            ("ellipse", (112, 182, 398, 540)),
            ("ellipse", (126, 36, 358, 274)),
            ("rounded", (114, 36, 366, 150), 48),
            ("polygon", [(80, 220), (400, 216), (410, 310), (92, 300)]),
            ("polygon", [(248, 272), (378, 286), (384, 470), (292, 440)]),
        ],
        "shadow": (0, 78, 0.7),
    },
    "scarf": {
        "source": "dessert",
        "box": (500, 198, 1165, 592),
        "fit": (860, 520),
        "mask": [
            ("ellipse", (20, 28, 650, 372)),
            ("rounded", (50, 120, 642, 352), 98),
            ("ellipse_cut", (222, 90, 500, 250)),
            ("polygon", [(500, 210), (656, 252), (650, 390), (480, 360)]),
        ],
        "shadow": (0, 66, 0.62),
    },
    "ice": {
        "source": "dessert",
        "box": (654, 808, 910, 1062),
        "fit": (560, 560),
        "mask": [
            ("polygon", [(42, 56), (154, 8), (232, 78), (210, 210), (72, 236), (8, 132)]),
            ("polygon", [(70, 84), (232, 78), (210, 210), (104, 228)]),
        ],
        "shadow": (0, 62, 0.58),
    },
}


def rounded_rectangle(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


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
            rounded_rectangle(draw, shape[1], shape[2], 255)
    return mask.filter(ImageFilter.GaussianBlur(3))


def warm_subject_mask(image):
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    mask = Image.new("L", rgba.size, 0)
    out = mask.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            warm = r > 115 and g > 82 and b < 190 and r + 18 > b
            dark_detail = r < 90 and g < 82 and b < 82
            fin_detail = r > 170 and g > 135 and b < 145
            if warm or dark_detail or fin_detail:
                out[x, y] = 255
    return mask.filter(ImageFilter.MaxFilter(19)).filter(ImageFilter.GaussianBlur(5))


def trim_alpha(image):
    bbox = image.getbbox()
    if not bbox:
        return image
    return image.crop(bbox)


def fit_to_canvas(image, max_width, max_height):
    width, height = image.size
    scale = min(max_width / width, max_height / height)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def add_shadow(canvas, item, offset_y, strength):
    alpha = item.getchannel("A")
    shadow = Image.new("RGBA", item.size, (0, 0, 0, 0))
    shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(18)).point(lambda value: int(value * strength)))
    x = (SIZE - item.width) // 2
    y = (SIZE - item.height) // 2 + offset_y
    canvas.alpha_composite(shadow, (x, y))


def build_asset(name, spec, sources):
    source = sources[spec["source"]].convert("RGBA")
    crop = source.crop(spec["box"])
    mask = build_mask(crop.size, spec["mask"])
    if spec.get("warm_cutout"):
        color_mask = warm_subject_mask(crop)
        mask = Image.eval(Image.composite(mask, Image.new("L", mask.size, 0), color_mask), lambda value: value)
    crop.putalpha(mask)
    item = trim_alpha(crop)
    item = fit_to_canvas(item, *spec["fit"])

    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow_x, shadow_y, shadow_strength = spec["shadow"]
    add_shadow(canvas, item, shadow_y, shadow_strength)
    x = (SIZE - item.width) // 2 + shadow_x
    y = (SIZE - item.height) // 2
    canvas.alpha_composite(item, (x, y))

    canvas.save(OUT_DIR / f"{name}.png")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    missing = [path for path in REFERENCE_IMAGES.values() if not path.exists()]
    if missing:
        names = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing reference image(s): {names}")

    sources = {key: Image.open(path) for key, path in REFERENCE_IMAGES.items()}
    for name, spec in ASSETS.items():
        build_asset(name, spec, sources)
    print(f"generated {len(ASSETS)} transparent shop item cutouts in {OUT_DIR}")


if __name__ == "__main__":
    main()
