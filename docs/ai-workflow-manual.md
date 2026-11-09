# AI 工作流使用手册

这份手册用于日常调用你的 Codex skills。你只需要用自然语言说明目标；Codex 会根据触发词选择对应 skill。遇到跨阶段任务时，先用 `research-workflow` 做路由。

## 一句话使用

| 你想做什么 | 可以这样说 | 主要 skill |
|---|---|---|
| 开始一整套科研流程 | 开始科研工作流，从检索到归档 | `research-workflow` |
| 今日论文推荐 | 今日论文推荐 / start my day | `start-my-day` |
| 联网找新论文 | 联网查文献，找最近关于 XXX 的论文 | `nature-academic-search` |
| 下载或获取全文 | 帮我下载这篇论文全文 | `nature-downloader` |
| 读论文或全文翻译 | 读这篇论文，做中英文对照 | `nature-reader` |
| 生成 Obsidian 深度笔记 | 分析这篇论文并归档到 Obsidian | `paper-analyze` |
| 从 Zotero 生成笔记 | 从 Zotero 生成这篇论文的 Obsidian 笔记 | `zotero-paper-note` |
| 编辑 Obsidian 格式 | 把这段整理成带 properties、wikilinks 和 callouts 的 Obsidian Markdown | `obsidian-markdown` |
| 查自己的论文笔记 | 在我的论文笔记中查找 XXX | `paper-search` |
| 提取论文原图 | 从 arXiv 源码提取原图 | `extract-paper-images` |
| 写论文段落 | 帮我起草引言/摘要/讨论 | `nature-writing` |
| 润色已有文字 | 润色这段学术英文 / 翻译成论文英语 | `nature-polishing` |
| 做投稿级图表 | 帮我做 Nature 风格论文图 | `nature-figure` |
| 审稿人视角预审 | 按审稿人视角评估这篇论文 | `nature-reviewer` |
| 回复审稿意见 | 帮我写逐点回复 | `nature-response` |
| 论文做 PPT | 把这篇论文做成组会 PPT | `nature-paper2ppt` |
| 查 CNKI | 在 CNKI 搜索/下载/导出 XXX | `cnki-*` |

## 推荐主流程

```text
发现论文 -> 获取全文 -> 阅读理解 -> 归档笔记 -> 本地检索 -> 写作投稿
```

1. 发现论文：用 `start-my-day` 做个性化每日推荐；用 `nature-academic-search` 做临时联网检索。
2. 获取全文：英文论文优先 `nature-downloader`；中文文献明确说 CNKI，会触发对应 `cnki-*` skill。
3. 阅读理解：只是读、翻译、做中英文对照，用 `nature-reader`。
4. 归档笔记：要写入 Obsidian、评分、提炼方法和局限，用 `paper-analyze`。
5. Zotero 来源：如果论文已经在 Zotero，用 `zotero-paper-note`。
6. 本地复用：查自己已有笔记，用 `paper-search`。
7. 写作投稿：起草用 `nature-writing`，润色用 `nature-polishing`，图表用 `nature-figure`，审稿和回复用 `nature-reviewer` / `nature-response`。

## 个人 Skill

### `research-workflow`

用于多阶段任务路由。适合你还没确定应该先检索、读论文、归档还是写作时使用。

示例：

```text
开始科研工作流，我想围绕海洋热浪和渔业影响找论文、读几篇并归档。
```

### `start-my-day`

生成当天的个性化论文推荐笔记，读取你的研究画像和已有 Obsidian 笔记，避免重复推荐。

示例：

```text
今日论文推荐。
开始今天的论文阅读，重点看海洋热浪、冷浪和知识图谱。
```

注意：它只做每日发现，不会自动给所有推荐论文生成深度笔记。看中某篇后再说“分析并归档这篇”。

### `paper-analyze`

把一篇论文变成结构化 Obsidian 深度笔记，包括核心信息、方法、实验、局限、评分、研究启发和可选图谱更新。

示例：

```text
分析 arXiv:2601.xxxxx，并生成 Obsidian 论文笔记。
深度分析这篇 PDF，归档到我的论文笔记。
```

边界：只是读论文或翻译全文时，不用它，用 `nature-reader`。

### `paper-search`

只搜索你的本地 Obsidian 论文笔记，不联网。

示例：

```text
在我的论文笔记中查找关于 marine heatwave detection 的方法。
我的笔记里有没有用知识图谱分析渔业影响的论文？
```

边界：找新论文用 `nature-academic-search`。

### `extract-paper-images`

从 arXiv 源码包或 PDF 提取论文原图，生成图片目录和索引。

示例：

```text
从 arXiv 源码提取这篇论文的原图。
导出这篇 PDF 里的论文图片，放到对应 Obsidian 笔记旁边。
```

### `zotero-paper-note`

从已有 Zotero 条目和本地 PDF 创建 Obsidian 分析笔记，保留 Zotero item link。

示例：

```text
从 Zotero 生成这篇论文的 Obsidian 笔记。
把 Zotero 里标题包含 XXX 的论文导入为分析笔记。
```

## Nature Skill

| Skill | 什么时候用 |
|---|---|
| `nature-academic-search` | 多源文献检索、引文核对、查最新论文、PubMed/CrossRef/arXiv/Scopus 等 |
| `nature-downloader` | 合法下载全文、复用学校/图书馆访问、整理 PDF |
| `nature-reader` | 全文阅读、翻译、中英文对照、图表就近解释 |
| `nature-ref-verifier` | 批量核验参考文献字段、DOI、年份、页码 |
| `nature-citation` | 给段落补引用，找 Nature/CNS/高质量文献支撑 |
| `nature-writing` | 从结果、图表、笔记起草摘要、引言、讨论等 |
| `nature-polishing` | 润色、翻译、重写已有学术段落 |
| `nature-figure` | 论文图、机制图、投稿级图表和图形摘要 |
| `nature-statistics` | 统计分析、统计方法检查、结果表达 |
| `nature-data` | 数据可用性声明、数据仓库、FAIR 元数据 |
| `nature-reviewer` | 投稿前模拟审稿，找 novelty、rigor、evidence 问题 |
| `nature-response` | 返修信、逐点回复、rebuttal、cover letter |
| `nature-paper2ppt` | 论文汇报、组会 PPT、文献报告 PPT |

## CNKI Skill

明确说“CNKI / 知网”时使用：

| Skill | 用途 |
|---|---|
| `cnki-search` | 普通关键词检索 |
| `cnki-advanced-search` | 作者、题名、期刊、日期、核心类别等高级检索 |
| `cnki-parse-results` | 解析当前检索结果页 |
| `cnki-navigate-pages` | 翻页、改排序 |
| `cnki-paper-detail` | 抽取论文详情、摘要、关键词、基金等 |
| `cnki-download` | 下载授权范围内的 PDF/CAJ |
| `cnki-export` | 导出 RIS 或推送到 Zotero |
| `cnki-journal-search` | 查期刊 |
| `cnki-journal-index` | 查期刊收录、核心、影响因子等 |
| `cnki-journal-toc` | 看某期目录、下载目录页 |

## 触发边界

| 容易混的请求 | 正确选择 |
|---|---|
| “读这篇论文” | `nature-reader` |
| “分析并归档到 Obsidian” | `paper-analyze` |
| “在我的笔记里有没有” | `paper-search` |
| “网上找最新论文” | `nature-academic-search` |
| “今日个性化推荐” | `start-my-day` |
| “自动持续文献流水线” | 默认不用；`nature-literature-pipeline` 目前保留但不启用 |
| “已有 Zotero 条目生成笔记” | `zotero-paper-note` |
| “单独提取原图文件” | `extract-paper-images` |

## 维护命令

在仓库目录运行：

```bash
cd /path/to/academic-reading-workflow

./scripts/skills.sh list
./scripts/skills.sh check
./scripts/skills.sh install
./scripts/skills.sh update-nature
./scripts/skills.sh update-obsidian
./scripts/skills.sh enable <skill-name>
./scripts/skills.sh disable <skill-name>
```

常用规则：

- 改自己的 skill：编辑 `skills/`，提交到个人仓库。
- 更新 Nature：运行 `./scripts/skills.sh update-nature`，不直接改 `vendor/nature-skills/`。
- 更新 Obsidian 通用格式 Skill：运行 `./scripts/skills.sh update-obsidian`，不直接改 `vendor/obsidian-skills/`。
- 启停 skill：改 `config/active-skills.txt`，或用 `enable` / `disable` 命令。
- 新增或改 MCP：改 `~/.codex/config.toml`，通常需要新开 Codex task 才会加载。
- 不再让 CC Switch 管 Codex skill/MCP；CC Switch 只保留旧文件和回退配置。
- Windows 迁移和 PowerShell 命令见 `docs/windows-migration.md`。

## 推荐开口模板

```text
开始科研工作流：我的目标是 XXX，先帮我检索，再挑 3 篇值得读的。
```

```text
今日论文推荐：重点关注 XXX，输出到 Obsidian。
```

```text
读这篇论文：请做中英文对照，图表放在相关段落附近。
```

```text
分析并归档这篇论文：生成 Obsidian 深度笔记，保留方法、实验、局限、评分和对我研究的启发。
```

```text
在我的论文笔记中查找：有没有关于 XXX 的方法或数据集？
```

```text
帮我起草讨论部分：基于这些结果和图表，按 Nature 风格组织论证。
```
