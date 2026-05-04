"""Generate a neutral 200x200 placeholder cover for the audiobook library."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    out = Path(__file__).resolve().parent / "default_cover.png"
    img = Image.new("RGB", (200, 200), color=(64, 64, 68))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, 160, 160], outline=(120, 120, 128), width=3)
    draw.line([40, 200, 200, 40], fill=(90, 90, 96), width=2)
    img.save(out, format="PNG")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
