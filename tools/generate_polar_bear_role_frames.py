import math
from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PROJECT_ROOT / "assets" / "polar_bear"
ROLE_ACTION_DIR = ASSET_ROOT / "role" / "PolarBear" / "action"
SOURCE_IMAGE = ASSET_ROOT / "polar-bear-realistic.png"
CANVAS_SIZE = (360, 520)
MAX_SUBJECT_SIZE = (330, 500)


def load_subject():
    image = Image.open(SOURCE_IMAGE).convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox:
        image = image.crop(bbox)
    image.thumbnail(MAX_SUBJECT_SIZE, Image.Resampling.LANCZOS)
    return image


def paste_centered(subject, x=0, y=0, scale_x=1.0, scale_y=1.0, angle=0):
    width = max(1, int(subject.width * scale_x))
    height = max(1, int(subject.height * scale_y))
    frame = subject.resize((width, height), Image.Resampling.LANCZOS)
    if angle:
        frame = frame.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)

    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    px = (CANVAS_SIZE[0] - frame.width) // 2 + int(x)
    py = CANVAS_SIZE[1] - frame.height - 8 + int(y)
    canvas.alpha_composite(frame, (px, py))
    return canvas


def add_wave_marks(frame, tick):
    draw = ImageDraw.Draw(frame)
    phase = math.sin(tick * math.pi * 2) * 9
    base_x = 86
    base_y = 148 + phase
    color = (126, 232, 255, 165)
    draw.arc((base_x - 10, base_y - 20, base_x + 24, base_y + 34), 285, 35, fill=color, width=2)
    draw.arc((base_x - 26, base_y - 32, base_x + 36, base_y + 48), 285, 35, fill=color, width=2)


def add_sleep_marks(frame, index):
    draw = ImageDraw.Draw(frame)
    y = 98 - (index % 12)
    draw.text((274, y), "Z", fill=(222, 248, 255, 220))
    draw.text((293, y - 16), "z", fill=(222, 248, 255, 190))


def save_action(name, frames):
    ROLE_ACTION_DIR.mkdir(parents=True, exist_ok=True)
    for old in ROLE_ACTION_DIR.glob(f"{name}_*.png"):
        old.unlink()
    for index, frame in enumerate(frames):
        frame.save(ROLE_ACTION_DIR / f"{name}_{index:03d}.png")


def make_idle(subject):
    frames = []
    for i in range(24):
        t = math.sin(i / 24 * math.pi * 2)
        frames.append(paste_centered(subject, y=t * 2, scale_x=1 + t * 0.004, scale_y=1 + t * 0.008))
    save_action("idle", frames)


def make_walk(subject, name, facing=1):
    frames = []
    source = subject if facing > 0 else subject.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    for i in range(24):
        step = math.sin(i / 24 * math.pi * 4)
        sway = math.sin(i / 24 * math.pi * 2)
        frames.append(
            paste_centered(
                source,
                x=sway * 3,
                y=-abs(step) * 8,
                scale_x=1 + abs(step) * 0.006,
                scale_y=1 - abs(step) * 0.006,
                angle=step * 2.2,
            )
        )
    save_action(name, frames)


def make_jump(subject):
    frames = []
    for i in range(18):
        progress = i / 17
        lift = math.sin(progress * math.pi) * 54
        squash = math.sin(progress * math.pi)
        frames.append(paste_centered(subject, y=-lift, scale_x=1 + squash * 0.025, scale_y=1 - squash * 0.025))
    save_action("jump", frames)


def make_wave(subject):
    frames = []
    for i in range(24):
        progress = i / 24
        sway = math.sin(progress * math.pi * 2)
        frame = paste_centered(subject, x=sway * 2, y=math.sin(progress * math.pi * 4) * 1.5, angle=sway * 1.4)
        add_wave_marks(frame, progress)
        frames.append(frame)
    save_action("wave", frames)


def make_sleep(subject):
    frames = []
    for i in range(18):
        t = math.sin(i / 18 * math.pi * 2)
        frame = paste_centered(subject, y=4 + t * 1.5, scale_x=1.01, scale_y=0.985, angle=-1.2)
        add_sleep_marks(frame, i)
        frames.append(frame)
    save_action("sleep", frames)


def make_drag(subject):
    frames = []
    for i in range(8):
        t = math.sin(i / 8 * math.pi * 2)
        frames.append(paste_centered(subject, y=-8, angle=t * 4.5, x=t * 2))
    save_action("drag", frames)


def main():
    subject = load_subject()
    make_idle(subject)
    make_walk(subject, "walk_right", facing=1)
    make_walk(subject, "walk_left", facing=-1)
    make_jump(subject)
    make_wave(subject)
    make_sleep(subject)
    make_drag(subject)
    print(f"generated PolarBear role frames in {ROLE_ACTION_DIR}")


if __name__ == "__main__":
    main()
