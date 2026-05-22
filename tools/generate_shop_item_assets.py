from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "assets" / "shop" / "reference" / "realistic_item_sheet.png"
OUT_DIR = ROOT / "assets" / "shop" / "items"


# The generated sheet is intentionally stored as a source asset. These boxes
# keep neighboring objects from leaking into transparent cutouts.
CROP_BOXES = {
    "fish": (0.00, 0.02, 0.37, 0.50),
    "milk": (0.37, 0.00, 0.64, 0.54),
    "berry_cake": (0.63, 0.04, 1.00, 0.50),
    "snowball": (0.02, 0.52, 0.35, 0.99),
    "scarf": (0.34, 0.54, 0.67, 1.00),
    "ice": (0.66, 0.56, 1.00, 1.00),
}


def remove_green_background(image):
    rgba = image.convert("RGBA")
    data = np.asarray(rgba).astype(np.float32)
    rgb = data[:, :, :3]
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    max_rb = np.maximum(red, blue)

    green_strength = (green - max_rb - 16) / 112
    green_brightness = (green - 96) / 132
    alpha_remove = np.clip(green_strength, 0, 1) * np.clip(green_brightness, 0, 1)
    hard_green = (green > 145) & (red < 128) & (blue < 128) & (green > max_rb * 1.22)
    alpha_remove = np.where(hard_green, 1.0, alpha_remove)

    alpha = ((1 - alpha_remove) * 255).clip(0, 255).astype(np.uint8)
    alpha[alpha < 14] = 0

    # Despill the antialiased edge so no neon-green fringe survives.
    spill = (alpha > 0) & (green > max_rb + 8)
    rgb[:, :, 1] = np.where(spill, np.minimum(green, max_rb + 6), green)
    rgb[alpha == 0] = 0

    out = np.dstack([rgb.clip(0, 255).astype(np.uint8), alpha])
    return Image.fromarray(out, "RGBA")


def trim_alpha(image, padding=18):
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        return image
    return image.crop(
        (
            max(0, bbox[0] - padding),
            max(0, bbox[1] - padding),
            min(image.width, bbox[2] + padding),
            min(image.height, bbox[3] + padding),
        )
    )


def fit_icon(image, max_size=560):
    image = trim_alpha(image)
    scale = min(1.0, max_size / max(image.size))
    if scale < 1:
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    return image


def polish(image):
    alpha = image.getchannel("A").filter(ImageFilter.GaussianBlur(0.35))
    image.putalpha(alpha)
    image = ImageEnhance.Sharpness(image).enhance(1.06)
    image = ImageEnhance.Contrast(image).enhance(1.03)
    image = ImageEnhance.Color(image).enhance(1.04)
    return image


def build_items():
    if not REFERENCE.exists():
        raise FileNotFoundError(f"Missing generated item sheet: {REFERENCE}")

    sheet = Image.open(REFERENCE).convert("RGBA")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, box in CROP_BOXES.items():
        pixel_box = (
            round(box[0] * sheet.width),
            round(box[1] * sheet.height),
            round(box[2] * sheet.width),
            round(box[3] * sheet.height),
        )
        cell = sheet.crop(pixel_box)
        icon = remove_green_background(cell)
        icon = fit_icon(icon)
        icon = polish(icon)
        icon.save(OUT_DIR / f"{name}.png")

    print(f"generated {len(CROP_BOXES)} realistic 3D shop item assets in {OUT_DIR}")


if __name__ == "__main__":
    build_items()
