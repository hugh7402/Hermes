"""清理 OCR 输出：去掉 <|LOC_N|> 定位标记和空段落，生成可入库 md"""
import re

src = '/tmp/embodied_full.txt'
text = open(src, encoding='utf-8').read()

# 1. 去掉 <|LOC_数字|> 定位标记
text = re.sub(r'<\|LOC_\d+\|>', '', text)
# 2. 去掉其他 <|...|> 残留
text = re.sub(r'<\|[^|]*\|>', '', text)
# 3. 清理空行堆积（3个以上换行压成2个）
text = re.sub(r'\n{3,}', '\n\n', text)
# 4. 清理每行尾部空白
text = '\n'.join(l.rstrip() for l in text.split('\n'))
# 5. 去掉纯空白行前的多余分隔
lines = [l for l in text.split('\n') if l.strip()]
text = '\n'.join(lines)

out = '/tmp/embodied_clean.txt'
open(out, 'w', encoding='utf-8').write(text)
print(f'清理后字数: {len(text)}')
print(f'残留LOC标记: {len(re.findall(r"<\|", text))}')
print(f'输出: {out}')
