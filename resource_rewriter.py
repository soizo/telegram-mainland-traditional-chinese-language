import os, re, json, sys, codecs

TG_DIR = os.path.dirname(os.path.abspath(__file__))
S2MT_DIR = os.environ["S2MT_DIR"]
INPUT_DIR  = os.path.join(TG_DIR, 'input')
OUTPUT_DIR = os.path.join(TG_DIR, 'output')
RULES_JSON = os.path.join(TG_DIR, 'TelegramMTPhrases.json')

def read_text_with_encoding(path):
    # 自動偵測 BOM：UTF-8/UTF-16（LE/BE），否則嘗試 UTF-8
    with open(path, 'rb') as f:
        raw = f.read()
    encoding = 'utf-8'
    if raw.startswith(codecs.BOM_UTF8):
        encoding = 'utf-8-sig'
    elif raw.startswith(codecs.BOM_UTF16_LE) or raw.startswith(codecs.BOM_UTF16_BE):
        encoding = 'utf-16'
    try:
        text = raw.decode(encoding)
        return text, encoding
    except Exception:
        # 退回嘗試常見編碼
        for enc in ('utf-8', 'utf-16', 'utf-8-sig', 'gb18030'):
            try:
                return raw.decode(enc), enc
            except Exception:
                pass
        # 最後保底：以替換錯誤方式解
        return raw.decode('utf-8', errors='replace'), 'utf-8'

def write_text_with_encoding(path, text, encoding):
    # 維持原始編碼；若是 utf-16，讓 Python 自行包含 BOM
    if encoding == 'utf-16':
        with open(path, 'wb') as f:
            f.write(codecs.BOM_UTF16_LE)  # 預設用 LE BOM
            f.write(text.encode('utf-16-le'))
    elif encoding == 'utf-8-sig':
        with open(path, 'wb') as f:
            f.write(codecs.BOM_UTF8)
            f.write(text.encode('utf-8'))
    else:
        with open(path, 'w', encoding=encoding, newline='') as f:
            f.write(text)

def apply_xml_replacement(content, key, pattern, substitution):
    # 同時支援 name="key" 與 name='key'；僅替換 <string name=...>value</string> 的 value
    tag_re = re.compile(
        r'(<string\b[^>]*\bname\s*=\s*([\'"])' + re.escape(key) + r'\2[^>]*>)(.*?)(</string>)',
        flags=re.DOTALL
    )
    def do_sub(m):
        before, val, after = m.group(1), m.group(3), m.group(4)
        new_val = re.sub(pattern, substitution, val, flags=re.DOTALL)
        return before + new_val + after
    new_content, count = tag_re.subn(do_sub, content)
    return new_content, count

def apply_strings_replacement(content, key, pattern, substitution):
    # 僅替換 "key" = "value"; 的 value（允許空白與可選分號）
    line_re = re.compile(
        r'(^\s*"' + re.escape(key) + r'"\s*=\s*")'   # 開頭+key+等號+開引號
        r'((?:\\.|[^"\\])*)'                         # value（支援跳脫）
        r'(";\s*$)',                                 # 收尾
        flags=re.MULTILINE
    )
    def do_sub(m):
        prefix, val, suffix = m.group(1), m.group(2), m.group(3)
        new_val = re.sub(pattern, substitution, val, flags=re.DOTALL)
        return prefix + new_val + suffix
    new_content, count = line_re.subn(do_sub, content)
    return new_content, count

def list_files(dirpath):
    try:
        return [f for f in os.listdir(dirpath) if os.path.isfile(os.path.join(dirpath, f))]
    except FileNotFoundError:
        return []

# 讀 JSON 規則
with open(RULES_JSON, 'r', encoding='utf-8') as f:
    try:
        rules = json.load(f)
    except Exception as e:
        print(f"❌  解析 TelegramMTPhrases.json 失敗：{e}", file=sys.stderr)
        sys.exit(2)

all_input_files = list_files(INPUT_DIR)
if not all_input_files:
    print("⚠️  input 為空，無檔可處理。")

total_changed_files = 0

for idx, item in enumerate(rules, 1):
    if not isinstance(item, dict):
        print(f"⚠️  規則第 {idx} 項不是物件，略過。")
        continue

    # 每個 item 只有一個「檔名正則」鍵
    for filename_regex, spec in item.items():
        try:
            file_pat = re.compile(filename_regex)
        except Exception as e:
            print(f"⚠️  檔名正則無效：{filename_regex} ({e})，略過。")
            continue

        # 找到 input 中匹配的檔案
        matched = [fn for fn in all_input_files if file_pat.fullmatch(fn)]
        if not matched:
            print(f"ℹ️  無匹配檔案：{filename_regex}（略過）")
            continue

        # 規則可能是空物件（表示不需替換）
        if not spec or not isinstance(spec, dict) or 'Type' not in spec or 'Replacements' not in spec:
            print(f"ℹ️  規則 {filename_regex} 未提供 Type/Replacements，僅複製不改動。")
            continue

        ftype = str(spec.get('Type', '')).strip().lower()
        repls = spec.get('Replacements') or []

        for fn in matched:
            in_path  = os.path.join(INPUT_DIR, fn)
            out_path = os.path.join(OUTPUT_DIR, fn)

            text, enc = read_text_with_encoding(in_path)
            orig_text = text
            per_file_changes = 0

            if ftype == 'xml':
                for r in repls:
                    targets = r.get('Target') or []
                    pattern = r.get('pattern', '')
                    subs    = r.get('substitution', '')
                    if not targets:
                        continue
                    for key in targets:
                        new_text, c = apply_xml_replacement(text, key, pattern, subs)
                        if c == 0:
                            print(f"   · 未找到 XML <string name=\"{key}\"> 的值於檔案 {fn}")
                        text = new_text
                        per_file_changes += c

            elif ftype == 'strings':
                for r in repls:
                    targets = r.get('Target') or []
                    pattern = r.get('pattern', '')
                    subs    = r.get('substitution', '')
                    if not targets:
                        continue
                    for key in targets:
                        new_text, c = apply_strings_replacement(text, key, pattern, subs)
                        if c == 0:
                            print(f"   · 未找到 .strings key \"{key}\" 的值於檔案 {fn}")
                        text = new_text
                        per_file_changes += c
            else:
                print(f"⚠️  不支援的 Type：{spec.get('Type')}（檔案 {fn}），略過替換。")
                continue

            # 寫回（即使無改動也覆寫，確保 output 完整）
            write_text_with_encoding(out_path, text, enc)

            if per_file_changes > 0:
                total_changed_files += 1
                print(f"✅  已處理 {fn}：套用 {per_file_changes} 處替換")
            else:
                print(f"➖  已檢查 {fn}：無符合替換")

print(f"\n🎉 完成。共更新 {total_changed_files} 個檔案。")