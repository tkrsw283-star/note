"""
eyecatch.py: note記事用アイキャッチ画像を生成
出力サイズ: 1280 x 670 px（note推奨）
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 670

# カラーパレット
BG          = (22, 38, 84)       # ネイビー
BG_DARK     = (14, 24, 58)       # より濃いネイビー（右パネル）
GOLD        = (245, 172, 40)     # ゴールド
GOLD_DARK   = (160, 100, 10)     # 濃いゴールド（バッジ文字）
BLUE_LIGHT  = (100, 160, 230)    # ライトブルー
WHITE       = (255, 255, 255)
ORANGE      = (220, 85, 40)      # オレンジ（著者バッジ）
GRAY_LIGHT  = (180, 205, 235)    # 薄いブルーグレー（サブテキスト）

_FONT_PATH = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"


def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for ch in text:
        test = cur + ch
        w = draw.textbbox((0, 0), test, font=font)[2]
        if w > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def _draw_badge(draw: ImageDraw.ImageDraw, text: str, font, x: int, y: int,
                fill, text_fill, pad_x: int = 20, pad_y: int = 10, radius: int = 8):
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.rounded_rectangle(
        [(x, y), (x + tw + pad_x * 2, y + th + pad_y * 2)],
        radius=radius, fill=fill,
    )
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=text_fill)
    return tw + pad_x * 2, th + pad_y * 2


def generate_eyecatch(topic_idea: dict, draft_path: Path) -> Path:
    """記事メタデータからアイキャッチ画像を生成して eyecatch/ に保存"""
    title  = topic_idea.get("title", "無題")
    price  = topic_idea.get("price", 500)
    target = topic_idea.get("target", "")

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ── 背景レイアウト ─────────────────────────────────────────
    # 右パネル（濃いネイビー）
    RIGHT_PANEL_X = W - 300
    draw.rectangle([(RIGHT_PANEL_X, 0), (W, H)], fill=BG_DARK)

    # 左ゴールドライン
    draw.rectangle([(0, 0), (10, H)], fill=GOLD)

    # 上部ライトブルーライン
    draw.rectangle([(0, 0), (W, 5)], fill=BLUE_LIGHT)

    # 下部ゴールドライン
    draw.rectangle([(0, H - 8), (W, H)], fill=GOLD)

    # 右パネル内の装飾円
    for cx, cy, r, opacity in [(RIGHT_PANEL_X + 150, 180, 110, 18),
                                (RIGHT_PANEL_X + 60,  500, 70,  14),
                                (RIGHT_PANEL_X + 250, 420, 55,  12)]:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                   fill=(*BLUE_LIGHT, opacity))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

    # ── 著者バッジ ─────────────────────────────────────────────
    badge_font = _font(26)
    _draw_badge(draw, "現役大学職員が執筆", badge_font,
                x=30, y=35, fill=ORANGE, text_fill=WHITE, pad_x=18, pad_y=9)

    # ── メインタイトル ─────────────────────────────────────────
    TITLE_LEFT  = 30
    TITLE_RIGHT = RIGHT_PANEL_X - 30
    TITLE_MAX_W = TITLE_RIGHT - TITLE_LEFT

    title_font = _font(60)
    lines = _wrap(draw, title, title_font, TITLE_MAX_W)

    if len(lines) > 3:
        title_font = _font(46)
        lines = _wrap(draw, title, title_font, TITLE_MAX_W)

    line_h    = title_font.size + 16
    total_h   = line_h * len(lines)
    y_title   = (H - total_h) // 2 - 10

    for i, line in enumerate(lines):
        y = y_title + i * line_h
        # ドロップシャドウ
        draw.text((TITLE_LEFT + 3, y + 3), line, font=title_font, fill=(0, 0, 0))
        draw.text((TITLE_LEFT,     y),     line, font=title_font, fill=WHITE)

    # ── 価格バッジ ─────────────────────────────────────────────
    price_label_font = _font(22)
    price_value_font = _font(44)
    label_text = "有料記事"
    price_text = f"¥{price:,}"

    lb = draw.textbbox((0, 0), label_text, font=price_label_font)
    pb = draw.textbbox((0, 0), price_text,  font=price_value_font)
    badge_w = max(pb[2] - pb[0], lb[2] - lb[0]) + 40
    badge_h = (lb[3] - lb[1]) + (pb[3] - pb[1]) + 40
    bx, by  = 30, H - badge_h - 40

    draw.rounded_rectangle([(bx, by), (bx + badge_w, by + badge_h)],
                           radius=10, fill=GOLD)
    draw.text((bx + 20, by + 12), label_text, font=price_label_font, fill=GOLD_DARK)
    draw.text((bx + 20, by + 12 + (lb[3] - lb[1]) + 6),
              price_text, font=price_value_font, fill=GOLD_DARK)

    # ── ターゲット読者 ─────────────────────────────────────────
    if target:
        tgt_font  = _font(23)
        tgt_short = target[:28] + ("…" if len(target) > 28 else "")
        tx = bx + badge_w + 24
        ty = H - draw.textbbox((0, 0), tgt_short, font=tgt_font)[3] - 46
        draw.text((tx, ty), f"対象: {tgt_short}", font=tgt_font, fill=GRAY_LIGHT)

    # ── 右パネル：noteロゴ風 + 装飾 ───────────────────────────
    note_font = _font(56)
    note_bb   = draw.textbbox((0, 0), "note", font=note_font)
    note_x    = RIGHT_PANEL_X + (300 - (note_bb[2] - note_bb[0])) // 2
    draw.text((note_x, H // 2 - 50), "note", font=note_font, fill=GOLD)

    sep_font = _font(20)
    sep_text = "有料記事"
    sep_bb   = draw.textbbox((0, 0), sep_text, font=sep_font)
    sep_x    = RIGHT_PANEL_X + (300 - (sep_bb[2] - sep_bb[0])) // 2
    draw.text((sep_x, H // 2 + 20), sep_text, font=sep_font, fill=GRAY_LIGHT)

    # ── 保存 ───────────────────────────────────────────────────
    out_dir = Path("eyecatch")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{draft_path.stem}.png"
    img.save(out_path, "PNG", optimize=True)
    return out_path
