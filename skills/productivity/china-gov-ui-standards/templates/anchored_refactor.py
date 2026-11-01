#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""锚点式批量改稿骨架 —— 改原型源码（或任何生成物）时用它，别手工逐处编辑。

为什么必须这样改（两个真实事故）：
  ① 用"在锚点前插入"改生成的 DOM → 旧块没删掉 → 面板 DOM 重复（两个 id="dbgbox"）
     （getElementById 只取第一个，第二个默默堆在页面上，肉眼不看根本不发现）
  ② 替换锚点没命中却静默跳过 → 日志只少一行，看日志会以为改完了

核心原则：**锚点对不上就当场炸掉**。每个替换必须断言「存在」且「唯一」。

用法：copy 本文件 → 按第 1、2 节填锚点 → 跑 → 看 `✓ N 处` 是否与你预期一致。
改多类文件时拆成 2~3 个脚本（壳 / 屏幕 / 文档），每个脚本独立断言。
"""
import pathlib
import sys

# ── 1. 目标文件 ──────────────────────────────────────────────────
TARGET = pathlib.Path('/path/to/proto/src/app.js')
s = TARGET.read_text(encoding='utf-8')
ORIG_LEN = len(s)
n_edits = 0


# ── 2. 两个原语 ──────────────────────────────────────────────────
def rep(old, new, label):
    """精确替换，要求锚点存在且唯一。删内容就传 new=''。"""
    global s, n_edits
    assert old in s, f'❌ 锚点未找到：{label}\n   期望片段：{old[:100]!r}'
    assert s.count(old) == 1, f'❌ 锚点不唯一（{s.count(old)} 处）：{label}'
    s = s.replace(old, new, 1)
    n_edits += 1
    print(f'  ✓ {label}')


def cut(start_marker, end_marker, new, label):
    """把 start_marker..end_marker（不含 end）整段换成 new —— 替换整个代码块时用。
    比 rep() 适合长块：不用把几百行原文粘进脚本。"""
    global s, n_edits
    i = s.find(start_marker)
    j = s.find(end_marker)
    assert i >= 0, f'❌ 起点未找到：{label}'
    assert j > i, f'❌ 终点未找到或顺序错：{label}'
    s = s[:i] + new + s[j:]
    n_edits += 1
    print(f'  ✓ {label}')


def check(cond, msg):
    """改完后的自检（如：旧名必须 0 命中、新名必须出现 N 次）。"""
    if cond:
        print(f'  ✅ {msg}')
    else:
        print(f'  ❌ {msg}')
        sys.exit(3)


# ── 3. 改动条目（下面换成你自己的）──────────────────────────────
print('① 顶部导航')
rep('<div class="sysname">' + "' + esc(sys.name) + '" + '</div>', '', '删除重复的系统名')

print('\n② 整块替换（示例）')
cut('  /* ── 旧的进度条数组', '  /* ── 屏幕 → 元信息',
    '  /* 新的分段结构 */\n', '进度条数组改为按系统分段')

# ── 4. 落盘前自检（关键：改名 / 删实体后必须收尾 grep）─────────
for gone in ('切换到其他系统', '一数一源一标准治理系统'):
    check(gone not in s, f'旧文案已清零：{gone}')

TARGET.write_text(s, encoding='utf-8')
print(f'\n✅ {TARGET.name} 完成 {n_edits} 处修改  {ORIG_LEN} → {len(s)} 字节')

# ── 5. 下一步别忘了（顺序不能乱）─────────────────────────────
#   ① 重建 → 构建门禁（node --check 语法 + 敏感词合规）必须过
#   ② 跑全套测试 → 逐条判定失败是「真 bug」还是「过时断言」
#      鉴别法：先读实际运行时值，再决定改代码还是改断言
#   ③ 交付物改名/加版本号 → 同步 build/package/测试脚本/文档 四处
