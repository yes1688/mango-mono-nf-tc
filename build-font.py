#!/usr/bin/env python3
"""
合成字型：Maple Mono NF + Noto Sans CJK TC + NotoEmoji（text glyph）
輸出：crates/hive-native-gui/assets/fonts/MapleMono-NF-TC-Regular.ttf

Pass 1 — CJK（CFF→TTF quadratic via Cu2QuPen）：
  U+2E80-U+FFEF 含 CJK、Bopomofo、標點、全形

Pass 2 — Emoji text glyph（TTF→TTF 直接複製）：
  NotoEmoji-Regular.ttf（2020 text 版）所有 codepoint，
  不覆蓋 base 已有 glyph（Nerd Font icon 優先）。

Pass 3 — 技術符號補完（TTF→TTF 直接複製）：
  NotoSansSymbols2-Regular.ttf 植入技術符號、幾何圖形、媒體控制鍵等，
  避免 fallback 到 Apple Color Emoji。
  範圍：U+2300-27BF + U+1F7E0-1F7FF（不覆蓋 base 已有 glyph）。
"""

import os
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "../crates/hive-native-gui/assets/fonts"))
# 若 Regular 存在用它重建，否則以現有 TC 版直接加 emoji
_regular = os.path.join(FONTS_DIR, "MapleMono-NF-Regular.ttf")
_tc = os.path.join(FONTS_DIR, "MapleMono-NF-TC-Regular.ttf")
BASE_PATH = _regular if os.path.exists(_regular) else _tc
NOTO_PATH = os.path.expanduser("~/Library/Fonts/NotoSansCJKtc-DemiLight.otf")
EMOJI_PATH = os.path.join(FONTS_DIR, "NotoEmoji-Regular.ttf")
SYMBOLS2_PATH = os.path.join(FONTS_DIR, "NotoSansSymbols2-Regular.ttf")
OUT_PATH = os.path.join(FONTS_DIR, "MapleMono-NF-TC-Regular.ttf")

CJK_RANGES = [
    (0x2E80, 0x2EFF),
    (0x2F00, 0x2FDF),
    (0x3000, 0x303F),
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0x3100, 0x312F),
    (0x31A0, 0x31BF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0xFE30, 0xFE4F),
    (0xFF00, 0xFFEF),
]


def in_cjk(cp: int) -> bool:
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)


def _do_emoji_pass(base):
    """Pass 2：把 NotoEmoji text glyph（TTF outline）植入 base，不覆蓋已有 codepoint。"""
    print(f"載入 NotoEmoji text: {EMOJI_PATH}")
    emoji_font = TTFont(EMOJI_PATH)
    emoji_cmap = emoji_font.getBestCmap() or {}
    emoji_glyf = emoji_font["glyf"]
    emoji_hmtx = emoji_font["hmtx"]

    base_glyph_order = base.getGlyphOrder()
    base_glyf = base["glyf"]
    base_hmtx = base["hmtx"]
    best_cmap = base.getBestCmap() or {}
    base_cmap_table = base["cmap"]

    emoji_added = 0
    emoji_skipped = 0
    emoji_cps_added = []

    for cp, gname in sorted(emoji_cmap.items()):
        if cp in best_cmap:
            emoji_skipped += 1
            continue
        src_glyph = emoji_glyf.get(gname)
        if src_glyph is None:
            emoji_skipped += 1
            continue
        new_name = f"emoji_{gname}" if gname in base_glyph_order else gname
        base_glyph_order.append(new_name)
        base_glyf[new_name] = src_glyph
        if gname in emoji_hmtx.metrics:
            base_hmtx.metrics[new_name] = emoji_hmtx.metrics[gname]
        else:
            base_hmtx.metrics[new_name] = (base_hmtx.metrics.get("space", (500, 0))[0], 0)
        best_cmap[cp] = new_name
        emoji_cps_added.append(cp)
        emoji_added += 1

    print(f"Emoji 植入：{emoji_added}，跳過（已有/空）：{emoji_skipped}")

    bmp_updates = {cp: best_cmap[cp] for cp in emoji_cps_added if cp <= 0xFFFF}
    smp_updates = {cp: best_cmap[cp] for cp in emoji_cps_added if cp > 0xFFFF}

    fmt12_table = None
    for table in base_cmap_table.tables:
        if table.isUnicode():
            if table.format == 4:
                table.cmap.update(bmp_updates)
            elif table.format == 12:
                table.cmap.update(bmp_updates)
                table.cmap.update(smp_updates)
                fmt12_table = table

    # format 12 がなければ追加（SMP emoji 用）
    if fmt12_table is None and smp_updates:
        from fontTools.ttLib.tables import _c_m_a_p as cmap_mod
        new_table = cmap_mod.cmap_format_12(12)
        new_table.platEncID = 3
        new_table.platformID = 3
        new_table.language = 0
        new_table.cmap = dict(best_cmap)
        base_cmap_table.tables.append(new_table)
        print(f"新增 cmap format 12（SMP emoji {len(smp_updates)} 個）")

    base.setGlyphOrder(base_glyph_order)


SYMBOLS2_RANGES = [
    (0x2300, 0x23FF),   # Miscellaneous Technical（媒體控制鍵 ⏱⏺⏵ 等）
    (0x2400, 0x243F),   # Control Pictures
    (0x2440, 0x245F),   # OCR
    (0x2460, 0x24FF),   # Enclosed Alphanumerics
    (0x2500, 0x257F),   # Box Drawing
    (0x2580, 0x259F),   # Block Elements
    (0x25A0, 0x25FF),   # Geometric Shapes
    (0x2600, 0x26FF),   # Miscellaneous Symbols（補 NotoEmoji 沒覆蓋的）
    (0x2700, 0x27BF),   # Dingbats
    (0x1F7E0, 0x1F7FF), # Geometric Shapes Extended（彩色圓圈）
]


def in_symbols2_range(cp: int) -> bool:
    return any(lo <= cp <= hi for lo, hi in SYMBOLS2_RANGES)


def _do_symbols2_pass(base):
    """Pass 3：把 NotoSansSymbols2 技術符號植入 base，不覆蓋已有 codepoint。"""
    print(f"載入 NotoSansSymbols2: {SYMBOLS2_PATH}")
    sym2_font = TTFont(SYMBOLS2_PATH)
    sym2_cmap = sym2_font.getBestCmap() or {}
    sym2_glyf = sym2_font["glyf"]
    sym2_hmtx = sym2_font["hmtx"]

    base_glyph_order = base.getGlyphOrder()
    base_glyf = base["glyf"]
    base_hmtx = base["hmtx"]
    best_cmap = base.getBestCmap() or {}
    base_cmap_table = base["cmap"]

    added = 0
    skipped = 0
    cps_added = []

    for cp, gname in sorted(sym2_cmap.items()):
        if not in_symbols2_range(cp):
            continue
        if cp in best_cmap:
            skipped += 1
            continue
        src_glyph = sym2_glyf.get(gname)
        if src_glyph is None:
            skipped += 1
            continue
        new_name = f"sym2_{gname}" if gname in base_glyph_order else gname
        base_glyph_order.append(new_name)
        base_glyf[new_name] = src_glyph
        if gname in sym2_hmtx.metrics:
            base_hmtx.metrics[new_name] = sym2_hmtx.metrics[gname]
        else:
            base_hmtx.metrics[new_name] = (base_hmtx.metrics.get("space", (500, 0))[0], 0)
        best_cmap[cp] = new_name
        cps_added.append(cp)
        added += 1

    print(f"Symbols2 植入：{added}，跳過（已有/空/範圍外）：{skipped}")

    bmp_updates = {cp: best_cmap[cp] for cp in cps_added if cp <= 0xFFFF}
    smp_updates = {cp: best_cmap[cp] for cp in cps_added if cp > 0xFFFF}

    fmt12_table = None
    for table in base_cmap_table.tables:
        if table.isUnicode():
            if table.format == 4:
                table.cmap.update(bmp_updates)
            elif table.format == 12:
                table.cmap.update(bmp_updates)
                table.cmap.update(smp_updates)
                fmt12_table = table

    if fmt12_table is None and smp_updates:
        from fontTools.ttLib.tables import _c_m_a_p as cmap_mod
        new_table = cmap_mod.cmap_format_12(12)
        new_table.platEncID = 3
        new_table.platformID = 3
        new_table.language = 0
        new_table.cmap = dict(best_cmap)
        base_cmap_table.tables.append(new_table)
        print(f"新增 cmap format 12（SMP symbols {len(smp_updates)} 個）")

    base.setGlyphOrder(base_glyph_order)


def main():
    print(f"載入 base TTF: {BASE_PATH}")
    base = TTFont(BASE_PATH)

    # 若 base 已是 TC 版（含 CJK），跳過 Pass 1 直接做 Pass 2+3
    base_is_tc = BASE_PATH == _tc
    if base_is_tc:
        print("base 已是 TC 版，跳過 Pass 1 CJK 植入")
        _do_emoji_pass(base)
        _do_symbols2_pass(base)
        print(f"輸出：{OUT_PATH}")
        base.save(OUT_PATH)
        size_mb = os.path.getsize(OUT_PATH) / 1024 / 1024
        print(f"完成，檔案大小：{size_mb:.1f} MB")
        return

    print(f"載入 Noto CJK: {NOTO_PATH}")
    noto = TTFont(NOTO_PATH)

    noto_cmap = noto.getBestCmap() or {}
    base_cmap_table = base["cmap"]

    # 取 base 最佳 cmap（Unicode BMP）
    best_cmap = base.getBestCmap() or {}

    # 篩出 Noto 有、在 CJK 範圍的 codepoint（base 已有的也覆蓋）
    cjk_cps = sorted(cp for cp in noto_cmap if in_cjk(cp))
    print(f"Noto CJK codepoint 數：{len(cjk_cps)}")

    noto_glyph_set = noto.getGlyphSet()
    base_glyf = base["glyf"]
    base_hmtx = base["hmtx"]
    base_glyph_order = base.getGlyphOrder()

    # 避免 glyph name 衝突：Noto CID 字型名稱形如 cid00001，重命名為 noto_cid00001
    noto_glyph_order = noto.getGlyphOrder()
    name_map = {}  # noto 原名 → base 內的新名
    for g in noto_glyph_order:
        new_name = f"noto_{g}" if g in base_glyph_order else g
        name_map[g] = new_name

    added = 0
    skipped_empty = 0

    for cp in cjk_cps:
        noto_name = noto_cmap[cp]
        new_name = name_map.get(noto_name, noto_name)

        # 如果已經植入這個 glyph，只更新 cmap
        if new_name in base_glyph_order:
            best_cmap[cp] = new_name
            continue

        # 取 Noto glyph（CFF）
        src = noto_glyph_set.get(noto_name)
        if src is None:
            skipped_empty += 1
            continue

        # CFF (cubic) → TTF (quadratic) 轉換
        tt_pen = TTGlyphPen(base)
        cu2qu_pen = Cu2QuPen(tt_pen, max_err=1.0, reverse_direction=True)
        try:
            src.draw(cu2qu_pen)
            glyph = tt_pen.glyph()
        except Exception as e:
            skipped_empty += 1
            continue

        if glyph is None:
            skipped_empty += 1
            continue

        # 植入 base
        base_glyph_order.append(new_name)
        base_glyf[new_name] = glyph

        # hmtx：用 Noto 的 advance width
        noto_hmtx = noto["hmtx"]
        if noto_name in noto_hmtx.metrics:
            base_hmtx.metrics[new_name] = noto_hmtx.metrics[noto_name]
        else:
            base_hmtx.metrics[new_name] = (base["hmtx"].metrics.get("space", (500, 0))[0], 0)

        best_cmap[cp] = new_name
        added += 1

    print(f"植入 glyph：{added}，跳過空 glyph：{skipped_empty}")

    # 更新所有 Unicode cmap subtable
    for table in base_cmap_table.tables:
        if table.isUnicode():
            table.cmap.update({cp: best_cmap[cp] for cp in cjk_cps if cp in best_cmap})

    # 更新 GlyphOrder
    base.setGlyphOrder(base_glyph_order)

    # ── Pass 2：植入 NotoEmoji text glyph ────────────────────────────────────
    _do_emoji_pass(base)

    # ── Pass 3：植入 Noto Sans Symbols2 技術符號 ─────────────────────────────
    _do_symbols2_pass(base)

    print(f"輸出：{OUT_PATH}")
    base.save(OUT_PATH)
    size_mb = os.path.getsize(OUT_PATH) / 1024 / 1024
    print(f"完成，檔案大小：{size_mb:.1f} MB")


if __name__ == "__main__":
    main()
