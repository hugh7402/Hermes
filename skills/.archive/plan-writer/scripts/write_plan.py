"""
方案智能体 v2 — 两轮制
- 第1轮：设计架构
- 第2轮：基于架构+知识库一次生成全文
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

def write_plan(requirement, output_name=None):
    if not output_name:
        output_name = f"方案-{datetime.now().strftime('%Y%m%d-%H%M')}"
    
    print(f"📋 方案智能体 v2 启动")
    print(f"   需求：{requirement[:80]}...")
    
    # 步骤1: 检索知识库
    print("\n🔍 检索知识库...")
    kb = search_knowledge_base(requirement)
    print(f"   找到 {len(kb)} 篇相关笔记")
    for r in kb[:5]:
        print(f"   - {r['title']} (相关性:{r['score']})")
    
    # 步骤2: 设计架构
    print("\n🏗️ 设计架构 (第1轮)...")
    kb_ctx = "\n".join([f"- [{r['title']}] {r['preview'][:200]}" for r in kb[:8]])
    
    arch_prompt = f"""你是政务信息化方案架构师。基于以下需求和知识库内容，设计一个方案的章节架构。

需求：{requirement}

知识库参考：
{kb_ctx}

输出一个清晰的章节结构，用 ## 标记章、### 标记节：
## 一、章标题
### 1.1 节标题
...
要求：6-10个章，覆盖背景、需求、设计、方案、实施、保障。只输出架构，不写内容。"""
    
    architecture = call_llm(arch_prompt, max_tokens=2000)
    print(f"   架构完成 ({len(architecture)}字符)")
    
    # 步骤3: 一次生成全文
    print("\n✍️ 撰写全文 (第2轮)...")
    full_prompt = f"""你是资深政务信息化方案撰写专家。请基于以下架构和知识库内容，撰写完整方案。

【方案需求】{requirement}

【方案架构】
{architecture}

【知识库参考资料】
{chr(10).join([f"### {r['title']}\n{r['preview'][:600]}" for r in kb[:6]])}

【撰写要求】
1. 严格按架构填充每个章节
2. 基于知识库真实信息，无法确认处标注[待确认]
3. 使用正式政府公文语言，Markdown格式
4. 术语统一，逻辑连贯
5. 总字数：3000-5000字
6. 输出完整方案文档，从第一个##开始"""
    
    full_content = call_llm(full_prompt, max_tokens=12000)
    print(f"   全文完成 ({len(full_content)}字符)")
    
    # 步骤4: 输出
    os.makedirs(OUTPUT, exist_ok=True)
    out_path = os.path.join(OUTPUT, f"{output_name}.md")
    
    final = f"""---
title: "{output_name}"
date: {datetime.now().strftime('%Y/%m/%d')}
source: "方案智能体 v2"
model: "deepseek-ai/DeepSeek-V4-Pro (硅基流动 2.5折)"
knowledge_base: {len(kb)} 篇参考
---

# {output_name}

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
> 需求：{requirement[:100]}
> 知识库参考：{len(kb)} 篇

{full_content}
"""
    Path(out_path).write_text(final, encoding='utf-8')
    print(f"\n✅ 方案已输出：{out_path}")
    print(f"   总长度：{len(final)} 字符")
    
    return out_path, full_content[:300]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 write_plan.py <需求> [名称]")
        sys.exit(1)
    path, preview = write_plan(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"\n📄 MEDIA:{path}")
