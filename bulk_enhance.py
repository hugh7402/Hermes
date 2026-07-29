"""批量补增强：对缺少 tags 的笔记重新调用 note_enhance.py"""
import subprocess, os
from pathlib import Path

CONCEPTS = "/opt/data/Obsidian Vault/Obsidian Vault/concepts"

# 找出所有缺 tags 的笔记
unenhanced = []
for f in sorted(Path(CONCEPTS).glob("*.md")):
    content = f.read_text(encoding='utf-8')
    if "tags:" not in content[:500]:  # 只在开头搜 frontmatter
        unenhanced.append(f.name)

total = len(unenhanced)
print(f"📋 待增强: {total} 篇\n")

success = 0
fail = 0
for i, name in enumerate(unenhanced):
    pct = (i+1)/total*100
    print(f"[{i+1}/{total} {pct:.0f}%] {name[:60]}", flush=True)
    try:
        result = subprocess.run(
            ['python3', '/opt/data/note_enhance.py', name],
            cwd=CONCEPTS, timeout=300,
            capture_output=True, text=True
        )
        if result.returncode == 0 and '✅ 摘要' in result.stdout:
            success += 1
        elif '❌' in result.stdout or '💥' in result.stdout:
            fail += 1
            print(f"  ⚠️ {result.stdout.strip()[-120:]}")
        else:
            # partial success
            if '已保存' in result.stdout:
                success += 1
            else:
                fail += 1
    except subprocess.TimeoutExpired:
        fail += 1
        print(f"  ⏰ 超时跳过")
    except Exception as e:
        fail += 1
        print(f"  💥 {e}")

print(f"\n{'='*50}")
print(f"✅ 成功 {success}/{total}  |  ❌ 失败 {fail}/{total}")
