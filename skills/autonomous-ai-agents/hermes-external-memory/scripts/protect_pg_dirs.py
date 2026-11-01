#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""治本：防止 disk-cleanup 插件删除 Hindsight 的 PG 空目录（幂等，可反复跑）。

根因（2026-10-10 用插件日志坐实）：
  disk-cleanup 插件 `_EMPTY_DIR_PROTECTED_TOP_LEVEL` 白名单不含 `.pg0`/`.hindsight`，
  每轮清理从 HERMES_HOME 递归进 PG 数据目录，把【空目录】全部 rmdir。而 PG 的
  pg_commit_ts/pg_dynshmem/pg_notify/pg_replslot/pg_serial/pg_snapshots/pg_stat_tmp/
  pg_tblspc/pg_twophase + pg_logical/{snapshots,mappings} + pg_wal/{archive_status,summaries}
  默认就是空的（PG 干净关闭后更空）→ 被删 → PG 起不来 → retain 卡 420s。
  证据：/opt/data/disk-cleanup/cleanup.log 里有 65 条
  `DELETED: .../data/pg_xxx (empty dir)`。

对策：往这些目录放一个 .keep 占位文件，目录恒非空 → 插件跳过。
      PG 只按固定文件名读写这些目录，多余文件无影响（实测 /health 仍 healthy）。
      插件不追踪 .keep（不在 tracked.json），所以不会被当临时文件删掉。

用法：/opt/data/.venv/bin/python3 protect_pg_dirs.py
"""
import pathlib
import sys

KNOWN = [
    'pg_commit_ts', 'pg_dynshmem', 'pg_notify', 'pg_replslot', 'pg_serial',
    'pg_snapshots', 'pg_stat_tmp', 'pg_tblspc', 'pg_twophase',
    'pg_logical/snapshots', 'pg_logical/mappings',
    'pg_wal/archive_status', 'pg_wal/summaries',
]


def find_data_dir() -> pathlib.Path:
    pref = pathlib.Path('/opt/data/.pg0/instances/hindsight-embed-hermes/data')
    if pref.is_dir():
        return pref
    cands = sorted(pathlib.Path('/opt/data/.pg0/instances').glob('*/data'))
    if not cands:
        sys.exit('❌ 找不到 PG 数据目录，先跑 hindsight_repair.sh')
    return cands[0]


def main() -> None:
    data = find_data_dir()
    print(f'PG 数据目录：{data}')

    # 已知 13 个 + 数据树下当前为空的任何目录（防未来再中招）
    extra = []
    for p in list(data.iterdir()) + list(data.glob('*/*')):
        if p.is_dir() and not p.is_symlink() and p.name != 'log':
            try:
                if not any(p.iterdir()):
                    extra.append(str(p.relative_to(data)))
            except OSError:
                pass
    targets = sorted(set(KNOWN) | set(extra))
    print(f'需保护 {len(targets)} 个目录（已知 {len(KNOWN)} + 顺带空目录 {len(set(extra) - set(KNOWN))}）')

    made = kept = 0
    for rel in targets:
        d = data / rel
        d.mkdir(parents=True, exist_ok=True)
        f = d / '.keep'
        if f.exists():
            kept += 1
        else:
            f.write_text('', encoding='utf-8')
            made += 1
    print(f'结果：新建 {made} · 已存在 {kept}')

    left = [str(p.relative_to(data)) for p in data.rglob('*')
            if p.is_dir() and not p.is_symlink() and not any(p.iterdir())]
    print(f'复查：PG 数据树下空目录 = {left if left else "无 ✅"}')
    sys.exit(1 if left else 0)


if __name__ == '__main__':
    main()
