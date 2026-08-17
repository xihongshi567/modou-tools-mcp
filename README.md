# modou-tools-mcp

**给中文开发者的全球技术情报台。**

一个 MCP server，装进 Agent 就能采集全球技术情报：英文侧看 GitHub 趋势、arXiv 论文、HN 热帖、Exa 语义搜索、SEC 美股财报；中文侧深入掘金、知乎、B站、A股财报。全部工具 **零 API key、零费用、国内直连**——这是它跟 Exa / Firecrawl / Perplexity 这类要订阅要 key 的方案最大的区别。

## 快速开始（云端托管版）

在支持 MCP 的客户端（Claude Code / Cherry Studio / Kimi Playground 等）中添加如下配置即可连接，无需本地安装任何依赖：

```json
{
  "mcpServers": {
    "modou-tools": {
      "command": "uvx",
      "args": ["modou-tools-mcp@latest"]
    }
  }
}
```

## 本地部署（完整功能）

云端托管版为兼容性考虑不包含本地搜索（见[已知限制](#已知限制)）。需要完整功能时，本地运行：

```bash
# 本机 Python 环境（建议 3.10+）
pip install modou-tools-mcp
```

```json
{
  "mcpServers": {
    "modou-tools": {
      "command": "uvx",
      "args": ["modou-tools-mcp@latest"]
    }
  }
}
```

或使用仓库源码直接运行（开发模式）：

```bash
git clone https://github.com/xihongshi567/modou-tools-mcp
cd modou-tools-mcp
pip install -e .
claude mcp add modou-tools -- python "D:/okok/modou-tools-mcp/src/modou_tools_mcp/server.py"
```

## 工具清单

| 工具 | 用途 | 网络 |
|------|------|------|
| `web_search` | 中文网页搜索（SearXNG 聚合，**仅本地部署可用**） | 本地 |
| `fetch_page` | 网页正文提取，去噪输出 Markdown（trafilatura） | 直连 |
| `fetch_hot_topics` | 热榜聚合（知乎/B站/GitHub/HN） | 直连 |
| `github_search_repos` / `github_compare_repos` | GitHub 仓库趋势/对比（60次/h，配 token 5000次/h） | 直连 |
| `arxiv_search` | arXiv 论文检索（支持分类/高级语法，按相关度或最新排序） | 直连 |
| `exa_search` | 英文语义搜索（Exa 免费端点，免 key） | 直连 |
| `juejin_recommended` / `juejin_by_category` | 掘金技术社区文章发现（推荐流/分类浏览） | 直连 |
| `sec_company_facts` / `sec_compare_companies` | 美股财报（SEC EDGAR 免费） | 可用，较慢 |
| `cninfo_company_profile` / `cninfo_financial_analysis` / `cninfo_compare_companies` | A股财报（东方财富公开接口） | 直连 |
| `parse_pdf` | PDF 报告 → Markdown + 表格（PyMuPDF） | 本地 |

所有工具返回统一结构：成功 `{"ok": true, ...}`；失败 `{"ok": false, "error": "...", "detail": "..."}`。

## 一个完整场景：调研"RAG 技术方向"

Agent 拿到一个调研任务，modou-tools 全链路支撑：

1. **开题**：`exa_search("retrieval augmented generation trends 2026")` 摸全球风向
2. **补学术**：`arxiv_search("cat:cs.CL AND all:RAG")` 看最新论文
3. **看社区**：`juejin_recommended` / `fetch_hot_topics(zhihu)` 看国内在聊什么
4. **抓原文**：`fetch_page(url)` 抓关键文章正文
5. **读报告**：`parse_pdf(url)` 解析 PDF 白皮书
6. **查数据**：`github_search_repos("RAG framework")` 看项目热度

## 设计原则

- **纯采集**：不做 LLM 加工（Agent 本身会总结提炼），server 保持轻量
- **零依赖**：除可选 GITHUB_TOKEN 外不需要任何 key；Exa 走官方免费端点
- **错误不打断**：单工具失败返回结构化错误，Agent 可换路重试

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `GITHUB_TOKEN` | GitHub API token，提升速率限制至 5000 次/h | 可选 |

## 开发

```bash
# 离线冒烟（结构检查，不依赖网络）
python smoke_test.py

# 在线验证全部工具
python scripts/verify_online.py
```

## 已知限制

- `web_search` 依赖本地 SearXNG（`docker start searxng`），云端托管版该工具不可用
- GitHub 无 token 仅 60 次/h（配额耗尽时返回 403 提示）；SEC 偶发 503 可重试；东方财富接口偶发断连（内置重试 3 次）
- Exa 免费端点有配额限制，大量调用时可能受限
- 掘金站内搜索接口需登录态，未提供；掘金文章全文需配合 `fetch_page`
- 扫描版 PDF 返回 `is_scanned=true` 警告（无 OCR）
