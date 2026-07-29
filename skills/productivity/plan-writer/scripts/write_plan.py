"""
方案智能体 v3 — 四轮制（含 humanizer 去AI味）
- 第1轮：设计架构
- 第2轮：用户确认（外部）
- 第3轮：基于架构+知识库一次生成全文（Prompt已嵌入humanizer原则）
- 第4步：humanizer 去AI味后处理
- 模型：硅基流动 deepseek-ai/DeepSeek-V4-Pro（2.5折优惠）
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

def call_llm(prompt, max_tokens=8000, temperature=0.3):
    fd = os.open("/opt/data/.env", os.O_RDONLY)
    data = os.read(fd, 8192).decode("utf-8")
    os.close(fd)
    key = ""
    for line in data.split("\n"):
        if line.startswith("SILICONFLOW_API_KEY"):
            key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    url = "https://api.siliconflow.cn/v1/chat/completions"
    for attempt in range(3):
        try:
            body = json.dumps({
                "model": "deepseek-ai/DeepSeek-V4-Pro",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens, "temperature": temperature
            }).encode()
            req = urllib.request.Request(url, data=body, headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json"
            })
            resp = urllib.request.urlopen(req, timeout=300)
            return json.loads(resp.read())["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt == 2: raise e
            time.sleep(5)

def humanize_text(text):
    """去AI味后处理：替换AI高频套路化表达"""
    import re
    
    # 1. 删掉套路开头（在...背景下 随着...的深入 众所周知）
    text = re.sub(r'(?m)^(在[^。]{0,40}背景下，?|随着[^。]{0,40}深入，?|众所周知，?|当前，?|近年来，?)', '', text)
    
    # 2. 删掉空洞引导句
    text = re.sub(r'(值得注意的是，?|需要指出的是，?|不难看出，?|毋庸置疑，?|不可否认，?|我们坚信，?)', '', text)
    
    # 3. 否定平行结构 → 直接陈述
    text = re.sub(r'不仅仅[^，。]{5,40}，更[^。]{5,40}[。，]', lambda m: m.group(0).replace('不仅仅', '').replace('，更', '，'), text)
    
    # 4. 删掉AI式收尾
    text = re.sub(r'(?m)^(展望未来，?|前景广阔[。！]|未来已来[。！]|必将[^。]{3,30}[。！])', '', text)
    
    # 5. 套话替换
    replacements = {
        'Additionally, ': '', 'Moreover, ': '', 'Furthermore, ': '', 'In addition, ': '',
        'It is worth noting that ': '', 'It should be noted that ': '',
        'stand as ': '是', 'serve as ': '是', 'marks a ': '',
        'underscores ': '', 'underscoring ': '',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # 6. 中文套话
    cn_replacements = {
        '彰显了': '',
        '标志着': '',
        '致力于': '做',
        '体现了': '',
        '赋能': '支持',
        '深耕': '专注',
        '闭环': '完整流程',
        '抓手': '手段',
        '协同': '协作',
        '切实': '',
        '有效': '',
        '深入': '',
        '扎实推进': '推进',
    }
    for old, new in cn_replacements.items():
        text = text.replace(old, new)
    
    # 7. 删重复空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

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
    
    arch = call_llm(arch_prompt, max_tokens=4000)
    
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
- 不用"stand as、serve as、marks a、underscores、彰显、标志着"等空洞拔高句式
- 多用"是/有/要/做"等简单动词，少用"致力于/赋能/深耕/闭环"等套话
- 不用"不仅仅...更是..."/"不是...而是..."的否定平行结构
- 不用"在...背景下/随着...的深入/众所周知"等套路开头
- 每个段落直接陈述，不加"我们需要指出的是/不难看出"等引导
- 具体数据前置，不用"显著/大幅/非常/极其"等模糊副词
- 标题写具体，不用"背景与意义/现状与挑战/对策与建议"等套话标题
- 结尾不写"展望未来/前景广阔/必将"等AI式收尾，用事实或问题收尾
- 像体制内有经验的老笔杆子那样写：该说理说理，该摆数摆数，不装不飘"""
    
    full = call_llm(full_prompt, max_tokens=8000)
    
    print(f"🔄  第4步：Humanizer 去AI味...")
    full = humanize_text(full)
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
