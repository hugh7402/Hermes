#!/usr/bin/env python3
"""
智能体开发模型评测
评测维度：延迟、工具调用准确性、指令遵循、代码生成、性价比
"""
import json, os, time, urllib.request, sys

# ============ 配置 ============

# 读取 API Keys
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

    # 百炼 DashScope
    ("qwen-3.7-max", "百炼", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", BAILIAN_KEY, "qwen-3.7-max"),
    ("qwen-max",     "百炼", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", BAILIAN_KEY, "qwen-max"),
    ("qwen-plus",    "百炼", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", BAILIAN_KEY, "qwen-plus"),

    # 硅基流动
    ("DS-V4-Pro-Si", "硅基", "https://api.siliconflow.cn/v1/chat/completions", SILICONFLOW_KEY, "deepseek-ai/DeepSeek-V4-Pro"),
]

# ============ 测试用例 ============

TEST_CASES = []

# Test 1: 简单工具调用 - 识别意图选函数
TEST_CASES.append({
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
})

# Test 2: 复杂工具选择 - 需要推理
TEST_CASES.append({
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
    "expected_args": {}  # 任意参数都行
})

# Test 3: 多步骤指令遵循
TEST_CASES.append({
    "name": "指令遵循-复杂输出",
    "type": "instruction_following",
    "prompt": """请按以下要求输出：

1. 写一段关于"智能体开发"的介绍（150-200字）
2. 然后列出3个关键技术点，每个点带一句话说明
3. 最后用一句话总结

要求：使用Markdown格式，标题用##，每个部分用---分隔。
严格按1→2→3的顺序输出，不要改变顺序。""",
    "check": ["##", "---", "智能体", "1.", "2.", "3."]
})

# Test 4: 代码生成 + 中文注释
TEST_CASES.append({
    "name": "代码生成-CSV解析排序",
    "type": "code_generation",
    "prompt": """写一个Python函数，功能：
1. 读取CSV文件（参数：文件路径、排序列名、是否升序）
2. 按指定列排序
3. 返回排序后的数据（list[dict]格式）
4. 要求：有完整的异常处理、中文注释、类型注解

只输出代码，不要其他解释。""",
    "check": ["def ", "csv", "sort", "->", "异常", "#"]
})

# ============ 评测函数 ============

def call_api(endpoint, api_key, model, messages, max_tokens=2000, tools_mode=False):
    """调用API并返回结果"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    if "硅基" in endpoint and "deepseek" in model.lower() and "pro" in model.lower():
        # 硅基流动的V4-Pro需要大max_tokens（thinking模型）
        max_tokens = 8000

    body = {
        "model": model,
        "messages": messages if isinstance(messages, list) else [{"role": "user", "content": messages}],
        "max_tokens": max_tokens,
        "temperature": 0.1  # 低温度确保一致性
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
        finish = choice.get("finish_reason", "")

        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "") or ""

        usage = result.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        reasoning_tokens = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0) if "completion_tokens_details" in usage else 0

        return {
            "success": True,
            "latency": round(lat, 2),
            "content": content,
            "reasoning": reasoning,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": reasoning_tokens,
            "finish_reason": finish,
        }
    except Exception as e:
        lat = time.time() - t0
        body_preview = str(e)[:300]
        return {
            "success": False,
            "latency": round(lat, 2),
            "error": body_preview,
        }


def score_tool_selection(content, expected_tool, expected_args):
    """评分工具调用准确性 (0-10)"""
    score = 0
    try:
        # Try to parse JSON
        data = json.loads(content)
        tool = data.get("tool", "")
        args = data.get("arguments", {})

        # 工具名匹配
        if tool.lower() == expected_tool.lower():
            score += 5
        elif expected_tool.lower() in tool.lower():
            score += 3

        # 参数匹配
        for k, v in expected_args.items():
            if k in args:
                val = str(args[k])
                if isinstance(v, str) and v.lower() in val.lower():
                    score += 3
                elif val:
                    score += 3

        # 额外加分：JSON格式正确
        if isinstance(data, dict) and "tool" in data:
            score += 2

    except json.JSONDecodeError:
        # Try to extract from text
        if expected_tool.lower() in content.lower():
            score += 3
        score += 1  # 格式分扣减

    return min(score, 10)


def score_instruction_following(content, checks):
    """评分指令遵循 (0-10)"""
    score = 0
    for check in checks:
        if check in content:
            score += 2
    # 长度分
    if len(content) >= 200:
        score += 2
    return min(score, 10)


def score_code_generation(content, checks):
    """评分代码生成 (0-10)"""
    score = 0
    for check in checks:
        if check in content:
            score += 1.5
    # 代码完整性
    if "import" in content:
        score += 1
    # 有实际代码体（不仅仅是注释）
    code_lines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
    if len(code_lines) > 10:
        score += 1.5
    return min(score, 10)


# ============ 成本计算 ============

PRICING = {
    "deepseek-v4-flash":  {"input": 1, "output": 2},    # ¥/M tokens
    "deepseek-v4-pro":    {"input": 4, "output": 16},
    "glm-5.2":            {"input": 5, "output": 20},    # 智谱价格 (估计)
    "glm-5.1":            {"input": 2, "output": 8},     # 智谱价格 (估计)
    "qwen-3.7-max":       {"input": 4, "output": 20},    # 百炼价格
    "qwen-max":           {"input": 4, "output": 12},
    "qwen-plus":          {"input": 0.8, "output": 2},
    "DS-V4-Pro-Si":       {"input": 1, "output": 4},     # 硅基2.5折
}


# ============ 主循环 ============

results = []

for model_name, platform, endpoint, api_key, model_id in MODELS:
    if not api_key or api_key.startswith("your-"):
        print(f"⚠️ 跳过 {model_name} ({platform}) - 无有效API Key")
        results.append({"model": model_name, "platform": platform, "error": "No API key"})
        continue

    print(f"\n{'='*60}")
    print(f"📊 测试: {model_name} ({platform})")
    print(f"{'='*60}")

    model_results = {"model": model_name, "platform": platform}
    total_lat = 0
    total_score = 0
    total_input = 0
    total_output = 0

    for tc in TEST_CASES:
        print(f"\n  ▶ 测试: {tc['name']}")
        result = call_api(endpoint, api_key, model_id, tc["prompt"])

        if not result["success"]:
            print(f"    ❌ 失败: {result.get('error', '')}")
            model_results[tc['name']] = {"score": 0, "latency": result['latency'], "error": result.get('error', '')}
            continue

        # 评分
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

        # 输出摘要
        content_preview = result["content"][:100].replace("\n", " ").strip()
        rt = result.get("reasoning_tokens", 0)
        print(f"    延迟:{result['latency']:>5.1f}s | 得分:{score:>2}/10 | 推理:{rt:>4}t | 输出:{result['output_tokens']:>4}t")
        print(f"    预览: {content_preview}")

        model_results[tc['name']] = {
            "score": score,
            "latency": result["latency"],
            "content": result["content"][:500],
            "reasoning_tokens": result["reasoning_tokens"],
            "output_tokens": result["output_tokens"],
        }

    model_results["avg_latency"] = round(total_lat / len(TEST_CASES), 2)
    model_results["total_score"] = round(total_score, 1)
    model_results["avg_score"] = round(total_score / len(TEST_CASES), 1)
    model_results["total_input_tokens"] = total_input
    model_results["total_output_tokens"] = total_output

    # 成本
    pricing = PRICING.get(model_name, {"input": 2, "output": 8})
    cost = (total_input * pricing["input"] + total_output * pricing["output"]) / 1_000_000
    model_results["cost_yuan"] = round(cost, 4)

    # 综合得分 = 平均分×7 + 效率加分 + 性价比加分
    speed_score = max(0, 10 - model_results["avg_latency"])
    value_score = max(0, min(10, 0.1 / max(cost, 0.0001) / 2))
    composite = model_results["avg_score"] * 7 + speed_score * 1.5 + value_score * 1.5
    model_results["composite_score"] = round(composite, 1)

    print(f"\n  📈 汇总: 均分={model_results['avg_score']} | 均延迟={model_results['avg_latency']}s | 成本=¥{cost} | 综合={model_results['composite_score']}")

    results.append(model_results)

# ============ 输出排名 ============

print("\n\n")
print("=" * 70)
print("🏆 智能体开发模型评测结果")
print("=" * 70)

valid_results = [r for r in results if "error" not in r or not r.get("error")]
valid_results.sort(key=lambda r: r["composite_score"], reverse=True)

print(f"\n{'排名':>4} | {'模型':<22} | {'平台':<6} | {'均分':>4} | {'延迟':>6} | {'成本¥':>8} | {'综合分':>6}")
print("-" * 70)

for i, r in enumerate(valid_results, 1):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    medal = medals.get(i, "  ")
    avg_lat = r.get("avg_latency", 0)
    avg_score = r.get("avg_score", 0)
    cost = r.get("cost_yuan", 0)
    composite = r.get("composite_score", 0)
    print(f"{medal} {i:>2} | {r['model']:<22} | {r['platform']:<6} | {avg_score:>4} | {avg_lat:>5.1f}s | ¥{cost:<6.4f} | {composite:>6}")

# 详细评测表格
print("\n\n📋 各模型每项得分:")
print("-" * 80)
header = f"{'模型':<22} | {'平台':<6}"
for tc in TEST_CASES:
    header += f" | {tc['name'][:8]:>8}"
header += " | {'均分':>4}"
print(header)
print("-" * 80)
for r in valid_results:
    line = f"{r['model']:<22} | {r['platform']:<6}"
    for tc in TEST_CASES:
        tc_result = r.get(tc['name'], {})
        if isinstance(tc_result, dict):
            score = tc_result.get("score", 0)
        else:
            score = 0
        line += f" | {score:>8}"
    line += f" | {r.get('avg_score', 0):>4}"
    print(line)

print("\n\n✅ 评测完成")
