#!/usr/bin/env python3
# mindustry_img2mlog LIB
# by Candy & ChatGPT (lol)
# pip install pillow
#
# Пример:
#   python mindustry_img2mlog.py input.png --preset small-inner --upscale 2 --resample lanczos --colors 48 --out out --display display1
#   python mindustry_img2mlog.py input.png --preset large      --upscale 4 --resample bicubic --colors 64 --out out --display display1
#   + с wait:
#   python mindustry_img2mlog.py input.png --wait 0.1 --wait-every 10

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import io
from PIL import Image

RGBA = Tuple[int, int, int, int]

@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int
    color: RGBA


PRESETS = {
    "small-inner": (80, 80, 4),
    "small-full": (88, 88, 0),
    "large": (176, 176, 0),
}

RESAMPLE_MAP = {
    "nearest": Image.Resampling.NEAREST,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}


def parse_rgb(s: str) -> Tuple[int, int, int]:
    parts = s.split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("RGB должен быть в формате r,g,b")
    r, g, b = (int(p.strip()) for p in parts)
    for v in (r, g, b):
        if not (0 <= v <= 255):
            raise argparse.ArgumentTypeError("RGB значения должны быть 0..255")
    return r, g, b


def blend_over_bg(rgba: RGBA, bg: Tuple[int, int, int]) -> RGBA:
    r, g, b, a = rgba
    if a >= 255:
        return (r, g, b, 255)
    if a <= 0:
        return (bg[0], bg[1], bg[2], 255)
    af = a / 255.0
    nr = int(round(r * af + bg[0] * (1 - af)))
    ng = int(round(g * af + bg[1] * (1 - af)))
    nb = int(round(b * af + bg[2] * (1 - af)))
    return (nr, ng, nb, 255)

def load_and_prepare(
    path: str,
    blocks_w: int,
    blocks_h: int,
    resample: Image.Resampling,
    colors: Optional[int],
    bg: Tuple[int, int, int],
    alpha_threshold: int,
) -> List[List[Optional[RGBA]]]:
    img = Image.open(path).convert("RGBA")
    img = img.resize((blocks_w, blocks_h), resample=resample)

    if colors is not None:
        pal = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=colors)
        img = pal.convert("RGBA")

    px = img.load()
    grid: List[List[Optional[RGBA]]] = []
    for y in range(blocks_h):
        row: List[Optional[RGBA]] = []
        for x in range(blocks_w):
            rgba = px[x, y]
            if rgba[3] < alpha_threshold:
                row.append(None)
            else:
                row.append(blend_over_bg(rgba, bg))
        grid.append(row)
    return grid


def greedy_merge_rects(grid: List[List[Optional[RGBA]]]) -> List[Rect]:
    h = len(grid)
    w = len(grid[0]) if h else 0
    used = [[False] * w for _ in range(h)]
    rects: List[Rect] = []

    for y in range(h):
        for x in range(w):
            if used[y][x]:
                continue
            c = grid[y][x]
            if c is None:
                used[y][x] = True
                continue

            rw = 1
            while x + rw < w and (not used[y][x + rw]) and grid[y][x + rw] == c:
                rw += 1

            rh = 1
            while y + rh < h:
                ok = True
                for xx in range(x, x + rw):
                    if used[y + rh][xx] or grid[y + rh][xx] != c:
                        ok = False
                        break
                if not ok:
                    break
                rh += 1

            for yy in range(y, y + rh):
                for xx in range(x, x + rw):
                    used[yy][xx] = True

            rects.append(Rect(x=x, y=y, w=rw, h=rh, color=c))

    return rects


def rect_to_draw_commands(
    rect: Rect,
    blocks_h: int,
    upscale: int,
    margin: int,
) -> Tuple[int, int, int, int]:
    x_px = margin + rect.x * upscale
    y_px = margin + (blocks_h - (rect.y + rect.h)) * upscale
    w_px = rect.w * upscale
    h_px = rect.h * upscale
    return x_px, y_px, w_px, h_px


def emit_programs(
    rects: List[Rect],
    target_w: int,
    target_h: int,
    margin: int,
    upscale: int,
    bg: Tuple[int, int, int],
    display_name: str,
    max_lines: int,
    drawbuf_limit: int,
    include_stop: bool,
    wait_time: Optional[float] = None,
    wait_every: int = 10,
) -> List[str]:
    by_color: Dict[RGBA, List[Rect]] = {}
    for r in rects:
        by_color.setdefault(r.color, []).append(r)

    colors_sorted = sorted(by_color.keys())

    programs: List[List[str]] = []
    cur_lines: List[str] = []
    is_first_program = False

    draw_ops_in_buf = 0
    current_color: Optional[RGBA] = None

    lines_since_wait = 0

    def fmt_wait(t: float) -> str:
        s = f"{t:.6f}".rstrip("0").rstrip(".")
        return s if s else "0"

    def start_new_program():
        nonlocal cur_lines, is_first_program, draw_ops_in_buf, current_color, lines_since_wait
        cur_lines = []
        cur_lines.append(f"jump 2 notEqual display1 null")
        cur_lines.append(f"end")
        draw_ops_in_buf = 0
        current_color = None
        lines_since_wait = 0

        if is_first_program:
            r, g, b = bg
            cur_lines.append(f"draw clear {r} {g} {b} 0 0 0")
            draw_ops_in_buf += 1  

    def finalize_program():
        nonlocal cur_lines, draw_ops_in_buf, current_color, is_first_program
        cur_lines.append(f"drawflush {display_name}")
        draw_ops_in_buf = 0
        current_color = None

        if include_stop:
            cur_lines.append("stop")
        else:
            cur_lines.append("end")

        programs.append(cur_lines)
        is_first_program = False

    def ensure_space(extra_needed: int):
        nonlocal cur_lines
        if len(cur_lines) + extra_needed + 2 > max_lines:
            finalize_program()
            start_new_program()

    def add_line(s: str, *, count_for_wait: bool = True):
        nonlocal lines_since_wait, cur_lines

        extra = 1
        will_add_wait = (
            wait_time is not None
            and wait_time > 0
            and wait_every > 0
            and count_for_wait
            and (lines_since_wait + 1) >= wait_every
        )
        if will_add_wait:
            extra += 1

        ensure_space(extra)
        cur_lines.append(s)

        if (
            wait_time is not None
            and wait_time > 0
            and wait_every > 0
            and count_for_wait
        ):
            lines_since_wait += 1
            if lines_since_wait >= wait_every:
                cur_lines.append(f"wait {fmt_wait(wait_time)}")
                lines_since_wait = 0

    def flush_if_needed():
        nonlocal draw_ops_in_buf, current_color
        if draw_ops_in_buf >= drawbuf_limit:
            add_line(f"drawflush {display_name}", count_for_wait=True)
            draw_ops_in_buf = 0
            current_color = None

    start_new_program()

    blocks_w = target_w // upscale
    blocks_h = target_h // upscale
    _ = blocks_w  

    for color in colors_sorted:
        rect_list = by_color[color]

        ensure_space(2)

        flush_if_needed()

        if current_color != color:
            r, g, b, a = color
            add_line(f"draw color {r} {g} {b} {a} 0 0", count_for_wait=True)
            draw_ops_in_buf += 1
            current_color = color
            flush_if_needed()

        for rect in rect_list:
            ensure_space(2)

            flush_if_needed()
            if current_color != color:
                r, g, b, a = color      # Lib core generation.
                add_line(f"draw color {r} {g} {b} {a} 0 0", count_for_wait=True)
                draw_ops_in_buf += 1
                current_color = color
                flush_if_needed()

            x_px, y_px, w_px, h_px = rect_to_draw_commands(
                rect=rect,
                blocks_h=blocks_h,
                upscale=upscale,
                margin=margin,
            )
            add_line(f"draw rect {x_px} {y_px} {w_px} {h_px} 0 0", count_for_wait=True)
            draw_ops_in_buf += 1
            flush_if_needed()

    finalize_program()
    return ["\n".join(p) + "\n" for p in programs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="Путь к картинке")
    ap.add_argument("--preset", choices=sorted(PRESETS.keys()), default="small-inner")
    ap.add_argument("--upscale", type=int, default=2, help="Размер блока (N): rect будет N×N (или шире при склейке)")
    ap.add_argument("--resample", choices=sorted(RESAMPLE_MAP.keys()), default="lanczos")
    ap.add_argument("--colors", type=int, default=None, help="Квантование до N цветов (например 32..96). Сильно экономит команды.")
    ap.add_argument("--bg", type=parse_rgb, default=(0, 0, 0), help="Фон для clear и для смешивания альфы: r,g,b")
    ap.add_argument("--alpha-threshold", type=int, default=1, help="Пиксели с alpha < threshold пропускать (0..255)")
    ap.add_argument("--display", default="display1", help="Имя линка дисплея в процессоре (обычно display1)")
    ap.add_argument("--max-lines", type=int, default=1000, help="Лимит строк-инструкций на программу (обычно 1000)")
    ap.add_argument("--drawbuf-limit", type=int, default=240, help="Сколько draw-операций держать между drawflush (<=256)")
    ap.add_argument("--out", default="out_mlog", help="Папка для результата")
    ap.add_argument("--use-end", action="store_true", help="Вместо stop поставить end (перерисовывать по кругу)")

    ap.add_argument("--wait", type=float, default=None, help="Вставлять 'wait T' после каждых N строк (T в секундах). Например 0.1")
    ap.add_argument("--wait-every", type=int, default=10, help="N: через сколько строк вставлять wait (по умолчанию 10)")

    args = ap.parse_args()

    target_w, target_h, margin = PRESETS[args.preset]

    if target_w % args.upscale != 0 or target_h % args.upscale != 0:
        raise SystemExit("upscale должен делить размеры цели без остатка (например 80 при upscale=2/4/5 и т.п.)")

    blocks_w = target_w // args.upscale
    blocks_h = target_h // args.upscale

    resample = RESAMPLE_MAP[args.resample]

    grid = load_and_prepare(
        path=args.image,
        blocks_w=blocks_w,
        blocks_h=blocks_h,
        resample=resample,
        colors=args.colors,
        bg=args.bg,
        alpha_threshold=args.alpha_threshold,
    )

    rects = greedy_merge_rects(grid)

    programs = emit_programs(
        rects=rects,
        target_w=target_w,
        target_h=target_h,
        margin=margin,
        upscale=args.upscale,
        bg=args.bg,
        display_name=args.display,
        max_lines=args.max_lines,
        drawbuf_limit=args.drawbuf_limit,
        include_stop=(not args.use_end),
        wait_time=args.wait,
        wait_every=args.wait_every,
    )

    os.makedirs(args.out, exist_ok=True)
    for i, text in enumerate(programs, start=1):
        fname = os.path.join(args.out, f"prog_{i:02d}.mlog")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(text)

    print(f"Готово: {len(programs)} файл(а) в папке: {args.out}")
    for i in range(1, len(programs) + 1):
        print(f"  - prog_{i:02d}.mlog")


if __name__ == "__main__":
    main()
