# MapleMono-NF-TC

Maple Mono NF + Noto Sans CJK TC — 台灣標準字形的等寬開發字型。

## 字型組成

| 部分 | 來源 | 授權 |
|------|------|------|
| 英文等寬 + Ligature | [Maple Mono](https://github.com/subframe7536/maple-font) v7.9 | OFL-1.1 |
| CJK 繁體中文（台灣標準） | [Noto Sans CJK TC](https://github.com/googlefonts/noto-cjk) DemiLight | OFL-1.1 |
| Nerd Font Icon | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) | MIT |

## 特色

- 英文字形舒適寬敞（Maple Mono 原創設計）
- CJK 使用台灣教育部標準字形（非 GB 18030 / CN 標準）
- Nerd Font icon 齊全（開發工具 icon）
- 中英文寬度 2:1 對齊
- 單一 .ttf，跨平台零設定

## 建置

需要 Python 3 + fontTools：

```bash
pip install fonttools cu2qu
python build-font.py
```

輸入檔：
- `MapleMono-NF-Regular.ttf` — Maple Mono NF base（本 repo 附帶）
- `~/Library/Fonts/NotoSansCJKtc-DemiLight.otf` — Noto CJK TC（需自行安裝）

輸出：`MapleMono-NF-TC-Regular.ttf`

## 授權

本合成字型遵循 [SIL Open Font License 1.1](LICENSE)。
原始字型的著作權歸各自作者所有。
