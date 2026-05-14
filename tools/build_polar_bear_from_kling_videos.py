import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".local_deps"))

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageFilter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTION_DIR = PROJECT_ROOT / "assets" / "polar_bear" / "role" / "PolarBear" / "action"
DOWNLOAD_DIR = Path("e:/firefox/xiaz")
CANVAS_SIZE = (360, 520)
MAX_SIZE = (335, 505)


def find_video(suffix):
    matches = sorted(DOWNLOAD_DIR.glob(f"*{suffix}*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"Cannot find video matching {suffix!r} in {DOWNLOAD_DIR}")
    return matches[0]


def wipe_watermark(image):
    # Watermarks and sleep "Z" marks are removed later as detached alpha
    # components. Avoid wiping a fixed bottom-right rectangle because the
    # sleeping bear can occupy that area.
    return image.convert("RGBA")


def green_screen_alpha(image):
    image = wipe_watermark(image)
    arr = np.array(image, dtype=np.uint16)
    rgb = arr[:, :, :3]
    r = rgb[:, :, 0]
    g = rgb[:, :, 1]
    b = rgb[:, :, 2]

    green_bg = (g > 125) & (g > r + 38) & (g > b + 38)
    green_bg |= (g > 170) & (r < 165) & (b < 165) & (g > r + 24) & (g > b + 24)

    alpha = np.where(green_bg, 0, 255).astype(np.uint8)
    alpha_image = Image.fromarray(alpha, "L")
    # Close tiny transparent holes caused by MP4 compression without filling large leg gaps.
    alpha_image = alpha_image.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    alpha_image = fill_internal_alpha_holes(alpha_image)
    alpha = np.array(alpha_image, dtype=np.uint8)

    visible = alpha > 0
    green_spill = visible & (g > r + 10) & (g > b + 10)
    softened_green = np.minimum(g, ((r + b) // 2) + 8)
    arr[:, :, 1] = np.where(green_spill, softened_green, g)
    arr[:, :, 3] = alpha
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def fill_internal_alpha_holes(alpha_image):
    alpha = np.array(alpha_image, dtype=np.uint8)
    transparent = alpha == 0
    h, w = transparent.shape
    outside = np.zeros(transparent.shape, dtype=bool)
    queue = deque()

    for x in range(w):
        for y in (0, h - 1):
            if transparent[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if transparent[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((x, y))

    while queue:
        cx, cy = queue.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < w and 0 <= ny < h and transparent[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                queue.append((nx, ny))

    alpha[transparent & ~outside] = 255
    return Image.fromarray(alpha, "L")


def normalize_frame(image):
    image = green_screen_alpha(image)
    bbox = image.getchannel("A").getbbox()
    if bbox:
        image = image.crop(bbox)
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    image.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
    canvas.alpha_composite(image, ((canvas.width - image.width) // 2, canvas.height - image.height - 8))
    remove_detached_alpha(canvas)
    return canvas


def remove_detached_alpha(image):
    alpha = np.array(image.getchannel("A"), dtype=np.uint8)
    mask = alpha > 0
    h, w = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    components = []

    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            queue = deque([(x, y)])
            seen[y, x] = True
            pixels = []
            while queue:
                cx, cy = queue.popleft()
                pixels.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((nx, ny))
            components.append(pixels)

    if len(components) <= 1:
        return

    largest = max(len(component) for component in components)
    keep_threshold = max(12000, int(largest * 0.18))
    cleaned = np.zeros_like(alpha)
    for component in components:
        if len(component) == largest or len(component) >= keep_threshold:
            for x, y in component:
                cleaned[y, x] = alpha[y, x]

    image.putalpha(Image.fromarray(cleaned, "L"))


def sample_indices(total_frames, count, start_ratio=0.0, end_ratio=1.0):
    start = int(total_frames * start_ratio)
    end = max(start + 1, int(total_frames * end_ratio) - 1)
    if count <= 1:
        return [start]
    return [start + round((end - start) * i / (count - 1)) for i in range(count)]


def clear_action(prefix):
    ACTION_DIR.mkdir(parents=True, exist_ok=True)
    for old in ACTION_DIR.glob(f"{prefix}_*.png"):
        try:
            old.unlink()
        except PermissionError:
            pass


def import_video(video_path, prefix, count, start_ratio=0.0, end_ratio=1.0, mirror=False):
    reader = imageio.get_reader(str(video_path), format="ffmpeg")
    meta = reader.get_meta_data()
    fps = float(meta.get("fps") or 24.0)
    duration = float(meta.get("duration") or 5.0)
    total_frames = max(1, int(fps * duration))
    indices = sample_indices(total_frames, count, start_ratio, end_ratio)

    clear_action(prefix)
    saved = 0
    for out_idx, frame_idx in enumerate(indices):
        try:
            frame = Image.fromarray(reader.get_data(frame_idx)).convert("RGBA")
        except Exception:
            continue
        output = normalize_frame(frame)
        if mirror:
            output = output.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        output.save(ACTION_DIR / f"{prefix}_{out_idx:03d}.png")
        saved += 1
    reader.close()
    return saved


def transformed_subject_frame(frame, scale_x=1.0, scale_y=1.0, dy=0, dx=0):
    bbox = frame.getchannel("A").getbbox()
    if not bbox:
        return frame.copy()

    subject = frame.crop(bbox)
    new_size = (
        max(1, int(subject.width * scale_x)),
        max(1, int(subject.height * scale_y)),
    )
    subject = subject.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    x = (CANVAS_SIZE[0] - subject.width) // 2 + dx
    y = CANVAS_SIZE[1] - subject.height - 8 + dy
    canvas.alpha_composite(subject, (x, y))
    return canvas


def load_normalized_frame(video_path, frame_ratio):
    reader = imageio.get_reader(str(video_path), format="ffmpeg")
    meta = reader.get_meta_data()
    fps = float(meta.get("fps") or 24.0)
    duration = float(meta.get("duration") or 5.0)
    total_frames = max(1, int(fps * duration))
    frame_idx = min(total_frames - 1, max(0, int(total_frames * frame_ratio)))
    frame = Image.fromarray(reader.get_data(frame_idx)).convert("RGBA")
    reader.close()
    return normalize_frame(frame)


def make_jump_action(stand_video, crouch_video, prefix):
    clear_action(prefix)
    stand = load_normalized_frame(stand_video, 0.06)
    lifted = load_normalized_frame(stand_video, 0.15)
    crouch = load_normalized_frame(crouch_video, 0.46)
    deep_crouch = load_normalized_frame(crouch_video, 0.54)

    frames = [
        transformed_subject_frame(stand, 1.00, 1.00, 0),
        transformed_subject_frame(crouch, 1.04, 0.96, 10),
        transformed_subject_frame(deep_crouch, 1.08, 0.92, 20),
        transformed_subject_frame(crouch, 1.03, 0.98, 4),
        transformed_subject_frame(lifted, 0.94, 0.94, -20),
        transformed_subject_frame(lifted, 0.88, 0.88, -48),
        transformed_subject_frame(lifted, 0.84, 0.84, -70),
        transformed_subject_frame(lifted, 0.83, 0.83, -82),
        transformed_subject_frame(lifted, 0.84, 0.84, -70),
        transformed_subject_frame(lifted, 0.88, 0.88, -48),
        transformed_subject_frame(lifted, 0.94, 0.94, -20),
        transformed_subject_frame(crouch, 1.06, 0.94, 18),
        transformed_subject_frame(deep_crouch, 1.08, 0.92, 24),
        transformed_subject_frame(crouch, 1.03, 0.98, 8),
        transformed_subject_frame(stand, 1.00, 1.00, 0),
        transformed_subject_frame(stand, 1.00, 1.00, 0),
    ]

    for idx, frame in enumerate(frames):
        frame.save(ACTION_DIR / f"{prefix}_{idx:03d}.png")
    return len(frames)


def make_jump_from_video(jump_video, prefix):
    clear_action(prefix)
    stand = load_normalized_frame(jump_video, 0.02)
    ready = load_normalized_frame(jump_video, 0.31)
    crouch = load_normalized_frame(jump_video, 0.36)
    launch = load_normalized_frame(jump_video, 0.44)
    landing = load_normalized_frame(jump_video, 0.60)
    settle = load_normalized_frame(jump_video, 0.65)

    frames = [
        transformed_subject_frame(stand, 1.00, 1.00, 0),
        transformed_subject_frame(ready, 1.00, 1.00, 0),
        transformed_subject_frame(crouch, 1.04, 0.96, 10),
        transformed_subject_frame(crouch, 1.08, 0.92, 20),
        transformed_subject_frame(launch, 0.96, 0.96, -10),
        transformed_subject_frame(launch, 0.90, 0.90, -36),
        transformed_subject_frame(launch, 0.86, 0.86, -60),
        transformed_subject_frame(launch, 0.84, 0.84, -76),
        transformed_subject_frame(launch, 0.86, 0.86, -62),
        transformed_subject_frame(launch, 0.90, 0.90, -38),
        transformed_subject_frame(launch, 0.96, 0.96, -12),
        transformed_subject_frame(landing, 1.05, 0.95, 14),
        transformed_subject_frame(landing, 1.08, 0.92, 24),
        transformed_subject_frame(settle, 1.03, 0.97, 8),
        transformed_subject_frame(ready, 1.00, 1.00, 0),
        transformed_subject_frame(stand, 1.00, 1.00, 0),
    ]

    for idx, frame in enumerate(frames):
        frame.save(ACTION_DIR / f"{prefix}_{idx:03d}.png")
    return len(frames)


def make_jump_from_2171(jump_video, prefix):
    clear_action(prefix)
    stand = load_normalized_frame(jump_video, 0.04)
    ready = load_normalized_frame(jump_video, 0.28)
    crouch = load_normalized_frame(jump_video, 0.37)
    launch = load_normalized_frame(jump_video, 0.45)
    landing = load_normalized_frame(jump_video, 0.63)
    settle = load_normalized_frame(jump_video, 0.72)
    finish = load_normalized_frame(jump_video, 0.92)

    frames = [
        transformed_subject_frame(stand, 1.00, 1.00, 0),
        transformed_subject_frame(ready, 1.00, 1.00, 0),
        transformed_subject_frame(crouch, 1.04, 0.96, 10),
        transformed_subject_frame(crouch, 1.08, 0.92, 22),
        transformed_subject_frame(launch, 0.98, 0.98, -8),
        transformed_subject_frame(launch, 0.94, 0.94, -24),
        transformed_subject_frame(launch, 0.90, 0.90, -42),
        transformed_subject_frame(launch, 0.88, 0.88, -54),
        transformed_subject_frame(launch, 0.90, 0.90, -42),
        transformed_subject_frame(launch, 0.94, 0.94, -24),
        transformed_subject_frame(landing, 1.04, 0.96, 12),
        transformed_subject_frame(landing, 1.08, 0.92, 22),
        transformed_subject_frame(settle, 1.02, 0.98, 6),
        transformed_subject_frame(finish, 1.00, 1.00, 0),
        transformed_subject_frame(stand, 1.00, 1.00, 0),
    ]

    for idx, frame in enumerate(frames):
        frame.save(ACTION_DIR / f"{prefix}_{idx:03d}.png")
    return len(frames)


def main():
    videos = {
        "wave_a": find_video("5138_0"),
        "sleep": find_video("5141_0"),
        "idle": find_video("4054_0"),
        "idle_life": find_video("2252_0"),
        "idle_blink": find_video("2528_0"),
        "wave_b": find_video("4064_0"),
        "walk": find_video("5223_0"),
        "jump": find_video("2171_0"),
        "touch": find_video("5515_0"),
    }

    results = {
        "video_idle": import_video(videos["idle"], "video_idle", 24, 0.0, 0.80),
        "video_idle_static": import_video(videos["idle"], "video_idle_static", 1, 0.08, 0.08),
        "video2252_idle_life": import_video(videos["idle_life"], "video2252_idle_life", 36, 0.00, 0.80),
        "video2252_idle_still": import_video(videos["idle_life"], "video2252_idle_still", 1, 0.00, 0.00),
        "video2252_blink": import_video(videos["idle_life"], "video2252_blink", 24, 0.00, 0.32),
        "video2528_idle_blink": import_video(videos["idle_blink"], "video2528_idle_blink", 72, 0.00, 1.00),
        "video4064_wave_clean": import_video(videos["wave_b"], "video4064_wave_clean", 32, 0.05, 0.95),
        "video5223_walk_right": import_video(videos["walk"], "video5223_walk_right", 32, 0.24, 0.98),
        "video5223_walk_left": import_video(videos["walk"], "video5223_walk_left", 32, 0.24, 0.98, mirror=True),
        "video2171_jump_clean": make_jump_from_2171(videos["jump"], "video2171_jump_clean"),
        "video5515_touch": import_video(videos["touch"], "video5515_touch", 28, 0.00, 0.96),
        "video_drag": import_video(videos["wave_a"], "video_drag", 16, 0.0, 0.55),
        "video_sleep": import_video(videos["sleep"], "video_sleep", 24, 0.66, 0.98),
    }
    for name, count in results.items():
        print(f"{name}: {count} frames")
    print(f"output: {ACTION_DIR}")


if __name__ == "__main__":
    main()
