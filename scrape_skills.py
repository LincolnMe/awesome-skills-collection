import os
import json
import time
import requests
from datetime import datetime

# GitHub 配置
GITHUB_TOKEN = os.getenv("GH_PAT")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "Awesome-Skills-Collector"
}

# 采集关键词列表
SKILLS_KEYWORDS = [
    "awesome-claude-skills",
    "awesome-agent-skills",
    "agent-skills",
    "claude-code-skills",
    "cursor-rules",
    "ai-agents-list",
    "llm-tools-collection",
    "coding-assistant-resources"
]

TOOLS_KEYWORDS = [
    "ai-coding-tools",
    "developer-productivity",
    "awesome-open-source",
    "programming-resources",
    "developer-tools-list",
    "ai-automation-scripts",
    "workflow-automation",
    "open-source-curated"
]

# 去重状态文件
SEEN_FILE = os.path.join(os.path.dirname(__file__), ".seen.json")


def load_seen():
    """加载已收集的仓库列表"""
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_seen(seen):
    """保存已收集的仓库列表"""
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, ensure_ascii=False)


def search_github(query, sort="stars", order="desc", per_page=100):
    """搜索 GitHub 仓库"""
    url = f"https://api.github.com/search/repositories"
    params = {
        "q": query,
        "sort": sort,
        "order": order,
        "per_page": per_page
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get("items", [])
    except Exception as e:
        print(f"❌ 搜索失败 [{query}]: {e}")
        return []


def collect_repos(keywords, seen_repos, category_label):
    """采集指定关键词的仓库"""
    print(f"\n{'='*60}")
    print(f"🔍 开始采集: {category_label}")
    print(f"{'='*60}")
    
    all_repos = []
    new_count = 0
    
    for keyword in keywords:
        print(f"\n  搜索关键词: {keyword}")
        repos = search_github(keyword)
        
        for repo in repos:
            full_name = repo["full_name"]
            
            # 去重
            if full_name in seen_repos:
                continue
            
            # 过滤掉自己的仓库和一些无关仓库
            if "LincolnMe/awesome-skills-collection" in full_name:
                continue
            if repo.get("private"):
                continue
            
            # 只收集有一定 Star 数的仓库 (>= 100 stars)
            if repo.get("stargazers_count", 0) < 100:
                continue
            
            all_repos.append({
                "name": repo["full_name"].split("/")[-1],
                "owner": repo["full_name"].split("/")[0],
                "full_name": full_name,
                "url": repo["html_url"],
                "stars": repo["stargazers_count"],
                "description": repo.get("description", "N/A") or "暂无描述",
                "language": repo.get("language", "Unknown") or "Unknown",
                "updated": datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
            })
            
            seen_repos.append(full_name)
            new_count += 1
        
        # 避免请求过快被封禁
        time.sleep(1)
    
    # 按 Star 数降序排列
    all_repos.sort(key=lambda x: x["stars"], reverse=True)
    
    print(f"\n✅ 采集完成: 共 {len(all_repos)} 个仓库, 新增 {new_count} 个")
    return all_repos


def generate_markdown(repos, title, filename):
    """生成 Markdown 表格"""
    md_content = f"# {title}\n\n"
    md_content += f"> 每日自动更新的优质开源资源集合\n"
    md_content += f"> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC+8)\n\n"
    md_content += f"## 📊 统计\n\n"
    md_content += f"- **收录总数**: {len(repos)} 个项目\n"
    md_content += f"- **平均 Star 数**: {sum(r['stars'] for r in repos) // max(len(repos), 1):,}\n"
    md_content += f"- **最近更新**: {repos[0]['updated'] if repos else 'N/A'}\n\n"
    md_content += f"## 📋 完整列表\n\n"
    md_content += "| 排名 | 项目名称 | 描述 | Star ⭐ | 语言 | 更新日期 |\n"
    md_content += "|------|----------|------|---------|------|----------|\n"
    
    for idx, repo in enumerate(repos, 1):
        desc = repo["description"].replace("|", "\\|").replace("\n", " ")
        md_content += f"| {idx} | [{repo['name']}](<{repo['url']}>/{repo['owner']}) | {desc} | {repo['stars']:,} | {repo['language']} | {repo['updated']} |\n"
    
    # 添加底部统计
    md_content += f"\n---\n\n"
    md_content += f"## 🏆 Top 10 热门项目\n\n"
    md_content += "| 排名 | 项目名称 | Star ⭐ |\n"
    md_content += "|------|----------|----------|\n"
    
    for idx, repo in enumerate(repos[:10], 1):
        md_content += f"| {idx} | [{repo['name']}](<{repo['url']}>/{repo['owner']}) | {repo['stars']:,} |\n"
    
    md_content += f"\n---\n\n"
    md_content += f"_本文档由 [LincolnMe/awesome-skills-collection](https://github.com/LincolnMe/awesome-skills-collection) 自动维护，每日更新_\n"
    
    # 写入文件
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"\n💾 已更新文件: {filename}")


def main():
    """主函数"""
    print("🚀 开始每日 Skills & Tools 采集...")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载已收集列表
    seen_repos = load_seen()
    initial_count = len(seen_repos)
    
    # 采集两类别数据
    skills_repos = collect_repos(SKILLS_KEYWORDS, seen_repos, "🧠 AI Agent Skills")
    tools_repos = collect_repos(TOOLS_KEYWORDS, seen_repos, "🛠️ 开发者工具")
    
    # 去重合并
    all_repos = skills_repos + tools_repos
    unique_repos = []
    seen_names = set()
    for repo in all_repos:
        if repo["full_name"] not in [r["full_name"] for r in unique_repos]:
            unique_repos.append(repo)
    
    # 按 Star 数重新排序
    unique_repos.sort(key=lambda x: x["stars"], reverse=True)
    
    # 生成 Markdown 文件
    generate_markdown(unique_repos, "🔥 Awesome Skills Collection", "SKILLS.md")
    generate_markdown(tools_repos, "🛠️ Awesome Developer Tools", "TOOLS.md")
    
    # 更新 README
    readme_content = f"""# 🔥 Awesome Skills Collection

> 每日自动更新的优质 AI Agent Skills 与开发者工具集合
> 
> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC+8)

## 📊 最新统计

- **AI Agent Skills**: {len(skills_repos)} 个项目
- **开发者工具**: {len(tools_repos)} 个项目
- **累计收录**: {len(unique_repos)} 个项目

## 📑 快速导航

- [🧠 AI Agent Skills](./SKILLS.md) - 精选 AI 编程助手 Skills
- [🛠️ 开发者工具](./TOOLS.md) - 实用开源工具集合

## 🤖 自动化

本仓库由 GitHub Actions 自动维护，每日 00:00 UTC (北京 08:00) 自动采集、更新。

### 工作流程

```yaml
.on:
  schedule:
    - cron: '0 0 * * *'  # 每天 UTC 00:00
  workflow_dispatch:     # 支持手动触发
```

---

_Automated by [LincolnMe](https://github.com/LincolnMe)_
"""
    
    with open(os.path.join(os.path.dirname(__file__), "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"\n💾 已更新文件: README.md")
    
    # 保存去重状态
    save_seen(seen_repos)
    
    print(f"\n✨ 完成! 新增 {len(seen_repos) - initial_count} 个仓库")


if __name__ == "__main__":
    main()
