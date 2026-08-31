#!/usr/bin/env python3
"""收尾：JUR-794 字幕改名 + MIDA-693 字幕检查 + 本地 13 个视频完整性核对"""
import os, subprocess

INBOX = '/opt/data/PikPak/Inbox-JAV'

# 1. JUR-794 字幕改名
s_src = os.path.join(INBOX, 'jur-794.srt')
s_dst = os.path.join(INBOX, 'JUR-794-一乃葵-多P轮奸中出 被恶毒婆婆卖给其他男人们玩弄并当着儿子面被轮奸中出的美尻美乳人妻.srt')
if os.path.exists(s_src) and not os.path.exists(s_dst):
    os.rename(s_src, s_dst)
    print(f'📝 JUR-794 字幕改名完成 ({os.path.getsize(s_dst)}B)')
elif os.path.exists(s_src):
    print('⚠️ JUR-794 字幕目标已存在')

# 2. MIDA-693 字幕检查（16B 空壳？）
mida_sub = os.path.join(INBOX, 'MIDA-693-天宮花南-多P轮奸中出 被同事轮奸中出并调教成肉便器的极品尤物OL.srt')
if os.path.exists(mida_sub):
    sz = os.path.getsize(mida_sub)
    with open(mida_sub, 'rb') as f:
        head = f.read(100)
    print(f'MIDA-693 字幕: {sz}B 内容开头: {head[:60]!r}')
    if sz < 100:
        print('  ❌ 空壳字幕，删除（稍后重下）')
        os.remove(mida_sub)
else:
    print('MIDA-693 无字幕')

# 3. 本地 13 个视频完整性核对
expected = [
    'HMN-896-愛花未滿-多P轮奸中出 被高薪职位诱骗被下药后被轮奸中出的极品尤物.mp4',
    'IPZZ-925-瀬緒凛-多P轮奸中出 被社长强奸调教并被轮奸中出的极品尤物前台小姐.mp4',
    'JUR-794-一乃葵-多P轮奸中出 被恶毒婆婆卖给其他男人们玩弄并当着儿子面被轮奸中出的美尻美乳人妻.mp4',
    'GARA-025-逢沢-多P乱伦轮奸 和公公同住被公公强奸并带人一起轮奸的美尻人妻.mp4',
    'IPZZ-901-三澄寧々-多P轮奸 被其他写真女星嫉妒雇人轮奸的极品尤物写真女明星.mp4',
    'IPZZ-914-堀北桃愛-多P轮奸 在学校游泳课后自慰被发现胁迫被轮奸的极品美胸女学生.mp4',
    'JUR-837-三比菜々美-单P强奸NTR 同是老师的丈夫殴打学生，为保护丈夫只能被不良学生当众强奸玩弄的美胸人妻教师.mp4',
    'DLDSS-525-与田りん-多P轮奸中出 在摄影棚被同事轮奸中出的美尻女气象主持人.mp4',
    'JUFE-628-持野蓬-多P轮奸中出 在美容院被恶德按摩师下药按摩挑逗到高潮并强奸诱奸后上瘾被轮奸中出的极品尤物.mp4',
    'CAWB-025-浅海-多P轮奸中出 被打工新同事庆祝被灌醉后轮奸中出的美尻店员.mp4',
    'DVMM-415-依本-多P轮奸中出 参加同学会被灌醉后被轮奸中出的极品美尻少妇.mp4',
    'IPZZ-879-山田鈴奈-多P轮媚药奸 参加同学Party被用强力媚药被轮奸玩弄到天亮的极品美尻女大学生.mp4',
    'MIDA-693-天宮花南-多P轮奸中出 被同事轮奸中出并调教成肉便器的极品尤物OL.mp4',
]
print(f'\n本地完整性核对（期望 {len(expected)} 个）:')
allok = True
for name in expected:
    fp = os.path.join(INBOX, name)
    if os.path.exists(fp):
        dur = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                              '-of', 'default=noprint_wrappers=1:nokey=1', fp],
                             capture_output=True, text=True, timeout=90).stdout.strip()
        ok = '✅' if dur else '❌ 损坏'
        if not dur:
            allok = False
        print(f'  {ok} {name[:45]}... ({os.path.getsize(fp)/2**30:.2f}G dur={dur[:8]})')
    else:
        print(f'  ❌ 缺失: {name[:45]}')
        allok = False
print(f'\n结果: {"全部完整 ✅" if allok else "有缺失 ❌"}')
