# Telegram Mainland Traditional Chinese Language
電報大陸繁體中文語言

將 Telegram 各平台的簡體中文語言包，轉換為大陸慣用繁體中文（即：繁體字形 + 大陸用語習慣）。

## 支援平台

- Android
- iOS
- macOS
- Desktop (tdesktop)
- Unigram (Windows/UWP)
- Web (weba / webk)

## 依賴項

- Python 3
- [OpenCC](https://github.com/BYVoid/OpenCC)（需可在命令列執行 `opencc`）
- [OpenCC-Mainland-Traditional-Chinese](https://github.com/soizo/OpenCC-Mainland-Traditional-Chinese)（S2MT 詞庫，見下方設定）

## 目錄結構

```
.
├── process.sh              # 主批次處理腳本
├── resource_rewriter.py    # Python 替換腳本（處理 XML / .strings 格式）
├── TelegramMTPhrases.json  # 針對 Telegram 各平台的正則替換規則
├── s2mt4TG.json            # OpenCC 自訂轉換設定
├── Phrases.txt             # 本地詞語覆蓋表（TSV，簡體→大陸繁體）
├── Characters.txt          # 本地字符覆蓋表（TSV，簡體→大陸繁體）
├── input/                  # 放入待轉換的原始語言檔（git 忽略）
└── output/                 # 轉換完成的輸出檔（git 忽略）
```

## 使用方法

### 1. 設定 S2MT_DIR

在腳本頂端或環境變數中設定 `S2MT_DIR` 為 [OpenCC-Mainland-Traditional-Chinese](https://github.com/soizo/OpenCC-Mainland-Traditional-Chinese) 倉庫內 `s2mt/` 的路徑：

```sh
export S2MT_DIR="/path/to/OpenCC-Mainland-Traditional-Chinese/s2mt"
```

或直接修改 `process.sh` 第 8 行的預設路徑。

### 2. 放入語言檔

將 Telegram 官方下載的簡體中文語言檔放入 `input/` 目錄。

### 3. 執行

```sh
bash process.sh
```

腳本會依序：

1. 將 `input/` 複製到 `output/`
2. 執行 `resource_rewriter.py`，套用 `TelegramMTPhrases.json` 的正則替換
3. 合併 S2MT 詞庫與本地 `Phrases.txt` / `Characters.txt`，生成 `Result_Phrases.txt` / `Result_Characters.txt`
4. 對 `output/` 內所有檔案執行兩段 OpenCC 轉換（繁化 + 大陸用語）

## 自訂詞語

- `Phrases.txt`：詞語級別的覆蓋，格式為 `簡體\t大陸繁體`（每行一條，`#` 開頭為注釋）
- `Characters.txt`：字符級別的覆蓋，格式相同

本地覆蓋表的優先順序高於 S2MT 詞庫（相同 key 以本地最後一條為準）。

## 授權

Apache License 2.0
