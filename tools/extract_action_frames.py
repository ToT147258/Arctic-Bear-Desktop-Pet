import argparse
from pathlib import Path

from PIL import Image, ImageSequence


def extract_frames(source, output_dir, prefix, max_frames=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        for index, frame in enumerate(ImageSequence.Iterator(image)):
            if max_frames is not None and index >= max_frames:
                break
            rgba = frame.convert("RGBA")
            rgba.save(output_dir / f"{prefix}_{index:03d}.png")
    return index + 1


def main():
    parser = argparse.ArgumentParser(description="Extract GIF/WebP action frames for the polar bear desktop pet.")
    parser.add_argument("source", help="Path to an animated GIF/WebP file.")
    parser.add_argument("action", help="Action name, for example idle, wave, walk_right, sleep.")
    parser.add_argument("--max-frames", type=int, default=None)
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"source not found: {source}")

    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "assets" / "polar_bear" / "actions" / args.action
    count = extract_frames(source, output_dir, args.action, args.max_frames)
    print(f"extracted {count} frames to {output_dir}")


if __name__ == "__main__":
    main()
