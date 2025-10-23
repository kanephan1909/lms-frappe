from googletrans import Translator
import re

# Đường dẫn file gốc và file xuất ra
input_file = "main.pot"              # đổi thành đường dẫn file .po của bạn
output_file = "vi_translated.po"  # file xuất kết quả

translator = Translator()

# Đọc file
with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

translated_lines = []
current_msgid = None
inside_msgid = False

for line in lines:
    if line.startswith("msgid "):
        inside_msgid = True
        current_msgid = re.findall(r'^msgid "(.*)"', line)
        if current_msgid:
            text = current_msgid[0]
            if text.strip():
                try:
                    result = translator.translate(text, src="en", dest="vi")
                    translated = result.text.replace('"', '\\"')
                except Exception as e:
                    translated = text
                translated_lines.append(f'msgid "{text}"\n')
                translated_lines.append(f'msgstr "{translated}"\n')
                continue
    if line.startswith("msgstr") and not inside_msgid:
        continue
    if not line.startswith("msgid") and not line.startswith("msgstr"):
        inside_msgid = False
        translated_lines.append(line)

# Ghi file dịch
with open(output_file, "w", encoding="utf-8") as f:
    f.writelines(translated_lines)

print(f"File đã được dịch và lưu tại: {output_file}")
