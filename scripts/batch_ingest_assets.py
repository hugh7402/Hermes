"""
数据资产文件合集 - 分批入库脚本（cron友好版）
每次处理5个文件，干净退出，由cron调度反复执行
"""
import sys, os, subprocess, hashlib, re, time
from pathlib import Path
from datetime import datetime

BACKUP_DIR = "/opt/data/WebChat BackUp/文档/数据资产文件合集"
VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"
CONCEPTS = f"{VAULT}/concepts"
PROCESSED_LOG = f"{VAULT}/.ingested"
PER_RUN = 7  # 每次处理7个，配合cron均匀分配
TIMEOUT_PER_FILE = 600  # 单个最长10分钟

def get_processed():
    processed = set()
    if os.path.exists(PROCESSED_LOG):
        with open(PROCESSED_LOG) as f:
            for line in f:
                processed.add(line.strip())
    return processed

def file_hash(filepath):
    return hashlib.md5(Path(filepath).read_bytes()).hexdigest()

def convert_text(filepath):
    """文本提取，扫描件走OCR"""
    ext = Path(filepath).suffix.lower()
    fname = Path(filepath).name
    
    try:
        if ext == '.pdf':
            r1 = subprocess.run(
                ['uv', 'run', '--with', 'pymupdf', 'python3', '-c', f'''
import fitz
doc = fitz.open("{filepath}")
text = [page.get_text() for page in doc]
print("---PAGEBREAK---".join(text))
'''],
                capture_output=True, text=True, timeout=60
            )
            text = r1.stdout.strip()
            
            if len(text) < 50:
                print(f"  📸 OCR ({fname})...", flush=True)
                r2 = subprocess.run(
                    ['/opt/hermes/.venv/bin/python3', '/opt/data/pdf_ocr.py', filepath],
                    capture_output=True, text=True, timeout=TIMEOUT_PER_FILE
                )
                if r2.returncode == 0 and r2.stdout.strip():
                    text = r2.stdout.strip()
                else:
                    return None, f"OCR failed"
            return text, None
            
        elif ext == '.docx':
            r = subprocess.run(
                ['uv', 'run', '--with', 'python-docx', 'python3', '-c', f'''
import docx
doc = docx.Document("{filepath}")
text = []
for p in doc.paragraphs:
    if p.style.name.startswith("Heading"):
        level = int(p.style.name.split()[-1]) if p.style.name.split()[-1].isdigit() else 1
        text.append("#" * level + " " + p.text)
    else:
        text.append(p.text)
print("\\\\n".join(text))
'''],
                capture_output=True, text=True, timeout=60
            )
            return r.stdout.strip(), None
    except subprocess.TimeoutExpired:
        return None, f"超时>{TIMEOUT_PER_FILE}s"
    except Exception as e:
        return None, str(e)
    
    return None, "unsupported format"

def save_and_enhance(text, filename):
    """保存markdown并增强"""
    safe_name = filename.rsplit('.', 1)[0] + '.md'
    out_path = os.path.join(CONCEPTS, safe_name)
    
    content = f"# {Path(filename).stem}\n\n"
    content += f"> **原始文件**：{filename}\n\n---\n\n{text}\n"
    
    Path(out_path).write_text(content, encoding='utf-8')
    
    print(f"  🤖 增强...", flush=True)
    subprocess.run(
        ['python3', '/opt/data/note_enhance.py', str(out_path)],
        capture_output=True, text=True, timeout=300
    )
    
    return out_path

def main():
    processed_hashes = get_processed()
    
    # 收集文件
    all_files = []
    for ext in ['.pdf', '.docx']:
        all_files.extend(sorted(Path(BACKUP_DIR).glob(f'**/*{ext}')))
    
    # 去重
    unprocessed = []
    for f in all_files:
        h = file_hash(str(f))
        if h not in processed_hashes:
            unprocessed.append((str(f), h))
    
    total = len(unprocessed)
    if total == 0:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] ✅ 所有文件已入库！")
        return
    
    batch = unprocessed[:PER_RUN]
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] "
          f"待处理 {total} 个，本次处理 {len(batch)} 个", flush=True)
    
    success = 0
    for filepath, h in batch:
        fname = Path(filepath).name
        print(f"\n📄 {fname}", flush=True)
        
        text, err = convert_text(filepath)
        if text and len(text.strip()) > 10:
            save_and_enhance(text, Path(filepath).name)
            with open(PROCESSED_LOG, 'a') as f:
                f.write(f"{h}\n")
            success += 1
            print(f"  ✅ 完成", flush=True)
        else:
            print(f"  ⏭️ 跳过: {err or '内容为空'}", flush=True)
            # 空内容也记hash防重复尝试
            with open(PROCESSED_LOG, 'a') as f:
                f.write(f"{h}\n")
        
        time.sleep(2)
    
    remaining = total - len(batch)
    print(f"\n✅ 本次入库 {success}/{len(batch)} 篇，剩余 ~{remaining} 篇", flush=True)
    if remaining > 0:
        estimated_runs = (remaining + PER_RUN - 1) // PER_RUN
        print(f"📊 预计还需 {estimated_runs} 次执行", flush=True)

if __name__ == '__main__':
    main()
