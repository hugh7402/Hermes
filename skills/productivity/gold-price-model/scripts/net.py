# -*- coding: utf-8 -*-
"""网络层：双通道取数 + 代理自愈 + 降级。

为什么不用 requests：本机没装，且 urllib 足够。

两个关键点（踩过）：
  1. 把代理交给 urllib 时必须同时换 HTTPSHandler 的 SSL context，
     否则部分站报 `SSL: RECORD_LAYER_FAILURE`。
  2. 代理端口是 HTTP 混入（http://127.0.0.1:10808），不是纯 socks5。

降级策略：
  境外源（Yahoo / CFTC / WGC）挂了不影响直连源（财政部 / 新浪 / 东财）。
  ensure_proxy() 自愈失败时，调用方应继续跑直连因子，并在输出里
  明确标出缺了哪些因子，**不要静默降级**。
"""
import json
import ssl
import subprocess
import time
import urllib.error
import urllib.request

PROXY = 'http://127.0.0.1:10808'
PROXY_SH = '/opt/data/proxy-skill/proxy.sh'
AUTO_SWITCH = '/opt/data/proxy-skill/proxy_auto_switch.sh'
UA = {'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')}
SINA = {**UA, 'Referer': 'https://finance.sina.com.cn'}

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

_direct = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_ctx))
_viaproxy = urllib.request.build_opener(
    urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY}),
    urllib.request.HTTPSHandler(context=_ctx))


# ────────────────────────── 代理自愈 ──────────────────────────

def proxy_alive(timeout=8) -> bool:
    """判活只看 generate_204 是否返 204。不要看 ps、不要看 ss。"""
    try:
        r = _viaproxy.open('https://www.google.com/generate_204', timeout=timeout)
        return r.status == 204
    except Exception:
        return False


def _sh(cmd, t=120):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 124, '超时'


def ensure_proxy(verbose=True) -> bool:
    """确保代理能出网。已通则直接返回。

    顺序：验活 → proxy.sh start → 换节点。不轻易换节点，因为换节点要重写
    reality_active.json，并发时会互相顶掉（见 proxy skill 的假活陷阱）。
    """
    if proxy_alive():
        return True
    if verbose:
        print('  [net] 代理不通，尝试拉起…')
    _sh(f'bash {PROXY_SH} start', t=90)
    for _ in range(3):
        time.sleep(3)
        if proxy_alive():
            if verbose:
                print('  [net] 代理已拉起')
            return True
    if verbose:
        print('  [net] 拉起无效，尝试换节点…')
    _sh(f'bash {AUTO_SWITCH}', t=600)
    if proxy_alive():
        if verbose:
            print('  [net] 换节点后可用')
        return True
    if verbose:
        print('  [net] ⚠️ 代理仍不可用，境外因子将缺失')
    return False


# ────────────────────────── 取数 ──────────────────────────

def fetch(url, hdr=None, via='auto', timeout=30, tries=3):
    """取网页/接口。via: 'direct' | 'proxy' | 'auto'。

    auto = 先直连，失败再走代理。调用前需已 ensure_proxy()。
    返回 str；失败抛异常（调用方自行缓存并降级）。

    tries>1 时对**瞬时错误**重试（RemoteDisconnected / 超时 / 5xx），
    这类错误非常常见，单次抖动就把整个回填搞崩不划算（真实踩过：
    跑了 6 个源后第 7 个 RemoteDisconnected，整轮白跑）。
    """
    last = None
    for k in range(max(1, tries)):
        try:
            req = urllib.request.Request(url, headers=hdr or UA)
            if via == 'direct':
                return _direct.open(req, timeout=timeout).read().decode('utf-8', 'ignore')
            if via == 'proxy':
                return _viaproxy.open(req, timeout=timeout).read().decode('utf-8', 'ignore')
            try:
                return _direct.open(req, timeout=timeout).read().decode('utf-8', 'ignore')
            except urllib.error.HTTPError:
                raise                     # 403/404 直连不行就换代理，不算瞬时错误
            except Exception:
                return _viaproxy.open(req, timeout=timeout).read().decode('utf-8', 'ignore')
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 404):
                raise                     # 重试无意义
            time.sleep(1.5 ** k)
        except Exception as e:
            last = e
            if k < tries - 1:
                time.sleep(1.5 ** k)
                continue
            raise
    raise last


def fetch_json(url, hdr=None, via='auto', timeout=30):
    return json.loads(fetch(url, hdr, via, timeout))


def sina(codes, timeout=20) -> dict:
    """新浪行情，codes 逗号分隔。返回 {code: [字段...]}。

    例：sina('hf_XAU,DINIW,fx_susdcny')
    """
    txt = fetch(f'https://hq.sinajs.cn/list={codes}', SINA, 'direct', timeout)
    out = {}
    for line in txt.splitlines():
        if '="' not in line:
            continue
        key = line.split('=')[0].replace('var hq_str_', '').strip()
        body = line.split('="', 1)[1].rstrip('";')
        out[key] = body.split(',') if body else []
    return out


def num(x, default=None):
    """安全转 float。空字符串/None/异常都返回 default，
    因为新浪的停牌/无数据字段全是空串，直接 float() 会炸。"""
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return default


if __name__ == '__main__':
    print('代理可用:', ensure_proxy())
    d = sina('hf_XAU,DINIW,fx_susdcny')
    print('伦敦金', num(d.get('hf_XAU', [''])[0]))
    print('美元指数', num(d.get('DINIW', ['', ''])[1] if len(d.get('DINIW', [])) > 1 else None))
    print('USDCNY', num(d.get('fx_susdcny', ['', ''])[1] if len(d.get('fx_susdcny', [])) > 1 else None))
