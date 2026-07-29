#!/usr/bin/env python3
"""
智能体开发模型评测脚本
评测维度：延迟、工具调用准确性、指令遵循、代码生成、性价比
结果解释见 references/agent-development-benchmark-20260627.md

Usage:
  python3 benchmark_agent_dev.py
"""
import json, os, time, urllib.request, sys

# ============ 配置 ============

env_path = os.path.expanduser("/opt/data/.env")
fd = os.open(env_path, os.O_RDONLY)
env_data = os.read(fd, 8192).decode("utf-8")
os.close(fd)

def get_env(key):
    for line in env_data.split("\n"):
        line = line.strip()
        if line.startswith(key + "="):
            _, val = line.split("=", 1)
            return val.strip().strip('"').strip("'")
    return ""

DEEPSEEK_KEY = get_env("DEEPSEEK_API_KEY")
BAILIAN_KEY = get_env("BAILIAN_API_KEY")
GLM_KEY = get_env("GLM_API_KEY")
SILICONFLOW_KEY = get_env("SILICONFLOW_API_KEY")

# 模型配置： (name, provider_label, endpoint, api_key, model_id)
MODELS = [
    # DeepSeek 官方
    ("deepseek-v4-flash",  "DS官方", "https://api.deepseek.com/v1/chat/completions", DEEPSEEK_KEY, "deepseek-chat"),
    ("deepseek-v4-pro",    "DS官方", "https://api.deepseek.com/v1/chat/completions", DEEPSEEK_KEY, "deepseek-reasoner"),
    # 智谱
    ("glm-5.2", "智谱", "https://open.bigmodel.cn/api/paas/v4/chat/completions", GLM_KEY, "glm-5.2"),
    ("glm-5.1", "智谱", "https://open.bigmodel.cn/api/paas/v4/chat/completions", GLM_KEY, "glm-5.1"),
    # 百炼 — 注意: qwen3.7-max 无横线
    ("qwen-3.7-max", "百炼", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", BAILIAN_KEY, "qwen-3.7-max"),
    ("qwen3.7-max", "百炼", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", BAILIAN_KEY, "qwen3.7-max"),
    ("qwen-max",     "百炼", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", BAILIAN_KEY, "qwen-max"),
    ("qwen-plus",    "百炼", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", BAILIAN_KEY, "qwen-plus"),
    # 硅基流动
    ("DS-V4-Pro-Si", "硅基", "https://api.siliconflow.cn/v1/chat/completions", SILICONFLOW_KEY, "deepseek-ai/DeepSeek-V4-Pro"),
]

# ============ 测试用例 ============

TEST_CASES = [
    {
        "name": "工具调用-天气查询",
        "type": "tool_selection",
        "prompt": """你是一个智能助手，你有以下工具可用：
- search_weather(location: str): 查询指定城市的天气
- search_news(topic: str): 搜索新闻
- create_note(title: str, content: str): 创建笔记
- send_email(to: str, subject: str, body: str): 发送邮件

用户说："帮我看看明天北京会不会下雨"

请选择应该调用哪个工具，并给出参数。只输出JSON格式：
{"tool": "工具名", "arguments": {"参数名": "参数值"}}""",
        "expected_tool": "search_weather",
        "expected_args": {"location": "北京"}
    },
    {
        "name": "工具调用-模糊意图",
        "type": "tool_selection",
        "prompt": """你是一个智能助手，你有以下工具可用：
- search_weather(location: str): 查询指定城市的天气
- search_news(topic: str): 搜索新闻
- create_note(title: str, content: str): 创建笔记
- calculate(expression: str): 数学计算
- send_email(to: str, subject: str, body: str): 发送邮件

用户说："我刚想起来一个灵感，帮我记下来"

请选择应该调用哪个工具，并给出参数。只输出JSON格式：
{"tool": "工具名", "arguments": {"参数名": "参数值"}}""",
        "expected_tool": "create_note",
        "expected_args": {}
    },
    {
        "name": "指令遵循-复杂输出",
        "type": "instruction_following",
        "prompt": """请按以下要求输出：

1. 写一段关于"智能体开发"的介绍（150-200字）
2. 然后列出3个关键技术点，每个点带一句话说明
3. 最后用一句话总结

要求：使用Markdown格式，标题用##，每个部分用---分隔。
严格按1→2→3的顺序输出，不要改变顺序。""",
        "check": ["##", "---", "智能体", "1.", "2.", "3."]
    },
    {
        "name": "代码生成-CSV解析排序",
        "type": "code_generation",
        "prompt": """写一个Python函数，功能：
1. 读取CSV文件（参数：文件路径、排序列名、是否升序）
2. 按指定列排序
3. 返回排序后的数据（list[dict]格式）
4. 要求：有完整的异常处理、中文注释、类型注解

只输出代码，不要其他解释。""",
        "check": ["def ", "csv", "sort", "->", "异常", "#"]
    },
]

# ============ 评分函数 ============

def call_api(endpoint, api_key, model, messages, max_tokens=2000):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    if "siliconflow" in endpoint.lower() and "pro" in model.lower():
        max_tokens = 8000

    body = {
        "model": model,
        "messages": [{"role": "user", "content": messages}] if isinstance(messages, str) else messages,
        "max_tokens": max_tokens,
        "temperature": 0.1
    }

    data = json.dumps(body).encode()
    t0 = time.time()
    try:
        req = urllib.request.Request(endpoint, data=data, headers=headers)
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        lat = time.time() - t0
        choice = result["choices"][0]
        msg = choice["message"]
        content = msg.get("content", "")
        usage = result.get("usage", {})
        reasoning_tokens = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0) if "completion_tokens_details" in usage else 0
        return {
            "success": True, "latency": round(lat, 2), "content": content,
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": reasoning_tokens,
        }
    except Exception as e:
        lat = time.time() - t0
        return {"success": False, "latency": round(lat, 2), "error": str(e)[:300]}


def score_tool_selection(content, expected_tool, expected_args):
    score = 0
    try:
        data = json.loads(content)
        tool = data.get("tool", "")
        args = data.get("arguments", {})
        if tool.lower() == expected_tool.lower():
            score += 5
        elif expected_tool.lower() in tool.lower():
            score += 3
        for k, v in expected_args.items():
            if k in args:
                val = str(args[k])
                score += 3 if (isinstance(v, str) and v.lower() in val.lower()) else 2
        if isinstance(data, dict) and "tool" in data:
            score += 2
    except json.JSONDecodeError:
        if expected_tool.lower() in content.lower():
            score += 3
        score += 1
    return min(score, 10)


def score_instruction_following(content, checks):
    score = sum(2 for c in checks if c in content)
    if len(content) >= 200:
        score += 2
    return min(score, 10)


def score_code_generation(content, checks):
    score = sum(1.5 for c in checks if c in content)
    if "import" in content:
        score += 1
    code_lines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
    if len(code_lines) > 10:
        score += 1.5
    return min(score, 10)


PRICING = {
    "deepseek-v4-flash":  {"input": 1, "output": 2},
    "deepseek-v4-pro":    {"input": 4, "output": 16},
    "glm-5.2":            {"input": 5, "output": 20},
    "glm-5.1":            {"input": 2, "output": 8},
    "qwen-3.7-max":       {"input": 4, "output": 20},
    "qwen3.7-max":        {"input": 4, "output": 20},
    "qwen-max":           {"input": 4, "output": 12},
    "qwen-plus":          {"input": 0.8, "output": 2},
    "DS-V4-Pro-Si":       {"input": 1, "output": 4},
}

# ============ 主循环 ============

results = []

for model_name, platform, endpoint, api_key, model_id in MODELS:
    if not api_key or api_key.startswith("your-"):
        print(f"⚠️ 跳过 {model_name} ({platform}) - 无有效API Key")
        results.append({"model": model_name, "platform": platform, "error": "No API key"})
        continue

    print(f"\n{'='*60}")
    print(f"📊 测试: {model_name} ({platform}) -> {model_id}")
    print(f"{'='*60}")

    model_results = {"model": model_name, "platform": platform}
    total_lat = total_score = total_input = total_output = 0

    for tc in TEST_CASES:
        print(f"\n  ▶ {tc['name']}")
        result = call_api(endpoint, api_key, model_id, tc["prompt"])
        if not result["success"]:
            print(f"    ❌ {result.get('error', '')}")
            model_results[tc['name']] = {"score": 0, "latency": result['latency'], "error": result.get('error', '')}
            continue

        if tc["type"] == "tool_selection":
            score = score_tool_selection(result["content"], tc["expected_tool"], tc["expected_args"])
        elif tc["type"] == "instruction_following":
            score = score_instruction_following(result["content"], tc["check"])
        elif tc["type"] == "code_generation":
            score = score_code_generation(result["content"], tc["check"])
        else:
            score = 0

        total_lat += result["latency"]
        total_score += score
        total_input += result["input_tokens"]
        total_output += result["output_tokens"]

        print(f"    延迟:{result['latency']:>5.1f}s | 得分:{score:>2}/10 | 推理:{result['reasoning_tokens']:>4}t | 输出:{result['output_tokens']:>4}t")

        model_results[tc['name']] = {
            "score": score, "latency": result["latency"],
            "reasoning_tokens": result["reasoning_tokens"],
            "output_tokens": result["output_tokens"],
        }

    model_results["avg_latency"] = round(total_lat / len(TEST_CASES), 2)
    model_results["avg_score"] = round(total_score / len(TEST_CASES), 1)
    model_results["total_input_tokens"] = total_input
    model_results["total_output_tokens"] = total_output

    pricing = PRICING.get(model_name, {"input": 2, "output": 8})
    cost = (total_input * pricing["input"] + total_output * pricing["output"]) / 1_000_000
    model_results["cost_yuan"] = round(cost, 4)

    speed_score = max(0, 10 - model_results["avg_latency"])
    value_score = max(0, min(10, 0.1 / max(cost, 0.0001) / 2))
    composite = model_results["avg_score"] * 7 + speed_score * 1.5 + value_score * 1.5
    model_results["composite_score"] = round(composite, 1)

    print(f"\n  📈 均分={model_results['avg_score']} | 均延迟={model_results['avg_latency']}s | 成本=¥{cost} | 综合={model_results['composite_score']}")
    results.append(model_results)

# ============ 输出排名 ============
print("\n\n" + "=" * 70)
print("🏆 智能体开发模型评测结果")
print("=" * 70)

valid_results = [r for r in results if r.get("avg_score", 0) > 0]
valid_results.sort(key=lambda r: r["composite_score"], reverse=True)

print(f"\n{'排名':>4} | {'模型':<22} | {'平台':<6} | {'均分':>4} | {'延迟':>6} | {'成本¥':>8} | {'综合分':>6}")
print("-" * 70)
for i, r in enumerate(valid_results, 1):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    medal = medals.get(i, "  ")
    print(f"{medal} {i:>2} | {r['model']:<22} | {r['platform']:<6} | {r['avg_score']:>4} | {r['avg_latency']:>5.1f}s | ¥{r['cost_yuan']:<6.4f} | {r['composite_score']:>6}")

print("\n✅ 评测完成")
print(f"完整结果参考: references/agent-development-benchmark-20260627.md")
