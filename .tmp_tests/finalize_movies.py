#!/usr/bin/env python3
"""校验 5 部电影 + 改名入库 Movie/ + 删临时源"""
import os, subprocess, shutil

SRC = '/tmp/movie_dl'
DST = '/opt/data/Movie'

# 临时文件名 -> 目标文件名（中文.英文.年份）
MAPPING = {
    '[摔跤吧！爸爸].Dangal.2016.BluRay.1080p.x264.AC3-CMCT.mkv': '摔跤吧！爸爸.Dangal.2016.mkv',
    'Children.of.Heaven.1997.BluRay.1080p.x265.10bit.2Audio-MiniHD.mkv': '小鞋子.Children.of.Heaven.1997.mkv',
    'Les.choristes.2004.2160p.IQY.WEB-DL.H265.60fps.DDP5.1.2Audio-DreamHD.mkv': '放牛班的春天.Les.Choristes.2004.mkv',
    '心灵捕手.Good.Will.Hunting.1997.BluRay.1080p.HEVC.10bit.2Audio-MOMOHD.mkv': '心灵捕手.Good.Will.Hunting.1997.mkv',
    '3 Idiots 2009 BluRay REMUX 1080p AVC DTS-HD MA5.1 2Audio-DreamHD.mkv': '三傻大闹宝莱坞.3.Idiots.2009.mkv',
}

os.makedirs(DST, exist_ok=True)

for src_name, dst_name in MAPPING.items():
    src = os.path.join(SRC, src_name)
    dst = os.path.join(DST, dst_name)
    if not os.path.exists(src):
        print(f'❌ 源缺失: {src_name}')
        continue
    size = os.path.getsize(src)
    # ffprobe 时长
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1', src],
                       capture_output=True, text=True, timeout=120)
    dur = r.stdout.strip()
    # 字幕流
    r2 = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 's',
                         '-show_entries', 'stream=index,codec_name,title',
                         '-of', 'csv=p=0', src], capture_output=True, text=True, timeout=120)
    subs = r2.stdout.strip().replace('\n', ' | ')
    # 音轨数
    r3 = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a',
                         '-show_entries', 'stream=codec_name,title',
                         '-of', 'csv=p=0', src], capture_output=True, text=True, timeout=120)
    audios = r3.stdout.strip().replace('\n', ' | ')
    print(f'\n{src_name[:50]}...')
    print(f'  大小: {size/2**30:.2f}G 时长: {dur}s')
    print(f'  音轨: {audios[:80]}')
    print(f'  字幕流: {subs[:80] if subs else "无"}')
    if not dur or dur == 'N/A':
        print('  ❌ 时长校验失败，跳过')
        continue
    # 复制入库（跨文件系统）
    print(f'  📤 复制 → {dst_name}')
    shutil.copy2(src, dst)
    # 验证目标
    r4 = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                         '-of', 'default=noprint_wrappers=1:nokey=1', dst],
                        capture_output=True, text=True, timeout=120)
    if r4.stdout.strip() == dur and os.path.getsize(dst) == size:
        print(f'  ✅ 校验通过，删临时源')
        os.remove(src)
    else:
        print(f'  ⚠️ 目标校验不一致，保留临时源')
print('\nALL_DONE')
