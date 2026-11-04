"""
方案智能体 v3 — 四轮制（含 humanizer 去AI味）
- 第1轮：设计架构
- 第2轮：用户确认（外部）
- 第3轮：基于架构+知识库一次生成全文（Prompt已嵌入humanizer原则）
- 第4步：humanizer 去AI味后处理
- 模型：DeepSeek 官方 deepseek-v4-pro（可用环境变量 PLAN_MODEL 覆盖）
"""
import os, sys, json, re, urllib.request, time
from pathlib import Path
from datetime import datetime

VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"
CONCEPTS = f"{VAULT}/concepts"
INBOX = f"{VAULT}/00-INBOX"
OUTPUT = "/opt/data/OutPut Box"

def search_knowledge_base(query, max_results=10):
    keywords = list(set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', query)))[:20]
    results = []
    for search_dir in [CONCEPTS, INBOX]:
        if not os.path.exists(search_dir):
            continue
        for f in sorted(Path(search_dir).glob("*.md")):
            try:
                content = f.read_text(encoding='utf-8')
                score = sum(content.lower().count(kw.lower()) for kw in keywords)
                if score > 0:
                    m = re.search(r'title:\s*"?(.+?)"?\n', content)
                    title = m.group(1) if m else f.stem
                    results.append({"file": str(f), "name": f.name, "title": title, "score": score, "preview": content[:1200]})
            except: pass
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]

# ── 模型链（2026-11-04 用户定：主官方、备百炼，主通道挂了自动切）──
#   主  官方 DeepSeek-V4.1-Flash  model=deepseek-flash（旧名 deepseek-v4-flash 是别名）
#   备  百炼 deepseek-v4.1-flash-1017
# 实测（同 prompt 2000 字政务方案，各 3 次复核）：三家质量无差别，差异只在输出 token 效率——
#   百炼 v4.1-flash 1849 tok / 百炼 -1017 快照 2517 tok / 官方 deepseek-flash 3081 tok（多烧 67%）
# 单价（元/百万 token，官方峰时）：输出 8；百炼同代同为 4 闲 / 8 峰
_PROVIDERS = [
    {"label": "官方 DeepSeek-V4.1-Flash",
     "url": "https://api.deepseek.com/v1/chat/completions",
     "model": "deepseek-flash", "key_env": "DEEPSEEK_API_KEY"},
    {"label": "百炼 deepseek-v4.1-flash-1017（备用）",
     "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
     "model": "deepseek-v4.1-flash-1017", "key_env": "BAILIAN_API_KEY"},
]

# 覆盖方式：PLAN_PROVIDER=primary|fallback 只跑单个；或 PLAN_API_URL/PLAN_KEY_ENV/PLAN_MODEL 强制指定
# PLAN_THINKING=0 关思考（仅百炼认 enable_thinking，官方忽略）
PLAN_PROVIDER = os.environ.get("PLAN_PROVIDER", "").strip().lower()
PLAN_THINKING = os.environ.get("PLAN_THINKING", "").strip().lower()
DS_MAXTOK_CAP = 32000          # 单次输出上限（推理型模型 reasoning 会占用该预算）

if os.environ.get("PLAN_MODEL"):
    _PROVIDERS = [{"label": "环境变量指定",
                   "url": os.environ.get("PLAN_API_URL", _PROVIDERS[0]["url"]),
                   "model": os.environ["PLAN_MODEL"],
                   "key_env": os.environ.get("PLAN_KEY_ENV", "DEEPSEEK_API_KEY")}]
elif PLAN_PROVIDER == "primary":
    _PROVIDERS = _PROVIDERS[:1]
elif PLAN_PROVIDER == "fallback":
    _PROVIDERS = _PROVIDERS[1:]

DS_URL = _PROVIDERS[0]["url"]
DS_MODEL = _PROVIDERS[0]["model"]
PLAN_KEY_ENV = _PROVIDERS[0]["key_env"]


def _read_key(key_env):
    fd = os.open("/opt/data/.env", os.O_RDONLY)
    data = os.read(fd, 65536).decode("utf-8")
    os.close(fd)
    for line in data.split("\n"):
        if line.startswith(key_env + "="):
            return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def call_llm(prompt, max_tokens=16000, temperature=0.3, providers=None):
    """按 providers（默认 _PROVIDERS）顺序调用，主通道彻底失败才切备用。每个 provider 内部最多重试 3 次。"""
    errors = []
    for prov in (providers or _PROVIDERS):
        key = _read_key(prov["key_env"])
        if not key:
            errors.append(f"{prov['label']}: .env 里没有 {prov['key_env']}")
            continue
        mt = max_tokens
        for attempt in range(3):
            try:
                body_dict = {
                    "model": prov["model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": mt, "temperature": temperature,
                }
                # enable_thinking 只有百炼认；官方靠 deepseek-chat 这个别名实现关思考
                if (PLAN_THINKING in ("0", "false", "off", "no") or prov.get("_think_off")) \
                        and "dashscope" in prov["url"]:
                    body_dict["enable_thinking"] = False
                body = json.dumps(body_dict).encode()
                req = urllib.request.Request(prov["url"], data=body, headers={
                    "Authorization": f"Bearer {key}", "Content-Type": "application/json"
                })
                d = json.loads(urllib.request.urlopen(req, timeout=600).read())
                ch = d["choices"][0]
                content = (ch.get("message") or {}).get("content") or ""
                u = d.get("usage") or {}
                # 闸门1：推理型模型可能把预算全用在 reasoning 上、正文为空（不报错的静默失败）
                if not content.strip():
                    mt = min(mt * 2, DS_MAXTOK_CAP)
                    raise RuntimeError(
                        f"模型未返回正文（completion_tokens={u.get('completion_tokens')}）；"
                        f"已把 max_tokens 提到 {mt} 重试")
                # 闸门2：被 max_tokens 截断的正文不能用
                if ch.get("finish_reason") == "length":
                    mt = min(mt * 2, DS_MAXTOK_CAP)
                    raise RuntimeError(
                        f"输出被 max_tokens 截断（本次 {len(content)} 字）；已提到 {mt} 重试")
                print(f"    [模型 {prov['model']} · 输出 {len(content)} 字 · "
                      f"completion_tokens={u.get('completion_tokens')} · mt={mt}]")
                return content
            except Exception as e:
                last = e
                if attempt == 2:
                    errors.append(f"{prov['label']} 3 次均失败：{last}")
                else:
                    time.sleep(5)
        if len(_PROVIDERS) > 1 and prov is not _PROVIDERS[-1]:
            print(f"    ⚠️ {prov['label']} 不可用，切换备用通道…", file=sys.stderr)
    raise RuntimeError("全部通道失败：\n  " + "\n  ".join(errors))

def humanize_text(text):
    """结构层安全清理——只删「删了句子仍完整」的东西，不碰任何中文实词。

    ⚠️ 2026-11-04 教训：上一版在这里无条件删「有效/深入/切实」和「彰显/赋能/抓手」，
        结果「有效提升A」→「提升A」变生硬、「展望未来，必将X」→「必将X」直接成了无主语病句、
        「数据有效性」被拆成「数据性」。**正则删词做不了去AI味，只会做坏句子。**
        真正的句级改写交给 humanize_llm()，这里只做零风险清理。
    """
    import re

    # 1. 独立引导句：后面接的是完整句子，删掉不影响语法
    text = re.sub(r'(值得注意的是，|需要指出的是，|不难看出，|毋庸置疑，|不可否认的是，|不可否认，|我们坚信，)', '', text)

    # 2. 纯英文套话（中文政务文里几乎不出现，连排时清掉）
    en_replacements = {
        'Additionally, ': '', 'Moreover, ': '', 'Furthermore, ': '', 'In addition, ': '',
        'It is worth noting that ': '', 'It should be noted that ': '',
    }
    for old, new in en_replacements.items():
        text = text.replace(old, new)

    # 3. 合并多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ── 句级改写：真正的去AI味 ──────────────────────────────────────────
_HUMANIZE_PROMPT = """下面是一份政务方案的正文。请做「去AI味」改写，**只改句式，不改事实**。

必须遵守的硬约束：
1. **信息一项都不能少**：数字、年份、金额、百分比、标准号（如 DB51/T 2441-2018）、机构名、系统名、专有名词，一律原样保留，不得增删改。
2. **不许产生病句**：删掉状语或引导成分时，必须重写整句让它语法完整。绝不允许出现「必将为数据要素市场化提供支撑」这种没有主语的残句。
3. **政务术语一律保留**：协同、抓手、赋能、闭环、深耕、彰显、体现、标志着、扎实推进、一体推进……这些是行业词，不是AI腔，不要替换、不要回避。
4. **正常书面副词保留**：有效、深入、切实、进一步、持续——这些是正常汉语，只在明显重复冗余时才调整，不要机械删除。
5. **字数不得低于原文的 90%**，不得缩写概括。

要改的是这些句式毛病：
- 空心状语开头：「在……背景下，」「随着……的深入，」「当前，」——不是简单删掉，而是把状语信息并入主句或后置
- 无主语的拔高收尾：「展望未来，必将……」「前景广阔」——补上明确主语，或换成事实性表述
- 机械排比：连续三个以上同构短句，打散节奏
- 段落一律用「首先/其次/最后」「一方面/另一方面」硬套结构
- 空转同义反复：把一句话拆成两句说的

只输出改写后的正文，不要任何解释、标题、前言、后记。"""


def _extract_facts(text):
    """提取不可丢失的硬事实：数字/年份/百分比/标准号"""
    import re
    return set(re.findall(r'[A-Z]{2,}/?T?\s?\d[\d\.\-/]*|\d+(?:\.\d+)?%?', text))


_GOV_TERMS = ['协同', '抓手', '赋能', '闭环', '深耕', '彰显', '体现', '标志着',
              '扎实推进', '一体推进', '统筹', '贯通', '闭环管理']

# 改写通道：必须开思考。实测关思考（deepseek-chat）虽然 2.9s 完成、快 26 倍，
#   但会丢掉政务术语「标志着」、且不改「在…背景下」，被 _humanize_guard 拦下。
#   质量优先，所以改写仍走 _PROVIDERS（开思考），靠**并发**压缩总耗时。
_HUMANIZE_PROVIDERS = None   # None = 用默认 _PROVIDERS（开思考）


def _humanize_guard(original, rewritten):
    """改写结果校验。返回 (是否通过, 原因)。宁可留着AI味，也不能丢信息或出病句。"""
    import re
    if not rewritten or len(rewritten.strip()) < 20:
        return False, "改写结果为空或过短"
    o_han = len(re.findall(r'[\u4e00-\u9fff]', original))
    r_han = len(re.findall(r'[\u4e00-\u9fff]', rewritten))
    if o_han and r_han < o_han * 0.90:
        return False, f"字数缩水 {o_han}→{r_han}（低于原文 90%）"
    lost = _extract_facts(original) - _extract_facts(rewritten)
    if lost:
        return False, f"丢失数字/标准号 {sorted(lost)[:6]}"
    lost_terms = [t for t in _GOV_TERMS if t in original and t not in rewritten]
    if lost_terms:
        return False, f"丢失政务术语 {lost_terms}"
    # 病句粗检：段落开头直接是「必将/将为/必须/应当/需要」而无主语的残句
    if re.search(r'(?m)^(必将|将为|将会|必须|应当|需要进一步)', rewritten):
        return False, "改写后出现无主语残句"
    return True, "ok"


def humanize_llm(text, chunk_size=2500, workers=4):
    """用模型做句级去AI味改写：分块 → 并发改写 → 逐块硬校验，校验不过保留原文。

    并发是必须的：改写要开思考（关思考会丢政务术语），单块约 75s，
    一份 2 万字方案 8 块串行要 10 分钟；4 并发放到 ~2.5 分钟。
    """
    import re
    from concurrent.futures import ThreadPoolExecutor

    paras = [p for p in re.split(r'\n{2,}', text) if p.strip()]
    chunks, buf = [], ''
    for p in paras:
        if len(buf) + len(p) > chunk_size and buf:
            chunks.append(buf)
            buf = p
        else:
            buf = (buf + '\n\n' + p) if buf else p
    if buf:
        chunks.append(buf)

    def _do(idx_ck):
        idx, ck = idx_ck
        try:
            new = call_llm(f"{_HUMANIZE_PROMPT}\n\n原文：\n{ck}",
                           max_tokens=max(4000, len(ck) * 3),
                           providers=_HUMANIZE_PROVIDERS)
        except Exception as e:
            return idx, ck, f"调用失败 {str(e)[:60]}"
        ok, why = _humanize_guard(ck, new)
        return idx, (new.strip() if ok else ck), (None if ok else why)

    results: list[str] = [""] * len(chunks)
    dropped = 0
    with ThreadPoolExecutor(max_workers=min(workers, len(chunks))) as ex:
        for idx, txt, why in ex.map(_do, list(enumerate(chunks))):
            results[idx] = txt
            if why:
                dropped += 1
                print(f"    ⚠️ 第{idx+1}/{len(chunks)}块未采用改写（{why}），保留原文")
    if any(r == "" for r in results):          # 理论上不会发生，保险
        results = [r if r else chunks[i] for i, r in enumerate(results)]
    print(f"  ✅ 句级改写完成：{len(chunks)-dropped}/{len(chunks)} 块通过校验"
          f"（{workers} 并发）")
    return '\n\n'.join(results)

def write_plan(requirement, output_name=None):
    if not output_name:
        output_name = f"方案-{datetime.now().strftime('%Y%m%d-%H%M')}"
    
    os.makedirs(OUTPUT, exist_ok=True)
    out_dir = os.path.join(OUTPUT, output_name)
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"📚 检索知识库...")
    refs = search_knowledge_base(requirement)
    print(f"  找到 {len(refs)} 篇相关笔记")
    ctx = "\n\n".join([
        f"--- 参考 {i+1}：{r['title']} ---\n{r['preview']}"
        for i, r in enumerate(refs[:5])
    ])
    
    print(f"🏗️  第1轮：架构设计...")
    arch_prompt = f"""你是政务信息化方案架构师。请为以下需求设计方案的完整架构。

需求：{requirement}

参考内容：
{ctx}

输出格式：
## 目录结构
（列出全部章节）

## 各节核心论点
（每节3-5点）

## 技术选型对比
（关键决策点，含推理理由）

===
注意：这是架构设计，不写全文。结构要清晰，每节涵盖核心要点。"""
    
    arch = call_llm(arch_prompt, max_tokens=8000)
    
    arch_path = os.path.join(out_dir, "01-架构设计.md")
    Path(arch_path).write_text(f"# 架构设计\n\n{requirement}\n\n{arch}", encoding='utf-8')
    print(f"  ✅ 架构已保存")
    
    print(f"✍️  第3轮：撰写全文（含 humanizer 原则）...")
    full_prompt = f"""你是政务信息化方案架构师。请基于以下架构设计，撰写完整方案。

需求：{requirement}

参考内容：
{ctx}

架构设计：
{arch}

要求：
1. 严格按照架构的目录结构输出
2. 每节内容充实，有数据支撑
3. 使用Markdown格式，适当使用表格
4. 总字数不限，务必完整
5. 引用参考内容中的真实数据和案例

【去AI味写作要求 — 严格遵守】
- 不用"Additionally、Moreover、Furthermore、值得注意的是"等AI高频引导词
- 不用"stand as、serve as、marks a、underscores its importance"等英文空洞拔高句式
- **政务术语照常使用**："协同/抓手/赋能/闭环/深耕/彰显/体现/标志着"是行业词，不是AI腔，该用就用
- 正常书面副词照常用："有效提升""深入开展""切实保障"都是对的，不要为了"去AI味"把它们删掉导致句子生硬
- 不用"不仅仅...更是..."/"不是...而是..."的否定平行结构
- 不用"在...背景下/随着...的深入/众所周知"等套路开头——但状语里的信息要保留，把它并入主句，不要一删了之
- 每个段落直接陈述，不加"我们需要指出的是/不难看出"等引导
- 具体数据前置，不用"显著/大幅/非常/极其"等模糊副词
- 标题写具体，不用"背景与意义/现状与挑战/对策与建议"等套话标题
- 结尾不写"展望未来/前景广阔/必将"等AI式收尾，用事实或问题收尾
- 像体制内有经验的老笔杆子那样写：该说理说理，该摆数摆数，不装不飘"""
    
    full = call_llm(full_prompt, max_tokens=24000)
    
    print(f"🔄  第4步：Humanizer 去AI味...")
    full = humanize_text(full)          # 层一：结构层安全清理（零风险）
    if os.environ.get("PLAN_NO_HUMANIZE_LLM", "").strip().lower() not in ("1", "true", "yes"):
        print(f"  🔁 层二：句级改写（模型，带事实/术语/字数校验，不过则回退原文）...")
        full = humanize_llm(full)
    else:
        print(f"  ⏭️  已按 PLAN_NO_HUMANIZE_LLM 跳过句级改写")
    print(f"  ✅ 去AI味完成")
    
    full_path = os.path.join(out_dir, "02-完整方案.md")
    Path(full_path).write_text(f"# {output_name}\n\n{requirement}\n\n---\n\n{full}", encoding='utf-8')
    print(f"  ✅ 方案已保存")
    
    # 索引
    summary = full[:200].replace('\n', ' ')
    index = f"""# {output_name}

生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
需求：{requirement}
总字数：{len(full)}

## 文件列表
- [架构设计](01-架构设计.md)
- [完整方案](02-完整方案.md)
"""
    Path(os.path.join(out_dir, "index.md")).write_text(index, encoding='utf-8')
    
    print(f"\n📁 输出目录：{out_dir}")
    print(f"📊 方案总字数：{len(full)}")
    return out_dir, len(full)

if __name__ == "__main__":
    req = " ".join(sys.argv[1:]) or "政务信息化项目方案"
    write_plan(req)
