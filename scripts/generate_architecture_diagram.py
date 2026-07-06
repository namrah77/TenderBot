"""Generate TenderBot architecture_diagram.png (16:9, exact labels)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "assets" / "architecture_diagram.png"

# Palette
BG = (0x1A, 0x1F, 0x2B)
TEXT = (0xF0, 0xED, 0xE6)
AMBER = (0xD4, 0xA0, 0x54)
TEAL = (0x4A, 0x9B, 0x8E)
ORANGE = (0xC9, 0x7B, 0x4A)
NODE_FILL = (0x22, 0x28, 0x38)
MCP_FILL = (0x1E, 0x2A, 0x32)
MCP_INNER = (0x15, 0x1C, 0x24)

W, H = 1920, 1080


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill,
    outline=None,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color,
    width: int = 3,
) -> None:
    draw.line([start, end], fill=color, width=width)
    import math

    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head = 12
    left = (
        end[0] - head * math.cos(angle - math.pi / 7),
        end[1] - head * math.sin(angle - math.pi / 7),
    )
    right = (
        end[0] - head * math.cos(angle + math.pi / 7),
        end[1] - head * math.sin(angle + math.pi / 7),
    )
    draw.polygon([end, left, right], fill=color)


def draw_bidirectional(
    draw: ImageDraw.ImageDraw,
    left: tuple[int, int],
    right: tuple[int, int],
    color,
) -> None:
    mid_y = left[1]
    draw.line([(left[0], mid_y), (right[0], mid_y)], fill=color, width=3)
    draw_arrow(draw, (left[0] + 28, mid_y), (left[0] + 8, mid_y), color, width=3)
    draw_arrow(draw, (right[0] - 28, mid_y), (right[0] - 8, mid_y), color, width=3)


def draw_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    pos: tuple[int, int],
    font,
    color=TEXT,
    anchor: str = "mm",
) -> None:
    draw.text(pos, text, fill=color, font=font, anchor=anchor)


def draw_node(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    title: str,
    role: str,
    *,
    border=AMBER,
    width: int = 360,
    height: int = 72,
    title_font,
    role_font,
) -> tuple[int, int, int, int]:
    x0, y0 = cx - width // 2, cy - height // 2
    x1, y1 = x0 + width, y0 + height
    rounded_rect(draw, (x0, y0, x1, y1), 14, NODE_FILL, outline=border, width=2)
    draw.text((cx, cy - 12), title, fill=TEXT, font=title_font, anchor="mm")
    draw.text((cx, cy + 16), role, fill=(0xC8, 0xC4, 0xBC), font=role_font, anchor="mm")
    return x0, y0, x1, y1


def draw_watermark(base: Image.Image) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = 170, H - 120
    scale = 2.2
    house = [
        (cx, cy - 40 * scale),
        (cx - 36 * scale, cy - 8 * scale),
        (cx - 36 * scale, cy + 28 * scale),
        (cx + 36 * scale, cy + 28 * scale),
        (cx + 36 * scale, cy - 8 * scale),
    ]
    d.polygon(house, outline=(AMBER[0], AMBER[1], AMBER[2], 28), fill=(AMBER[0], AMBER[1], AMBER[2], 12))
    d.rectangle(
        (cx - 14 * scale, cy + 4 * scale, cx + 14 * scale, cy + 28 * scale),
        fill=(TEAL[0], TEAL[1], TEAL[2], 18),
    )
    heart = [
        (cx, cy + 6 * scale),
        (cx - 10 * scale, cy - 4 * scale),
        (cx, cy - 18 * scale),
        (cx + 10 * scale, cy - 4 * scale),
    ]
    d.polygon(heart, fill=(TEAL[0], TEAL[1], TEAL[2], 22))
    base.alpha_composite(layer)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    title_font = load_font(44, bold=True)
    subtitle_font = load_font(22)
    node_title_font = load_font(20, bold=True)
    node_role_font = load_font(15)
    label_font = load_font(14)
    small_font = load_font(13)
    mcp_header_font = load_font(18, bold=True)
    mcp_body_font = load_font(17)

    draw.text((W // 2, 52), "The professional AI agent workflow", fill=TEXT, font=title_font, anchor="mm")
    draw.text(
        (W // 2, 96),
        "TenderBot - a UK care-sector tender intelligence system",
        fill=(*TEXT[:3],),
        font=subtitle_font,
        anchor="mm",
    )

    cx = 520
    gap = 88
    y0 = 190

    nodes = [
        ("Security Checkpoint", "Checks incoming data", ORANGE),
        ("Company Profiler", "Scrapes company website", AMBER),
        ("Tender Discovery", "Searches UK tender portals", AMBER),
        ("Tender Crawler", "Extracts notice requirements", AMBER),
        ("Eligibility Checker", "Scores 8 mandatory criteria", AMBER),
        ("Evaluation Agent", "Reliability self-review score", AMBER),
        ("Report Generator", "Produces bid readiness report", AMBER),
    ]

    boxes: list[tuple[int, int, int, int]] = []
    centers: list[tuple[int, int]] = []
    for i, (title, role, border) in enumerate(nodes):
        cy = y0 + i * gap
        box = draw_node(
            draw,
            cx,
            cy,
            title,
            role,
            border=border,
            title_font=node_title_font,
            role_font=node_role_font,
        )
        boxes.append(box)
        centers.append((cx, cy))

    sec_box = boxes[0]
    end_w, end_h = 92, 44
    end_x = sec_box[2] + 130
    end_y = centers[0][1]
    end_box = (end_x - end_w // 2, end_y - end_h // 2, end_x + end_w // 2, end_y + end_h // 2)
    rounded_rect(draw, end_box, 10, (0x3A, 0x22, 0x1E), outline=ORANGE, width=2)
    draw.text((end_x, end_y), "END", fill=TEXT, font=node_title_font, anchor="mm")

    draw_arrow(draw, (sec_box[2], centers[0][1]), (end_box[0], end_y), ORANGE, width=3)
    mid_x = (sec_box[2] + end_box[0]) // 2
    draw_label(draw, "injection detected", (mid_x, end_y - 18), label_font, color=ORANGE)

    draw_arrow(draw, (sec_box[0] - 70, centers[0][1]), (sec_box[0], centers[0][1]), TEAL, width=3)
    draw_label(draw, "Data", (sec_box[0] - 95, centers[0][1] - 18), label_font, color=TEAL)

    for i in range(len(centers) - 1):
        y_from = boxes[i][3]
        y_to = boxes[i + 1][1]
        draw_arrow(draw, (cx, y_from), (cx, y_to), TEAL, width=3)
        if i == 0:
            draw_label(draw, "clean", (cx + 52, (y_from + y_to) // 2), label_font, color=TEAL, anchor="lm")

    mcp_x0, mcp_y0 = 1280, 610
    mcp_x1, mcp_y1 = 1760, 860
    rounded_rect(draw, (mcp_x0, mcp_y0, mcp_x1, mcp_y1), 16, MCP_FILL, outline=TEAL, width=2)
    header_h = 46
    draw.rectangle((mcp_x0 + 2, mcp_y0 + 2, mcp_x1 - 2, mcp_y0 + header_h), fill=TEAL)
    draw.text(((mcp_x0 + mcp_x1) // 2, mcp_y0 + header_h // 2 + 1), "MCP Server", fill=BG, font=mcp_header_font, anchor="mm")
    inner = (mcp_x0 + 18, mcp_y0 + header_h + 16, mcp_x1 - 18, mcp_y1 - 18)
    rounded_rect(draw, inner, 12, MCP_INNER, outline=(0x2E, 0x3E, 0x46), width=1)
    tool_y = inner[1] + 52
    draw.text((inner[0] + 28, tool_y), "1. save_report", fill=TEXT, font=mcp_body_font, anchor="lm")
    draw.text((inner[0] + 28, tool_y + 42), "2. save_report_to_drive", fill=TEXT, font=mcp_body_font, anchor="lm")

    report_box = boxes[-1]
    report_cy = centers[-1][1]
    draw_bidirectional(draw, (report_box[2] + 8, report_cy), (mcp_x0 - 8, report_cy + 20), TEAL)

    rgba = img.convert("RGBA")
    draw_watermark(rgba)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rgba.convert("RGB").save(OUT, format="PNG", optimize=True)
    print(f"Saved {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
