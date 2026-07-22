"""Convert the transparent snow-leopard source into compact vector-pixel data.

This is a development helper. The scheduled workflow only needs pixel_art.json,
so its runtime stays dependency-free.
"""

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "snow-leopard-pixel.png"
OUTPUT = ROOT / "pixel_art.json"
GRID_SIZE = 96
COLORS = 64
ALPHA_CUTOFF = 48


def main() -> None:
    source = Image.open(SOURCE).convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError("source image has no visible pixels")

    cropped = source.crop(bbox)
    cropped.thumbnail((GRID_SIZE, GRID_SIZE), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (GRID_SIZE, GRID_SIZE))
    offset = ((GRID_SIZE - cropped.width) // 2, (GRID_SIZE - cropped.height) // 2)
    canvas.alpha_composite(cropped, offset)

    rgb = Image.new("RGB", canvas.size)
    rgb.paste(canvas.convert("RGB"), mask=canvas.getchannel("A"))
    indexed = rgb.quantize(colors=COLORS, method=Image.Quantize.MAXCOVERAGE)
    palette_data = indexed.getpalette()
    used_indices = sorted(
        {
            indexed.getpixel((x, y))
            for y in range(GRID_SIZE)
            for x in range(GRID_SIZE)
            if canvas.getpixel((x, y))[3] >= ALPHA_CUTOFF
        }
    )
    index_map = {old: new for new, old in enumerate(used_indices)}
    palette = [
        "#{:02x}{:02x}{:02x}".format(*palette_data[old * 3 : old * 3 + 3])
        for old in used_indices
    ]

    rows: list[list[list[int]]] = []
    for y in range(GRID_SIZE):
        row: list[list[int]] = []
        x = 0
        while x < GRID_SIZE:
            if canvas.getpixel((x, y))[3] < ALPHA_CUTOFF:
                x += 1
                continue
            palette_index = index_map[indexed.getpixel((x, y))]
            start = x
            x += 1
            while (
                x < GRID_SIZE
                and canvas.getpixel((x, y))[3] >= ALPHA_CUTOFF
                and index_map[indexed.getpixel((x, y))] == palette_index
            ):
                x += 1
            row.append([start, x - start, palette_index])
        rows.append(row)

    payload = {
        "source": "user-provided snow leopard portrait",
        "width": GRID_SIZE,
        "height": GRID_SIZE,
        "palette": palette,
        "rows": rows,
    }
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    print(f"saved {OUTPUT} ({len(palette)} colors, {GRID_SIZE}x{GRID_SIZE})")


if __name__ == "__main__":
    main()
