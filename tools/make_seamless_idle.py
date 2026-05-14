from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


ACTION_DIR = Path(__file__).resolve().parents[1] / "assets" / "polar_bear" / "role" / "PolarBear" / "action"


def mean_rgb_diff(left: Path, right: Path) -> float:
    left_img = Image.open(left).convert("RGBA")
    right_img = Image.open(right).convert("RGBA")
    diff = ImageChops.difference(left_img, right_img)
    stat = ImageStat.Stat(diff)
    return sum(stat.mean[:3]) / 3


def make_pingpong_sequence(source_prefix: str, output_prefix: str) -> int:
    source_frames = sorted(ACTION_DIR.glob(f"{source_prefix}_*.png"))
    if len(source_frames) < 2:
        raise RuntimeError(f"Need at least 2 source frames for {source_prefix}, got {len(source_frames)}")

    sequence = source_frames + list(reversed(source_frames[1:-1]))
    for index, frame_path in enumerate(sequence):
        Image.open(frame_path).convert("RGBA").save(ACTION_DIR / f"{output_prefix}_{index:03d}.png")

    old_diff = mean_rgb_diff(source_frames[-1], source_frames[0])
    new_diff = mean_rgb_diff(ACTION_DIR / f"{output_prefix}_{len(sequence) - 1:03d}.png", ACTION_DIR / f"{output_prefix}_000.png")
    print(f"created={len(sequence)} prefix={output_prefix}")
    print(f"original_loop_mean_diff={old_diff:.2f}")
    print(f"new_loop_mean_diff={new_diff:.2f}")
    return len(sequence)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a seamless ping-pong idle sequence from existing PNG frames.")
    parser.add_argument("source_prefix", help="Existing frame prefix, for example video2528_idle_blink")
    parser.add_argument("output_prefix", help="New frame prefix, for example video2528_idle_seamless_v1")
    args = parser.parse_args()
    make_pingpong_sequence(args.source_prefix, args.output_prefix)


if __name__ == "__main__":
    main()
