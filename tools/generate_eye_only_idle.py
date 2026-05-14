from math import cos, pi
from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTION_DIR = PROJECT_ROOT / "assets" / "polar_bear" / "role" / "PolarBear" / "action"
BASE_FRAME = ACTION_DIR / "video2252_idle_still_000.png"
PREFIX = "video2252_eye_idle_v2"
FRAME_COUNT = 48
SCALE = 4


def clean_watermark(image):
    image = image.copy()
    pixels = image.load()
    width, height = image.size
    for y in range(height - 35, height):
        for x in range(width - 105, width):
            pixels[x, y] = (0, 0, 0, 0)
    return image


def draw_eye_lid(draw, eye, closure, fur_color, crease_color):
    if closure <= 0.02:
        return

    x1, y1, x2, y2 = [int(v * SCALE) for v in eye]
    width = x2 - x1
    height = y2 - y1
    center_y = int((y1 + y2) / 2)
    cover_height = max(1, int((height + 2 * SCALE) * closure))
    patch = (
        x1 - SCALE,
        center_y - cover_height // 2,
        x2 + SCALE,
        center_y + cover_height // 2,
    )
    draw.ellipse(patch, fill=fur_color)

    if closure > 0.72:
        draw.line((x1, center_y, x2, center_y), fill=crease_color, width=max(1, SCALE))


def make_frame(base, closure):
    work = base.resize((base.width * SCALE, base.height * SCALE), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(work, "RGBA")

    # Coordinates are measured on video2252_idle_still_000.png.
    draw_eye_lid(draw, (126, 40, 137, 50), closure, (218, 211, 198, 245), (118, 104, 88, 155))
    draw_eye_lid(draw, (160, 32, 170, 41), closure, (224, 218, 207, 245), (118, 104, 88, 155))

    return work.resize(base.size, Image.Resampling.LANCZOS)


def main():
    ACTION_DIR.mkdir(parents=True, exist_ok=True)
    base = clean_watermark(Image.open(BASE_FRAME).convert("RGBA"))

    for old in ACTION_DIR.glob(f"{PREFIX}_*.png"):
        old.unlink(missing_ok=True)

    for index in range(FRAME_COUNT):
        t = index / FRAME_COUNT
        # Smooth open -> closed -> open loop with no held source-video frames.
        closure = 0.5 - 0.5 * cos(2 * pi * t)
        frame = make_frame(base, closure)
        frame.save(ACTION_DIR / f"{PREFIX}_{index:03d}.png")

    print(f"{PREFIX}: {FRAME_COUNT} frames")


if __name__ == "__main__":
    main()
