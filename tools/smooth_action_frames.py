from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter


ACTION_DIR = Path(__file__).resolve().parents[1] / "assets" / "polar_bear" / "role" / "PolarBear" / "action"


def smooth_sequence(source_prefix: str, output_prefix: str, sharpen: float = 1.08) -> int:
    source_files = sorted(ACTION_DIR.glob(f"{source_prefix}_*.png"))
    if len(source_files) < 2:
        raise RuntimeError(f"Need at least 2 frames for {source_prefix}, got {len(source_files)}")

    source_images = [Image.open(path).convert("RGBA") for path in source_files]
    output_images = []
    for index, image in enumerate(source_images[:-1]):
        output_images.append(image)
        middle = Image.blend(image, source_images[index + 1], 0.5)
        if sharpen > 1:
            middle = middle.filter(ImageFilter.UnsharpMask(radius=0.8, percent=70, threshold=3))
            middle = ImageEnhance.Sharpness(middle).enhance(sharpen)
        output_images.append(middle)
    output_images.append(source_images[-1])

    for index, image in enumerate(output_images):
        image.save(ACTION_DIR / f"{output_prefix}_{index:03d}.png")

    print(f"{source_prefix} -> {output_prefix}: {len(source_files)} -> {len(output_images)} frames")
    return len(output_images)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create in-between frames for smoother polar bear actions.")
    parser.add_argument("source_prefix")
    parser.add_argument("output_prefix")
    parser.add_argument("--sharpen", type=float, default=1.08)
    args = parser.parse_args()
    smooth_sequence(args.source_prefix, args.output_prefix, args.sharpen)


if __name__ == "__main__":
    main()
