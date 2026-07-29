"""
批量 note_enhance — 自动扫描无标签笔记并批量处理
解决参数含空格/特殊字符的问题，使用 Python subprocess 逐批传参
"""
import sys, subprocess, time, yaml
from pathlib import Path

VAULT = Path("/opt/data/Obsidian Vault/Obsidian Vault/concepts")
BATCH_SIZE = 10
TIMEOUT = 120

def find_untagged():
    untagged = []
    for f in sorted(VAULT.glob("*.md")):
        c = f.read_text(encoding='utf-8')
        lines = c.split('\n')
        for i in range(1, len(lines)):
            if lines[i].rstrip() == '---':
                try:
                    fm = yaml.safe_load('\n'.join(lines[1:i])) or {}
                except:
                    fm = None
                if fm and not fm.get('tags'):
                    untagged.append(str(f))
                break
    return untagged

def main():
    files = find_untagged()
    total = len(files)
    if total == 0:
        print("✅ 全部已标记")
        return

    print(f"待处理 {total} 篇，每批 {BATCH_SIZE} 个\n")
    total_ok = 0

    for i in range(0, total, BATCH_SIZE):
        batch = files[i:i+BATCH_SIZE]
        print(f"--- 第 {i//BATCH_SIZE+1} 批 ({i+1}-{i+len(batch)}/{total}) ---")
        try:
            r = subprocess.run(
                [sys.executable, "/opt/data/note_enhance.py"] + batch,
                capture_output=True, text=True, timeout=TIMEOUT
            )
            ok = sum(1 for l in r.stdout.split('\n') if '已保存' in l)
            total_ok += ok
            for l in r.stdout.strip().split('\n')[-3:]:
                if l.strip():
                    print(f"  {l}")
        except subprocess.TimeoutExpired:
            print(f"  ⚠️ 超时，继续下一批")
        time.sleep(1)

    print(f"\n✅ 完成: {total_ok}/{total} 篇")

if __name__ == '__main__':
    main()
