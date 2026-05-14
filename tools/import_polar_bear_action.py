import argparse
from pathlib import Path

from PIL import Image, ImageSequence


def write_frame(frame, output_path):
    image = frame.convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox:
        image = image.crop(bbox)

    canvas = Image.new("RGBA", (360, 520), (0, 0, 0, 0))
    image.thumbnail((330, 500), Image.Resampling.LANCZOS)
    canvas.alpha_composite(image, ((canvas.width - image.width) // 2, canvas.height - image.height - 8))
    canvas.save(output_path)


def import_animation(source, action_name, max_frames=None):
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "assets" / "polar_bear" / "role" / "PolarBear" / "action"
    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as image:
        count = 0
        for index, frame in enumerate(ImageSequence.Iterator(image)):
            if max_frames is not None and index >= max_frames:
                break
            output_path = output_dir / f"{action_name}_{index:03d}.png"
            write_frame(frame, output_path)
            count += 1
    return count, output_dir


def main():
    parser = argparse.ArgumentParser(description="Import a GIF/WebP into the old-project PolarBear role format.")
    parser.add_argument("source", help="Animated GIF/WebP path.")
    parser.add_argument("action", help="Action prefix, such as idle, wave, walk_right, jump, sleep, drag.")
    parser.add_argument("--max-frames", type=int, default=None)
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"source not found: {source}")

    count, output_dir = import_animation(source, args.action, args.max_frames)
    print(f"imported {count} frames to {output_dir}")


if __name__ == "__main__":
    main()
