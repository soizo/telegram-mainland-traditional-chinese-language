#!/usr/bin/env bash
set -euo pipefail

# -------------------------
# 基本路徑與前置檢查
# -------------------------
TG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
S2MT_DIR="$HOME/Documents/GHAEP/opencc/OpenCC-Mainland-Traditional-Chinese/s2mt"
INPUT_DIR="$TG_DIR/input"
OUTPUT_DIR="$TG_DIR/output"
RULES_JSON="$TG_DIR/TelegramMTPhrases.json"
SMT_DIR="$TG_DIR/SMT"  # 放置被扒下來的檔

if [[ ! -d "$INPUT_DIR" ]]; then
  echo "錯誤：找不到 input 資料夾：$INPUT_DIR" >&2
  exit 1
fi

if [[ ! -f "$RULES_JSON" ]]; then
  echo "錯誤：找不到規則檔 TelegramMTPhrases.json：$RULES_JSON" >&2
  exit 1
fi

if [[ ! -d "$S2MT_DIR" ]]; then
  echo "錯誤：找不到 S2MT 目錄：$S2MT_DIR" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
mkdir -p "$SMT_DIR"

# -------------------------
# 從 S2MT_DIR 扒標準詞/字表 → 本地 SMT 夾（覆蓋）
# -------------------------
echo "➡️  從 S2MT_DIR 複製詞/字表到 SMT/（覆蓋）"
for f in "SMTPhrases.txt" "SMTCharacters.txt"; do
  src="$S2MT_DIR/$f"
  dst="$SMT_DIR/$f"
  if [[ ! -f "$src" ]]; then
    echo "錯誤：找不到來源檔：$src" >&2
    exit 1
  fi
  cp -f "$src" "$dst"
  echo "📥 已覆蓋 $dst"
done

# -------------------------
# 清空 output（移到擸㩑桶）
# -------------------------
echo "➡️  清空 output：把舊檔移到擸㩑桶(~/.Trash)"
find "$OUTPUT_DIR" -mindepth 1 -maxdepth 1 -exec mv -f {} "$HOME/.Trash/" \; || true

# -------------------------
# 複製 input → output（未改動的先完整複製過去）
# -------------------------
echo "➡️  複製 input → output"
rsync -a --delete-excluded "$INPUT_DIR"/ "$OUTPUT_DIR"/

# -------------------------
# 進入 Python 真正處理替換
# 將 S2MT_DIR 路徑傳入 Python（環境變數）
# -------------------------
export S2MT_DIR
/usr/bin/env python3 "$TG_DIR/resource_rewriter.py"

echo "全部處理完成。輸出位於：$OUTPUT_DIR"

# -------------------------
# 合併 TSV（相同 key 僅保留最後一次）
# -------------------------
merge_kv_unique () {
  local SRC1="$1" SRC2="$2" TARGET="$3"

  awk -F '\t' '
    BEGIN{OFS="\t"}
    {
      buf[++n] = $0
      type[n] = "other"
      if ($0 ~ /^# / || NF==0) next
      if (NF >= 2) {
        key = $1
        type[n] = "kv"
        last[key] = n
        keys[n] = key
      }
    }
    END{
      for (i=1; i<=n; i++) {
        if (type[i] == "kv") {
          k = keys[i]
          if (last[k] == i) print buf[i]
        } else {
          print buf[i]
        }
      }
    }
  ' "$SRC1" "$SRC2" > "$TARGET"
}

# 使用 S2MT_DIR 的原始表 + 本地 Phrases/Characters 合併出結果
TARGET="$TG_DIR/Result_Phrases.txt"
SRC1="$S2MT_DIR/SMTPhrases.txt"
SRC2="$TG_DIR/Phrases.txt"
merge_kv_unique "$SRC1" "$SRC2" "$TARGET"
echo "✅ 已生成或更新：$TARGET"

TARGET="$TG_DIR/Result_Characters.txt"
SRC1="$S2MT_DIR/SMTCharacters.txt"
SRC2="$TG_DIR/Characters.txt"
merge_kv_unique "$SRC1" "$SRC2" "$TARGET"
echo "✅ 已生成或更新：$TARGET"
echo "opencc 處理中..."

# -------------------------
# 對 output 內所有檔進行 OpenCC 兩段轉換
# -------------------------
for f in "$TG_DIR"/output/*; do
    [[ -e "$f" ]] || continue
    filename=$(basename "$f")
    tmp="$TG_DIR/output/${filename}.tmp"
    opencc -i "$f" -o "$tmp" -c t2s.json
    opencc -i "$tmp" -o "$TG_DIR/output/$filename" -c "$TG_DIR/s2mt4TG.json"
    rm "$tmp"
    echo "✅ $filename 完成雙重轉換"
done

echo "opencc 處理完成"