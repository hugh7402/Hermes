"""
思源笔记提取 + 增强 → 00-INBOX/
- 从 /opt/data/INBOX_FILES/ 提取用户笔记
- 帮助文档跳过
- 文件名按层级：父标题-子标题.md
- 增强后留在 00-INBOX/，不混入 concepts
"""
import subprocess, sys, os, shutil, re, json
from pathlib import Path
from datetime import datetime

SIYUAN_DATA = "/opt/data/INBOX_FILES/workspace/data"
VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"
INBOX = f"{VAULT}/00-INBOX"
CONCEPTS = f"{VAULT}/concepts"
EXTRACTED = "/opt/data/.siyuan_extracted"
NOTE_ENHANCE = "/opt/data/note_enhance.py"
INDEX = f"{VAULT}/index.md"
LOG = f"{VAULT}/log.md"

SKIP = [
    "请从这里开始", "常见问题", "隐私政策", "致谢", "数据安全", "性能优化",
    "社区资源", "术语表", "最新进展", "移动端 App", "扩展开发", "编辑器",
    "内容块", "搜索进阶", "自定义外观", "通用操作", "会员特权", "排版元素",
    "优化排版", "通过标题", "什么是", "引用内容块", "在内容块中", "嵌入内容块",
    "文档块和标题", "内容块属性", "数据库表", "类型过滤", "查询语法",
    "忽略索引", "忽略搜索", "图标", "主题", "快捷键", "导入和导出",
    "窗口和页签", "内核参数", "书签和标签", "资源文件", "在浏览器上",
    "模板片段", "Docker 伺服", "内核 API", "日记", "PDF 标注", "超链接",
    "剪藏", "数据历史", "挂件", "虚拟引用", "闪卡", "分享文档",
    "工作空间", "人工智能", "插件", "数据库", "发布服务", "功能特性",
    "云端服务", "对接第三方", "搜索资源文件", "数据同步", "资源文件图床",
    "存储空间", "收集箱", "数据备份", "微信提醒", "限制", "数据可用性保障"
]

def load_extracted():
    if os.path.exists(EXTRACTED):
        return set(Path(EXTRACTED).read_text().strip().split("\n"))
    return set()

def save_extracted(ids):
    Path(EXTRACTED).write_text("\n".join(ids))

def node_to_md(node, level=0):
    md = ""
    ntype = node.get("Type", "")
    props = node.get("Properties", {})
    children = node.get("Children", [])
    
    if ntype == "NodeDocument":
        title = props.get("title", "未命名")
        md += f"# {title}\n\n"
    elif ntype == "NodeHeading":
        text = extract_text(node)
        hlevel = int(props.get("HeadingLevel", 1)) + 1
        md += f"{'#' * hlevel} {text}\n\n"
    elif ntype == "NodeParagraph":
        text = extract_text(node)
        if text.strip():
            md += f"{text}\n\n"
    elif ntype == "NodeListItem":
        list_data = node.get("ListData", {})
        prefix = "1. " if list_data.get("Typ", 1) == 1 else "- "
        text = extract_text(node)
        indent = "  " * (level - 1) if level > 1 else ""
        md += f"{indent}{prefix}{text}\n"
    elif ntype == "NodeBlockquote":
        for line in extract_text(node).split("\n"):
            md += f"> {line}\n"
        md += "\n"
    elif ntype == "NodeCodeBlock":
        lang = props.get("CodeBlockInfo", "")
        md += f"```{lang}\n{extract_text(node)}\n```\n\n"
    elif ntype == "NodeTable":
        md += f"{extract_text(node)}\n\n"
    
    for child in children:
        child_level = level + 1 if ntype in ("NodeList", "NodeListItem") else level
        md += node_to_md(child, child_level)
    return md

def extract_text(node):
    text = ""
    for child in node.get("Children", []):
        if child.get("Type") == "NodeText":
            text += child.get("Data", "")
        else:
            text += extract_text(child)
    return text

def get_title_tree():
    """扫描所有文档，建立 ID → (title, parent_id) 映射和层级链"""
    id_map = {}  # doc_id → (title, parent_doc_id)
    
    for root, dirs, files in os.walk(SIYUAN_DATA):
        for f in files:
            if f.endswith(".sy") and not f.startswith("."):
                filepath = os.path.join(root, f)
                try:
                    node = json.loads(Path(filepath).read_text(encoding='utf-8'))
                    if node.get("Type") == "NodeDocument":
                        doc_id = node["ID"]
                        title = node.get("Properties", {}).get("title", "未命名")
                        
                        # 推断父文档：目录层级
                        rel = os.path.relpath(filepath, SIYUAN_DATA)
                        parts = Path(rel).parts
                        # parts: [notebook, parent.sy] 或 [notebook, parent_dir, child.sy]
                        parent_id = None
                        if len(parts) >= 3:
                            # 子文档在父目录中，父目录名就是父 ID
                            parent_id = parts[-2]
                        
                        id_map[doc_id] = (title, parent_id)
                except:
                    pass
    return id_map

def build_hierarchical_name(doc_id, id_map):
    """构建层级文件名：一级标题-二级标题-三级标题"""
    chain = []
    current = doc_id
    while current:
        if current in id_map:
            title, parent = id_map[current]
            chain.append(title)
            current = parent
        else:
            break
    chain.reverse()  # 从根到叶
    return "-".join(chain)

def collect_user_docs(id_map):
    """收集用户文档，构建层级文件名"""
    docs = []
    for doc_id, (title, parent_id) in id_map.items():
        if any(kw in title for kw in SKIP):
            continue
        fname = build_hierarchical_name(doc_id, id_map)
        filepath = find_sy_file(doc_id)
        docs.append((doc_id, fname, title, filepath))
    return docs

def find_sy_file(doc_id):
    """根据 doc_id 找到 .sy 文件路径"""
    for root, dirs, files in os.walk(SIYUAN_DATA):
        fname = f"{doc_id}.sy"
        if fname in files:
            return os.path.join(root, fname)
    return None

def main():
    os.makedirs(INBOX, exist_ok=True)
    os.makedirs(CONCEPTS, exist_ok=True)
    extracted = load_extracted()
    
    # 建立标题树
    id_map = get_title_tree()
    docs = collect_user_docs(id_map)
    
    if not docs:
        print("📭 无用户笔记")
        return
    
    new_ids = []
    enhanced = 0
    
    for doc_id, fname, title, filepath in docs:
        if doc_id in extracted:
            continue
        
        if not filepath or not os.path.exists(filepath):
            continue
        
        try:
            node = json.loads(Path(filepath).read_text(encoding='utf-8'))
        except:
            continue
        
        md_content = node_to_md(node)
        if not md_content.strip():
            continue
        
        # 文件名：层级中文名
        safe_fname = re.sub(r'[\\/:*?"<>|]', '-', fname)[:120]
        if not safe_fname.endswith(".md"):
            safe_fname += ".md"
        
        out_path = os.path.join(INBOX, safe_fname)
        # 如果已存在，跳过（同文件可能由不同层级路径但内容相同）
        Path(out_path).write_text(md_content, encoding='utf-8')
        print(f"  📥 {safe_fname}")
        
        # 增强
        tmp_concepts = os.path.join(CONCEPTS, f"__tmp_{doc_id}.md")
        shutil.copy2(out_path, tmp_concepts)
        result = subprocess.run(
            ['python3', NOTE_ENHANCE, f"__tmp_{doc_id}.md"],
            cwd=CONCEPTS, capture_output=True, text=True, timeout=300
        )
        
        if os.path.exists(tmp_concepts):
            shutil.move(tmp_concepts, out_path)
            enhanced += 1
            print(f"    ✅ 已增强")
        else:
            print(f"    ⚠️ 增强失败")
        
        new_ids.append(doc_id)
    
    if new_ids:
        save_extracted(extracted | set(new_ids))
        
        total = len(list(Path(INBOX).glob('*.md')))
        if os.path.exists(INDEX):
            content = Path(INDEX).read_text(encoding='utf-8')
            entry = f"- [[00-INBOX/]] — {total} 篇思源笔记"
            old = re.search(r'- \[\[00-INBOX/\]\].*', content)
            if old:
                content = content.replace(old.group(), entry)
            elif "## 实体" in content:
                content = content.replace("## 实体", f'{entry}\n\n## 实体')
            Path(INDEX).write_text(content, encoding='utf-8')
        
        today = datetime.now().strftime('%Y-%m-%d')
        with open(LOG, 'a') as f:
            f.write(f"\n## [{today}] siyuan | 思源入库 {len(new_ids)} 篇\n")
    
    total = len(list(Path(INBOX).glob('*.md')))
    print(f"\n📊 00-INBOX/: {total} 篇思源笔记")

if __name__ == '__main__':
    main()
