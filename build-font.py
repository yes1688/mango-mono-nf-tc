#!/usr/bin/env python3
"""
合成字型：Maple Mono NF（base TTF）+ Noto Sans CJK TC（CJK glyph 覆蓋）
策略：把 Noto 的 CJK CFF glyph 轉成 TTF quadratic，逐一植入 Maple Mono NF。

輸出：crates/hive-native-gui/assets/fonts/MapleMono-NF-TC-Regular.ttf

覆蓋 Unicode 範圍（Noto 優先）：
  U+2E80-U+2EFF  CJK Radicals Supplement
  U+2F00-U+2FDF  Kangxi Radicals
  U+3000-U+303F  CJK Symbols and Punctuation
  U+3040-U+309F  Hiragana
  U+30A0-U+30FF  Katakana
  U+3100-U+312F  Bopomofo
  U+31A0-U+31BF  Bopomofo Extended
  U+3400-U+4DBF  CJK Unified Ideographs Extension A
  U+4E00-U+9FFF  CJK Unified Ideographs
  U+F900-U+FAFF  CJK Compatibility Ideographs
  U+FE30-U+FE4F  CJK Compatibility Forms
  U+FF00-U+FFEF  Halfwidth and Fullwidth Forms
"""

import os
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.normpath(os.path.join(
    SCRIPT_DIR, "../crates/hive-native-gui/assets/fonts/MapleMono-NF-Regular.ttf"
))
NOTO_PATH = os.path.expanduser("~/Library/Fonts/NotoSansCJKtc-DemiLight.otf")
OUT_PATH = os.path.normpath(os.path.join(
    SCRIPT_DIR, "../crates/hive-native-gui/assets/fonts/MapleMono-NF-TC-Regular.ttf"
))

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


def main():
    print(f"載入 base TTF: {BASE_PATH}")
    base = TTFont(BASE_PATH)

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

    print(f"輸出：{OUT_PATH}")
    base.save(OUT_PATH)

    size_mb = os.path.getsize(OUT_PATH) / 1024 / 1024
    print(f"完成，檔案大小：{size_mb:.1f} MB")


if __name__ == "__main__":
    main()
