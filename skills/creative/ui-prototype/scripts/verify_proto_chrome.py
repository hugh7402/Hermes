#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单文件原型的真 Chrome 验证：全屏渲染扫 + JS 报错 + 交互联动探针。

用法:
    python3 verify_proto_chrome.py <产物.html> [--screens s1,s1b,s3] \
        [--probe 'openCollect|#c-dock|库表对接,接口对接,文件对接|#sync-mode']

--probe 四段用 | 分隔：
    1) 打开抽屉/弹窗要调的 JS 表达式（如 window.SCREENS.s1b.openCollect()）
    2) 要操作的控件选择器（select/input）
    3) 依次设定的值，逗号分隔
    4) 要读回验证的联动元素选择器

判断标准：全部屏 status=ok、JS 报错为空、probe 每个值读回的内容各不相同（说明联动真生效）。
只读代码容易把「绑定写在 init()、元素还不存在」这类问题当成已实现，必须跑一次。
"""
import argparse
import asyncio
import pathlib
import sys

CHROME = '/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell'


def parse_probe(s):
    parts = s.split('|')
    if len(parts) != 4:
        sys.exit('--probe 需四段：动作|控件选择器|值1,值2|读回选择器')
    action, ctrl, values, target = (x.strip() for x in parts)
    return action, ctrl, [v.strip() for v in values.split(',') if v.strip()], target


async def run(html: pathlib.Path, screens, probe, shot):
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME,
                                          args=['--no-sandbox', '--disable-gpu'])
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        errs = []
        page.on('pageerror', lambda e: errs.append(str(e)[:160]))
        await page.goto(html.resolve().as_uri())
        await page.wait_for_timeout(1200)

        ok = bad = 0
        for sc in screens:
            r = await page.evaluate(
                """(sc) => {
                     try { window.APP.go(sc); } catch (e) { return 'go:' + e; }
                     const el = document.getElementById('screen-' + sc);
                     if (!el) return 'missing';
                     return el.textContent.trim().length > 20 ? 'ok' : 'empty';
                   }""", sc)
            if r == 'ok':
                ok += 1
            else:
                bad += 1
                print(f'  ✗ {sc}: {r}')
            await page.wait_for_timeout(120)
        print(f'  屏渲染 {ok}/{len(screens)} 正常，异常 {bad}')

        if probe:
            action, ctrl, values, target = parse_probe(probe)
            opened = await page.evaluate(f"() => {{ try {{ {action}; return 'ok'; }} catch(e) {{ return String(e); }} }}")
            await page.wait_for_timeout(500)
            print(f'  抽屉/弹窗打开: {opened}')
            seen = []
            for v in values:
                await page.evaluate(
                    """([sel, val]) => {
                         const el = document.querySelector(sel);
                         if (!el) return false;
                         el.value = val;
                         el.dispatchEvent(new Event('change', {bubbles: true}));
                         return true;
                       }""", [ctrl, v])
                await page.wait_for_timeout(250)
                got = await page.evaluate(
                    "(sel) => { const e = document.querySelector(sel); return e ? e.textContent.trim() : null; }", target)
                seen.append(got)
                print(f'  「{v}」 → {target} = {got!r}')
            if len(set(map(str, seen))) == 1:
                print('  ⚠️ 所有取值读回相同 → 联动没生效（检查 handler 是否绑在 init() 里）')
            if shot:
                await page.screenshot(path=shot)
                print(f'  截图: {shot}')

        print('  JS 报错:', errs[:3] or '无 ✅')
        await browser.close()
        return bad == 0 and not errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html')
    ap.add_argument('--screens', default='')
    ap.add_argument('--probe', default='')
    ap.add_argument('--shot', default='')
    a = ap.parse_args()
    screens = [x.strip() for x in a.screens.split(',') if x.strip()]
    if not screens:
        sys.exit('请用 --screens 指定要扫的屏 key（逗号分隔）')
    fine = asyncio.run(run(pathlib.Path(a.html), screens, a.probe, a.shot))
    sys.exit(0 if fine else 1)


if __name__ == '__main__':
    main()
