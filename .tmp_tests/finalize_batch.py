#!/usr/bin/env python3
"""批量处理：校验 /tmp/dl2 文件 → 按用户后缀复制到 Inbox-JAV → 删临时 → 字幕改名"""
import os, subprocess, sys

DL2 = '/tmp/dl2'
INBOX = '/opt/data/PikPak/Inbox-JAV'

# 临时文件名 -> 目标文件名（用户指定后缀）；None = 已存在跳过
MAPPING = {
    'CAWB-025.mp4': 'CAWB-025-浅海-多P轮奸中出 被打工新同事庆祝被灌醉后轮奸中出的美尻店员.mp4',
    'DLDSS-525.mp4': 'DLDSS-525-与田りん-多P轮奸中出 在摄影棚被同事轮奸中出的美尻女气象主持人.mp4',
    'DVMM-415-C.mp4': 'DVMM-415-依本-多P轮奸中出 参加同学会被灌醉后被轮奸中出的极品美尻少妇.mp4',
    'GARA-025.mp4': 'GARA-025-逢沢-多P乱伦轮奸 和公公同住被公公强奸并带人一起轮奸的美尻人妻.mp4',
    'HMN-896-愛花未滿-多P轮奸中出 被高薪职位诱骗被下药后被轮奸中出的极品尤物.mp4': None,
    'IPZZ-879-C.mp4': 'IPZZ-879-山田鈴奈-多P轮媚药奸 参加同学Party被用强力媚药被轮奸玩弄到天亮的极品美尻女大学生.mp4',
    'IPZZ-901-U.mp4': 'IPZZ-901-三澄寧々-多P轮奸 被其他写真女星嫉妒雇人轮奸的极品尤物写真女明星.mp4',
    'IPZZ-914.mp4': 'IPZZ-914-堀北桃愛-多P轮奸 在学校游泳课后自慰被发现胁迫被轮奸的极品美胸女学生.mp4',
    'IPZZ-925-瀬緒凛-多P轮奸中出 被社长强奸调教并被轮奸中出的极品尤物前台小姐.mp4': 'IPZZ-925-瀬緒凛-多P轮奸中出 被社长强奸调教并被轮奸中出的极品尤物前台小姐.mp4',
    'JUFE-628.mp4': 'JUFE-628-持野蓬-多P轮奸中出 在美容院被恶德按摩师下药按摩挑逗到高潮并强奸诱奸后上瘾被轮奸中出的极品尤物.mp4',
    'JUR-794.mp4': 'JUR-794-一乃葵-多P轮奸中出 被恶毒婆婆卖给其他男人们玩弄并当着儿子面被轮奸中出的美尻美乳人妻.mp4',
    'MIDA-693.mp4': 'MIDA-693-天宮花南-多P轮奸中出 被同事轮奸中出并调教成肉便器的极品尤物OL.mp4',
}

def ffprobe_dur(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1', p],
                       capture_output=True, text=True, timeout=90)
    return r.stdout.strip()

ok = 0
for src, dst in MAPPING.items():
    p = os.path.join(DL2, src)
    if not os.path.exists(p):
        print(f'⚠️ 缺失: {src}')
        continue
    dur = ffprobe_dur(p)
    size = os.path.getsize(p)
    print(f'{src}: {size/2**30:.2f}GB dur={dur}')
    if not dur or dur == 'N/A':
        print(f'  ❌ 损坏，跳过')
        continue
    if dst is None:
        print(f'  ⏭️ 本地已存在，跳过搬入（仅校验）')
        ok += 1
        continue
    dst_path = os.path.join(INBOX, dst)
    if os.path.exists(dst_path) and os.path.getsize(dst_path) == size:
        print(f'  ⏭️ 目标已存在且大小一致，跳过复制')
        os.remove(p)
        ok += 1
        continue
    print(f'  📤 复制 → {dst}')
    r2 = subprocess.run(['cp', p, dst_path], timeout=900)
    if r2.returncode != 0:
        print(f'  ❌ 复制失败 rc={r2.returncode}')
        continue
    dur2 = ffprobe_dur(dst_path)
    if dur2 and os.path.getsize(dst_path) == size:
        print(f'  ✅ 校验通过（dur={dur2}），删临时')
        os.remove(p)
        ok += 1
    else:
        print(f'  ❌ 目标校验失败 dur2={dur2}')

# 字幕改名（与视频同名）
SUB_MAP = {
    'JUR-794.srt': 'JUR-794-一乃葵-多P轮奸中出 被恶毒婆婆卖给其他男人们玩弄并当着儿子面被轮奸中出的美尻美乳人妻.srt',
    'IPZZ-914.srt': 'IPZZ-914-堀北桃愛-多P轮奸 在学校游泳课后自慰被发现胁迫被轮奸的极品美胸女学生.srt',
    'MIDA-693.srt': 'MIDA-693-天宮花南-多P轮奸中出 被同事轮奸中出并调教成肉便器的极品尤物OL.srt',
}
for s_src, s_dst in SUB_MAP.items():
    sp = os.path.join(INBOX, s_src)
    if os.path.exists(sp):
        dp = os.path.join(INBOX, s_dst)
        if not os.path.exists(dp):
            os.rename(sp, dp)
            print(f'📝 字幕改名: {s_src} → {s_dst}')
        else:
            print(f'📝 字幕目标已存在: {s_dst}')
    else:
        print(f'📝 未找到字幕: {s_src}')

print(f'DONE ok={ok}/{len(MAPPING)}')
