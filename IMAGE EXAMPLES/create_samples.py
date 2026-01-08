from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


SIZES = [80, 128, 256, 512]

PALETTE = [
    (0, 0, 0),         # black
    (255, 255, 255),   # white 
    (220, 20, 60),     # crimson
    (34, 139, 34),     # forest green
    (30, 144, 255),    # dodger blue
    (255, 215, 0),     # gold
    (255, 140, 0),     # dark orange
    (138, 43, 226),    # blue violet
    (0, 206, 209),     # dark turquoise
    (128, 128, 128),   # gray
]

LAT_UP = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LAT_LO = "abcdefghijklmnopqrstuvwxyz"
CYR_UP = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
CYR_LO = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
DIGITS = "0123456789"

ALL_CHARS = LAT_UP + LAT_LO + CYR_UP + CYR_LO + DIGITS


def find_font_path() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\arialuni.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def wrap_by_pixels(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_w: int) -> list[str]:
    lines = []
    buf = ""
    for ch in text:
        test = buf + ch
        w = draw.textlength(test, font=font)
        if w <= max_w or not buf:
            buf = test
        else:
            lines.append(buf)
            buf = ch
    if buf:
        lines.append(buf)
    return lines


def make_image(size: int, out_dir: Path):
    img = Image.new("RGB", (size, size), (255, 255, 255))
    d = ImageDraw.Draw(img)

    margin = max(2, size // 64)
    palette_h = max(10, size // 8) 
    text_top = palette_h + margin

    sw = (size - 2 * margin) / len(PALETTE)
    x = margin
    for i, color in enumerate(PALETTE):
        x0 = int(round(x))
        x1 = int(round(margin + (i + 1) * sw))
        y0 = margin
        y1 = palette_h
        d.rectangle([x0, y0, x1, y1], fill=color)
        d.rectangle([x0, y0, x1, y1], outline=(0, 0, 0))
        x += sw

    font_path = find_font_path()
    base_size = max(6, size // 14)

    if font_path:
        def load(sz): return ImageFont.truetype(font_path, sz)
    else:
        def load(sz): return ImageFont.load_default()

    available_w = size - 2 * margin
    available_h = size - text_top - margin

    available_h = max(1, available_h)

    chosen_font = load(base_size)
    lines = []

    for fs in range(base_size, 3, -1):  
        font = load(fs)
        lines_try = wrap_by_pixels(d, ALL_CHARS, font, available_w)
        bbox = d.textbbox((0, 0), "Ag", font=font)
        line_h = (bbox[3] - bbox[1]) + 1
        total_h = line_h * len(lines_try)

        if total_h <= available_h:
            chosen_font = font
            lines = lines_try
            break

    if not lines:
        chosen_font = load(4)
        lines = wrap_by_pixels(d, ALL_CHARS, chosen_font, available_w)

    bbox = d.textbbox((0, 0), "Ag", font=chosen_font)
    line_h = (bbox[3] - bbox[1]) + 1

    y = text_top
    for line in lines:
        if y + line_h > size - margin:
            break
        d.text((margin, y), line, font=chosen_font, fill=(0, 0, 0))
        y += line_h

    d.rectangle([0, 0, size - 1, size - 1], outline=(0, 0, 0))

    out_path = out_dir / f"example_{size}x{size}.png"
    img.save(out_path, "PNG")
    print("Saved:", out_path)


def main():
    out_dir = Path("out_examples")
    out_dir.mkdir(parents=True, exist_ok=True)

    for s in SIZES:
        make_image(s, out_dir)


if __name__ == "__main__":
    main()
