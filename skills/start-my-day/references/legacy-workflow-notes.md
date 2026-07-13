# Legacy Workflow Notes

These notes preserve user-tested workflow experience from the pre-reorganization skill. Current `SKILL.md` instructions take precedence. Use this file only when the active task needs detailed templates, scoring heuristics, troubleshooting notes, or historical edge-case handling. Do not reintroduce obsolete tool-specific setup, hard-coded private paths, or deprecated scripts.

Source skill: `start-my-day`.

---

## Contents

- Language Setting / 语言设置
  - Language Detection
- Resolve OBSIDIAN_VAULT_PATH if not set in the current session
- Codex bash sessions do not source ~/.zshrc automatically
- Resolve Python from paper conda environment
- Read conda_env from config; default to "paper"
- Read language from config
- Default to Chinese if not set
- Set note filename suffix based on language
- 目标
- 搜索策略
- 工作流程
  - 工作流程概述
  - 步骤1：收集上下文（静默）
  - 步骤2：搜索论文
    - 2.1 搜索策略
    - 2.2 执行搜索和筛选
- 使用 Python 脚本搜索、解析和筛选论文
- 首先切换到 skill 目录，然后执行脚本
  - 步骤3：读取筛选结果
    - 3.1 读取 JSON 结果
- 读取筛选结果
    - 3.2 评分说明
  - 步骤4：生成今日推荐笔记
    - 4.1 读取筛选结果
    - 4.2 创建推荐笔记文件
    - 4.2 推荐笔记结构
      - 4.2.1 今日概览（放在论文列表之前）
  - Today's Overview
  - 今日概览
      - 4.2.2 所有论文统一格式
    - [[Note_Filename|Paper Title as Displayed]]
    - [[Note_Filename|论文标题显示名]]
      - 4.2.3 前三篇论文插入图片和调用详细分析
- 在 论文笔记/ 目录中搜索已有笔记
- 搜索方式：
- 1. 按论文ID搜索（如 2602.23351）
- 2. 按论文标题搜索（模糊匹配）
- 3. 按论文标题关键词搜索
    - [[已有论文名称]]
    - [[Note_Filename|Paper Title Display Name]]
  - 步骤5：自动链接关键词（可选）
- 步骤1：扫描现有笔记
- 步骤2：生成推荐笔记（正常流程）
- ... 使用 search_arxiv.py 搜索论文 ...
- 步骤3：链接关键词（新增步骤）
- 重要规则
- 与其他 skills 的区别
  - start-my-day (本skill)
  - paper-analyze (深度分析skill)
- 使用说明
  - 自动执行流程
  - 临时文件清理
  - 依赖项
  - 脚本说明
    - search_arxiv.py
    - scan_existing_notes.py
    - link_keywords.py
- 首先切换到 skill 目录，然后执行脚本
- 步骤1：扫描现有笔记
- 步骤2：生成推荐笔记（正常流程）
- ... 使用 search_arxiv.py 搜索论文 ...
- 步骤3：链接关键词（新增步骤）
    - 关键词链接实现（新增！）
- 步骤1：扫描现有笔记
- 步骤2：生成推荐笔记（正常流程）
- ... 使用 search_arxiv.py 搜索论文 ...
- 步骤3：链接关键词（新增步骤）

---
# Language Setting / 语言设置

This skill supports both Chinese and English reports. The language is determined by the `language` field in your config file:

- **Chinese (default)**: Set `language: "zh"` in config
- **English**: Set `language: "en"` in config

The config file should be located at: `$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml`

## Language Detection

At the start of execution, read the config file to detect the language setting:

```bash
# Resolve OBSIDIAN_VAULT_PATH if not set in the current session
# Codex bash sessions do not source ~/.zshrc automatically
if [ -z "$OBSIDIAN_VAULT_PATH" ]; then
    [ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" 2>/dev/null || true
    [ -f "$HOME/.bash_profile" ] && source "$HOME/.bash_profile" 2>/dev/null || true
fi

# Resolve Python from paper conda environment
# Read conda_env from config; default to "paper"
CONDA_ENV=$(grep -E "^\s+conda_env:" "$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml" | awk '{print $2}' | tr -d '"')
if [ -z "$CONDA_ENV" ]; then CONDA_ENV="paper"; fi
PYTHON="$HOME/anaconda3/envs/$CONDA_ENV/bin/python"
if [ ! -f "$PYTHON" ]; then
    echo "Warning: conda env '$CONDA_ENV' not found, falling back to system python"
    PYTHON="python"
fi

# Read language from config
LANGUAGE=$(grep -E "^\s*language:" "$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml" | awk '{print $2}' | tr -d '"')

# Default to Chinese if not set
if [ -z "$LANGUAGE" ]; then
    LANGUAGE="zh"
fi

# Set note filename suffix based on language
if [ "$LANGUAGE" = "en" ]; then
    NOTE_SUFFIX="paper-recommendations"
else
    NOTE_SUFFIX="论文推荐"
fi
```

Then use this language setting throughout the workflow:
- When generating notes, pass `--language $LANGUAGE` to scripts
- Use appropriate section headers in the generated notes

---

# 目标
帮助用户开启他们的研究日，搜索最近一个月和最近一年的极火、极热门、极优质论文，生成推荐笔记。

# 搜索策略

**核心原则**：Semantic Scholar 为主 + CNKI 为辅 + arXiv 补充，确保论文与研究领域高度相关。

搜索源优先级：
1. **Semantic Scholar（主）**：按领域查询模板精准搜索，覆盖面广、引用数据丰富
2. **CNKI（辅）**：中文期刊论文，需 chrome-devtools MCP 支持
3. **arXiv（补）**：关键词搜索（非分类搜索），补充预印本论文

配置文件 `research_interests.yaml` 中的 `search_strategy` 字段控制搜索行为：
- `order`: 搜索源优先级
- `s2_queries`: 每个领域的 S2 查询模板
- `arxiv_search_mode`: arXiv 搜索模式（keyword 或 category）

# 工作流程

## 工作流程概述

本 skill 使用 Python 脚本调用 Semantic Scholar API（主）和 arXiv API（补）搜索论文，解析结果并根据研究兴趣进行筛选和评分。CNKI 搜索通过 chrome-devtools MCP 执行。

## 步骤1：收集上下文（静默）

1. **获取今日日期**
   - 确定当前日期（YYYY-MM-DD格式）

2. **读取研究配置**
   - 读取 `$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml`（注意：文件名是 interests 不是 interest）获取研究领域
   - 提取：关键词、类别和优先级

3. **扫描现有笔记构建索引**
   - 扫描 `论文笔记/` 目录下的所有 `.md` 文件
   - 提取笔记标题（从文件名和frontmatter的title字段）
   - 构建关键词到笔记路径的映射表，用于后续自动链接
   - 优先使用 frontmatter 中的 title 字段，其次使用文件名

## 步骤2：搜索论文

### 2.1 搜索策略

按配置文件中的 `search_strategy.order` 依次搜索：

1. **Semantic Scholar（主）**
   - 使用配置中 `s2_queries` 的领域查询模板
   - 每个领域多个查询，覆盖不同子方向
   - 搜索最近365天论文 + 过去730天高引用论文
   - 每个查询返回最多50篇论文

2. **CNKI（辅）** — 通过 chrome-devtools MCP 执行
   - 使用 `cnki-search` skill 搜索中文期刊
   - 搜索最近30天论文
   - 每日最多2篇中文论文
   - 必须匹配配置中的期刊列表

3. **arXiv（补）**
   - 使用领域关键词进行关键词搜索（非分类搜索）
   - 搜索最近30天论文
   - 仅补充 S2 未覆盖的预印本

### 2.2 执行搜索和筛选

使用 `scripts/search_arxiv.py` 脚本完成 S2 + arXiv 搜索、解析和筛选：

```bash
# 使用 Python 脚本搜索、解析和筛选论文
# 首先切换到 skill 目录，然后执行脚本
cd "$SKILL_DIR"
$PYTHON scripts/search_arxiv.py \
  --config "$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml" \
  --output arxiv_filtered.json \
  --max-results 200 \
  --top-n 10 \
  --categories "physics.ao-ph,cs.AI,cs.LG,cs.CV" \
  --target-date "{目标日期}"
```

**脚本功能**：
1. **Step 1: Semantic Scholar 领域查询（主）**
   - 从配置读取 `s2_queries` 查询模板
   - 每个领域执行多个精准查询
   - 搜索最近365天 + 过去730天高引用论文
   - 按引用数排序，保留高影响力论文

2. **Step 2: arXiv 关键词搜索（补充）**
   - 从领域关键词提取英文关键词
   - 在 arXiv 中搜索最近30天论文
   - 仅补充 S2 未覆盖的预印本

3. **Step 3: 合并、去重和评分**
   - 合并 S2 和 arXiv 结果
   - 按标题和 arXiv ID 去重
   - 计算综合推荐评分（相关性40%、新近性20%、热门度30%、质量10%）
   - 按评分排序，保留前10篇

**输出**：
- `arxiv_filtered.json` - 筛选后的论文列表（JSON 格式）
- 每篇论文包含：
  - 论文ID、标题、作者、摘要
  - 发布日期、分类
  - 相关性评分、新近性评分、热门度评分、质量评分
  - 最终推荐评分、匹配的领域

## 步骤3：读取筛选结果

### 3.1 读取 JSON 结果

从 `arxiv_filtered.json` 中读取筛选和评分后的论文列表：

```bash
# 读取筛选结果
cat arxiv_filtered.json
```

**结果包含**：
- `total_found`: 搜索到的总论文数
- `total_filtered`: 筛选后的论文数
- `top_papers`: 前10篇高评分论文，每篇包含：
  - 论文ID、标题、作者、摘要
  - 发布日期、分类
  - 相关性评分、新近性评分、质量评分
  - 最终推荐评分、匹配的领域、匹配的关键词

### 3.2 评分说明

综合多个维度的评分：

```yaml
推荐评分 =
  相关性评分: 40%
  新近性评分: 20%
  热门度评分: 30%
  质量评分: 10%
```

**评分细则**：

1. **相关性评分** (40%)
   - 与研究兴趣的匹配程度
   - 标题关键词匹配：每个+0.5分
   - 摘要关键词匹配：每个+0.3分
   - 类别匹配：+1.0分
   - 最高分：~3.0

2. **新近性评分** (20%)
   - 最近30天内：+3分
   - 30-90天内：+2分
   - 90-180天内：+1分
   - 180天以上：0分

3. **热门度评分** (30%)
   - （如果数据可用）引用数 > 100：+3分
   - 引用数 50-100：+2分
   - 引用数 < 50：+1分
   - 无引用数据：0分
   - 或者基于发布后的时间推断（最近7天内的热门新论文）：+2分

4. **质量评分** (10%)
   - 从摘要推断：显著创新：+3分
   - 明确方法：+2分
   - 一般性工作：+1分
   - 或者读取已有笔记的质量评分

**最终推荐评分** = 相关性(40%) + 新近性(20%) + 热门度(30%) + 质量(10%)

## 步骤4：生成今日推荐笔记

### 4.1 读取筛选结果

从 `arxiv_filtered.json` 中读取筛选后的论文列表：
- 包含前 10 篇高评分论文
- 每篇论文包含完整信息：ID、标题、作者、摘要、评分、匹配领域

### 4.2 创建推荐笔记文件

1. **创建推荐笔记文件**
   - 文件名（根据语言设置）：
     - 中文（`language: "zh"`）：`Daily_paper/YYYY-MM-DD论文推荐.md`
     - 英文（`language: "en"`）：`Daily_paper/YYYY-MM-DD-paper-recommendations.md`
   - 使用变量：`Daily_paper/YYYY-MM-DD${NOTE_SUFFIX}.md`（其中 `NOTE_SUFFIX` 在语言检测阶段已设置）
   - 必须包含属性：
     - `keywords`: 当天推荐论文的关键词（逗号分隔，从论文标题和摘要中提取）
     - `tags`: ["llm-generated", "daily-paper-recommend"]

2. **检查论文是否值得详细写**
   - **很值得读的论文**：推荐评分 >= 7.5 或特别推荐的论文
   - **一般推荐论文**：其他论文

3. **检查论文是否已有笔记**
   - 搜索 `论文笔记/` 目录
   - 查找是否有该论文的详细笔记
   - 如果已有笔记：简略写，引用已有笔记
   - 如果无笔记：
     - 很值得读：在推荐笔记中写详细部分
     - 一般推荐：只写基本信息

### 4.2 推荐笔记结构

笔记文件结构如下：

```markdown
---
keywords: [关键词1, 关键词2, ...]
tags: ["llm-generated", "daily-paper-recommend"]
---

[具体论文推荐列表...]
```

#### 4.2.1 今日概览（放在论文列表之前）

在论文列表之前，添加一个概览部分，总结今日推荐论文的整体情况。

**根据 `$LANGUAGE` 设置选择语言：**

**English (`language: "en"`)**:
```markdown
## Today's Overview

Today's {paper_count} recommended papers focus on **{direction1}**, **{direction2}**, and **{direction3}**.

- **Overall Trends**: {summary of research trends}
- **Quality Distribution**: Scores range from {min}-{max}, {quality assessment}.
- **Research Hotspots**:
  - **{hotspot1}**: {description}
  - **{hotspot2}**: {description}
  - **{hotspot3}**: {description}
- **Reading Suggestions**: {reading order recommendations}
```

**Chinese (`language: "zh"`)**:
```markdown
## 今日概览

今日推荐的{论文数量}篇论文主要聚焦于**{主要研究方向1}**、**{主要研究方向2}**和**{主要研究方向3}**等前沿方向。

- **总体趋势**：{总结今日论文的整体研究趋势}
- **质量分布**：今日推荐的论文评分在 {最低分}-{最高分} 之间，{整体质量评价}。
- **研究热点**：
  - **{热点1}**：{简要描述}
  - **{热点2}**：{简要描述}
  - **{热点3}**：{简要描述}
- **阅读建议**：{给出阅读顺序建议}
```

**说明**：
- 基于筛选出的前10篇论文的标题、摘要和评分进行总结
- 提取共同的研究主题和趋势
- 给出合理的阅读顺序建议

#### 4.2.2 所有论文统一格式

所有论文按评分从高到低排列，使用统一格式

**根据 `$LANGUAGE` 设置选择标签语言：**

**English (`language: "en"`)**:
```markdown
### [[Note_Filename|Paper Title as Displayed]]
- **Authors**: [author list]
- **Affiliation**: [institution names, extracted from paper source or arXiv page]
- **Links**: [DOI](url)
- **Source**: [journal name]
- **Zotero**: --  ← fill with zotero://select/items/0_{key} after manual import
- **Note**: [[existing_note_path|short title]] or --

**One-line Summary**: [one sentence summarizing the core contribution]

**Core Contributions**:
- [contribution 1]
- [contribution 2]
- [contribution 3]

**Key Results**: [most important results from abstract]

---
```

**Chinese (`language: "zh"`)**:
```markdown
### [[Note_Filename|论文标题显示名]]
- **作者**：[作者列表]
- **机构**：[机构名称，从论文源码或 arXiv 页面提取]
- **链接**：[DOI](链接)
- **来源**：[期刊名]
- **Zotero**：--  ← 手动导入后填写 zotero://select/items/0_{key}
- **笔记**：[[已有笔记路径|简称]] 或 --

**一句话总结**：[一句话概括论文的核心贡献]

**核心贡献/观点**：
- [贡献点1]
- [贡献点2]
- [贡献点3]

**关键结果**：[从摘要中提取的最重要结果]

---
```

**重要格式规则**：
- **Wikilink 必须使用 display alias**：`[[File_Name|Display Title]]`，不要使用 bare `[[File_Name]]`（下划线会直接显示，影响阅读）
- **图片必须使用 Obsidian wikilink 嵌入语法**：`![[filename.png|600]]`，**禁止**使用 `![alt](path%20encoded)` 格式（URL 编码在 Obsidian 中不工作）
- **机构信息**：从论文 TeX 源码的 `\author` 或 `\affiliation` 字段提取；若 arXiv API 未提供，从下载的源码包读取
- **不要使用 `---` 作为"无数据"占位符**：使用 `--` 代替（三个短横线会被 Obsidian 解析为分隔线）

#### 4.2.3 前三篇论文插入图片和调用详细分析

对于前3篇论文（评分最高的3篇）：

**步骤0：检查论文是否已有笔记**
```bash
# 在 论文笔记/ 目录中搜索已有笔记
# 搜索方式：
# 1. 按论文ID搜索（如 2602.23351）
# 2. 按论文标题搜索（模糊匹配）
# 3. 按论文标题关键词搜索
```

**步骤1：根据检查结果决定处理方式**

如果已有笔记：
- 不生成新的详细报告
- 使用已有笔记路径作为 wikilink
- 在推荐笔记的"详细报告"字段引用已有笔记
- 检查是否需要提取图片（如果没有 images 目录或 images 目录为空）
  - 如果需要图片：调用 `extract-paper-images`
  - 如果已有图片：使用现有图片

如果没有笔记：
- 调用 `extract-paper-images` 提取图片
- 调用 `paper-analyze` 生成详细报告
- 在推荐笔记中添加图片和详细报告链接

**步骤2：在推荐笔记中插入图片和链接**

**如果已有笔记**：
```markdown
### [[已有论文名称]]
- **作者**：[作者列表]
- **机构**：[机构名称]
- **链接**：[DOI](链接)
- **来源**：[期刊名]
- **Zotero**：--  ← 用户手动导入后填写 zotero://select/items/0_{key}
- **笔记**：[[已有笔记路径|简称]]

**一句话总结**：[一句话概括论文的核心贡献]

![[existing_image_filename.png|600]]

**核心贡献/观点**：
...
```

**如果没有笔记**：
```markdown
### [[Note_Filename|Paper Title Display Name]]
- **作者**：[作者列表]
- **机构**：[机构名称]
- **链接**：[DOI](链接)
- **来源**：[期刊名]
- **Zotero**：--  ← 用户手动导入后填写 zotero://select/items/0_{key}
- **笔记**：[[论文笔记/[domain]/[note_filename]|Short Title]] (自动生成)

**一句话总结**：[一句话概括论文的核心贡献]

![[paperID_fig1.png|600]]

**核心贡献/观点**：
...
```

**注意**：如果论文PDF无法下载（付费墙），则跳过图片插入，不显示 `![[...]]` 行。

**图片格式规则（重要！）**：
- **必须使用 Obsidian wikilink 嵌入语法**：`![[filename.png|600]]`
- **禁止使用 markdown 图片语法**：~~`![alt](path%20with%20encoding)`~~ — URL 编码（`%20`, `%26`）在 Obsidian 中不工作
- 图片文件名示例：`2603.24124_fig1.png`
- Obsidian 会自动在 vault 中搜索匹配的文件名，无需写完整路径

**详细报告说明**：
- 报告路径：`论文笔记/[论文分类]/[note_filename].md`
- **重要**：使用 JSON 中的 `note_filename` 字段拼接 wikilink
- **必须使用 display alias**：`[[论文笔记/[domain]/[note_filename]|Short Title]]`
  - 正确：`[[论文笔记/大模型/Hypothesis-Conditioned_Query_Rewriting|Hypothesis-Conditioned Query Rewriting]]`
  - 错误：`[[论文笔记/大模型/Hypothesis-Conditioned_Query_Rewriting_for_Decision-Useful_Retrieval]]`（下划线直接显示，不美观）
- 详细报告由 `paper-analyze` 自动生成

**机构/Affiliation 提取**：
- 从下载的 arXiv 源码包（`.tar.gz`）中的 `.tex` 文件提取 `\author` 和 `\affiliation` 字段
- 若源码不可用，从 arXiv 页面 HTML 提取
- 若仍无法获取，标记为 `--`（使用两个短横线，**不要用三个** `---`，因为 Obsidian 会将其解析为分隔线）

## 步骤5：自动链接关键词（可选）

在生成推荐笔记后，自动链接关键词到现有笔记：

```bash
# 步骤1：扫描现有笔记
cd "$SKILL_DIR"
$PYTHON scripts/scan_existing_notes.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --output existing_notes_index.json

# 步骤2：生成推荐笔记（正常流程）
# ... 使用 search_arxiv.py 搜索论文 ...

# 步骤3：链接关键词（新增步骤）
$PYTHON scripts/link_keywords.py \
  --index existing_notes_index.json \
  --input "Daily_paper/YYYY-MM-DD${NOTE_SUFFIX}.md" \
  --output "Daily_paper/YYYY-MM-DD${NOTE_SUFFIX}_linked.md"
```

**注意**：
- 关键词链接脚本会自动跳过 frontmatter、标题行、代码块
- 过滤通用词（and, for, model, learning 等）
- 保留已有 wikilink 不被修改

# 重要规则

- **搜索策略**：S2 为主 + CNKI 为辅 + arXiv 补充，确保论文高度相关
- **综合推荐评分**：结合相关性、新近性、热门度、质量四个维度
- **文件名以日期**：保持 `Daily_paper/YYYY-MM-DD${NOTE_SUFFIX}.md` 格式（中文：`论文推荐`，英文：`paper-recommendations`）
- **添加今日概览**：在推荐笔记开头添加"## 今日概览"部分，总结今日论文的主要研究方向、总体趋势、质量分布、研究热点和阅读建议
- **按评分排序**：所有论文按推荐评分从高到低排列
- **前3篇特殊处理**：
  - 论文名称用 wikilink 格式：`[[论文名字]]`
  - 尝试下载PDF并提取图片（付费墙论文可能无法获取PDF，此时跳过图片）
  - 自动调用 `paper-analyze` 生成详细报告
  - 在"详细报告"字段显示 wikilink 关联
  - 在"Zotero"字段保留占位符 `--`，用户手动通过浏览器 Connector 导入后填写 `zotero://select/items/0_{key}`
- **其他论文**：只写基本信息，不插入图片
- **保持快速**：让用户快速了解当日推荐
- **避免重复**：检查已推荐论文
- **自动关键词链接**：
  - 在生成推荐笔记后，自动扫描现有笔记
  - 将文本中的关键词（如 BLIP、CLIP 等）替换为 wikilink
  - 示例：`BLIP` → `[[BLIP]]`
  - 保留已有 wikilink 不被修改
  - 不替换代码块中的内容
  - 不替换已存在 wikilink 的内容（避免重复）

# 与其他 skills 的区别

## start-my-day (本skill)
- **目的**：从大范围搜索中筛选推荐论文，生成每日推荐笔记
- **搜索范围**：近一个月 + 近一年热门/优质论文
- **内容**：推荐列表
  - 开头包含"今日概览"：总结主要研究方向、总体趋势、质量分布、研究热点和阅读建议
  - 所有论文统一格式
  - 前3篇特殊处理：
    - 论文名称用 wikilink 格式：`[[论文名字]]`
    - 自动提取第一张图片并插入
    - 自动调用 `paper-analyze` 生成详细报告
    - 在"详细报告"字段显示 wikilink 关联
- **图片处理**：前3篇自动提取并插入第一张图片；不包含所有论文的图
- **详细报告**：前3篇自动生成，其他论文不生成
- **适用**：用户每天手动触发
- **笔记引用**：如果论文已有笔记，简略写并引用；如果分析需要引用历史笔记，也直接引用

## paper-analyze (深度分析skill)
- **目的**：用户主动查看单篇论文，深度研究
- **适用场景**：用户自己还想要看，但AI没有整理到的论文
- **内容**：详细的论文深度分析笔记
  - 包含所有核心信息：研究问题、方法概述、方法架构、关键创新、实验结果、深度分析、相关论文对比等
  - **图文并茂**：论文中的所有图片都要用上（核心架构图、方法图、实验结果图等）
- **适用**：用户主动调用 `/paper-analyze [论文ID]` 或论文标题
- **重要要求**：无论是start-my-day整理的论文，还是用户主动查看的论文，都要图文并茂

# 使用说明

当用户输入 "start my day" 时，按以下步骤执行：

**日期参数支持**：
- 无参数：生成当天的论文推荐笔记
- 有参数（YYYY-MM-DD）：生成指定日期的论文推荐笔记
  - 例如：`/start-my-day 2026-02-27`

## 自动执行流程

1. **获取目标日期**
   - 无参数：使用当前日期（YYYY-MM-DD格式）
   - 有参数：使用指定日期

2. **扫描现有笔记构建索引**
   ```bash
   # 扫描 vault 中现有的论文笔记
   cd "$SKILL_DIR"
   $PYTHON scripts/scan_existing_notes.py \
     --vault "$OBSIDIAN_VAULT_PATH" \
     --output existing_notes_index.json
   ```
   - 扫描 `论文笔记/` 目录
   - 提取笔记标题和 tags
   - 构建关键词到笔记路径的映射表

3. **搜索和筛选论文（S2 为主 + arXiv 补充）**
   ```bash
   # 使用 Python 脚本搜索、解析和筛选论文
   # 首先切换到 skill 目录，然后执行脚本
   # 如果有目标日期参数（如 2026-02-21），传递给 --target-date
   cd "$SKILL_DIR"
   $PYTHON scripts/search_arxiv.py \
     --config "$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml" \
     --output arxiv_filtered.json \
     --max-results 200 \
     --top-n 10 \
     --categories "physics.ao-ph,cs.AI,cs.LG,cs.CV" \
     --target-date "{目标日期}"  # 如果用户指定了日期，替换为实际日期
   ```

4. **CNKI 搜索中文论文（辅）**
   - 使用 `cnki-search` skill 搜索中文期刊
   - 搜索关键词从研究领域配置中提取
   - 每日最多2篇中文论文
   - 需 chrome-devtools MCP 支持

5. **读取筛选结果**
   - 从 `arxiv_filtered.json` 中读取筛选结果
   - 获取前 10 篇高评分论文（S2 + arXiv 合并结果）
   - 每篇论文包含：ID、标题、作者、摘要、评分、匹配领域、来源（S2/arXiv）

6. **前3篇论文导入 Zotero（已移除）**
   - 用户手动通过浏览器 Zotero Connector 插件导入，笔记中保留 `Zotero: --` 占位符供用户填写

7. **生成推荐笔记（包含关键词链接）**
   - 创建 `Daily_paper/YYYY-MM-DD${NOTE_SUFFIX}.md`（使用目标日期，`NOTE_SUFFIX` 依语言设置）
   - **按评分排序**：所有论文按推荐评分从高到低排列
   - **前3篇特殊处理**：
     - 论文名称用 wikilink 格式：`[[论文名字]]`
     - 尝试下载PDF提取图片（付费墙论文可能无法获取PDF，此时跳过图片）
     - 在"一句话总结"后插入提取的图片（如有）
     - 在"笔记"字段显示 wikilink 关联
     - 在"Zotero"字段保留占位符 `--`，用户手动导入后填写
   - **其他论文**：只写基本信息，不插入图片
   - **关键词自动链接**（重要！）：
     - 在生成笔记后，扫描文本中的关键词
     - 使用 `existing_notes_index.json` 进行匹配
     - 将关键词替换为 wikilink，如 `BLIP` → `[[BLIP]]`
     - 保留已有 wikilink 不被修改
     - 不替换代码块中的内容

8. **对前三篇论文执行深度分析**
   - **如果已有笔记**：
     - 不重复生成详细报告
     - 使用已有笔记路径作为 wikilink
     - 检查是否需要提取图片（如果没有 images 目录或 images 目录为空）
     - 在推荐笔记的"笔记"字段引用已有笔记
   - **如果没有笔记**：
     - 尝试下载PDF并提取图片（付费墙论文可能无法获取PDF）
     - 如果PDF可用：提取图片保存到 vault 的 images 目录，在详细分析笔记中插入图片
     - 如果PDF不可用：跳过图片，仅基于摘要生成详细分析笔记
     - 生成详细的论文分析报告
     - 在推荐笔记中添加图片（如有）和详细报告链接

## 临时文件清理

- 搜索过程产生的临时 XML 和 JSON 文件可以清理
- 推荐笔记已保存到 vault 后，临时文件不再需要

## 依赖项

- Python 3.x（用于运行搜索和筛选脚本）
- PyYAML（用于读取研究兴趣配置文件）
- 网络连接（访问 Semantic Scholar API + arXiv API）
- chrome-devtools MCP（用于 CNKI 搜索，可选）
- `论文笔记/` 目录（用于扫描现有笔记和保存详细报告）
- `extract-paper-images` skill（用于提取论文图片，仅当PDF可下载时）
- `paper-analyze` skill（用于生成详细报告）
- `cnki-search` skill（用于搜索中文期刊论文）

## 脚本说明

### search_arxiv.py

位于 `scripts/search_arxiv.py`，功能包括：

1. **Step 1: Semantic Scholar 领域查询（主）**：从配置读取查询模板，按领域精准搜索
2. **Step 2: arXiv 关键词搜索（补充）**：使用 `arxiv_domain_queries` 配置的 AND-logic 查询
3. **Step 3: 合并CNKI结果（如有）**：通过 `--cnki-results` 参数注入外部CNKI结果
4. **Step 4: 合并去重评分**：合并 S2 + arXiv + CNKI 结果，去重，计算综合评分
5. **输出 JSON**：保存筛选后的结果到 `arxiv_filtered.json`

配置文件 `research_interests.yaml` 中的 `search_strategy` 字段控制搜索行为：
- `s2_queries`: 每个领域的 S2 查询模板（如 "marine heatwave fishery impact"）
- `s2_recent_days`: S2 近期窗口天数（默认30天）
- `s2_mid_days`: S2 中期窗口天数（默认365天）
- `s2_hot_days`: S2 高引用窗口天数（默认730天）
- `arxiv_domain_queries`: 每个领域的 arXiv AND-logic 查询（如 "marine heatwave AND fishery"）
- `arxiv_search_mode`: arXiv 搜索模式（keyword 或 category）

**评分规则**：
- 近期窗口（s2_window=='recent'）论文加分 +0.5
- 纯 CS 论文（fieldsOfStudy 仅含 Computer Science）降权 -0.5

### scan_existing_notes.py

位于 `scripts/scan_existing_notes.py`，功能包括：

1. **扫描笔记目录**：扫描 `论文笔记/` 下所有 `.md` 文件
2. **提取笔记信息**：
   - 文件路径
   - 文件名
   - frontmatter 中的 title 字段
   - tags 字段
3. **构建索引**：创建关键词到笔记路径的映射表
4. **输出 JSON**：保存索引到 `existing_notes_index.json`

**使用方法**：
```bash
cd "$SKILL_DIR"
$PYTHON scripts/scan_existing_notes.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --output existing_notes_index.json
```

**输出格式**：
```json
{
  "notes": [
    {
      "path": "论文笔记/多模态技术/BLIP_Bootstrapping-Language-Image-Pre-training.md",
      "filename": "BLIP_Bootstrapping-Language-Image-Pre-training.md",
      "title": "BLIP: Bootstrapping Language-Image Pre-training for Unified Vision-Language Understanding and Generation",
      "title_keywords": ["BLIP", "Bootstrapping", "Language-Image", "Pre-training", "Unified", "Vision-Language", "Understanding", "Generation"],
      "tags": ["Vision-Language-Pre-training", "Multimodal-Encoder-Decoder", "Bootstrapping", "Image-Captioning", "Image-Text-Retrieval", "VQA"]
    }
  ],
  "keyword_to_notes": {
    "blip": ["论文笔记/多模态技术/BLIP_Bootstrapping-Language-Image-Pre-training.md"],
    "bootstrapping": ["论文笔记/多模态技术/BLIP_Bootstrapping-Language-Image-Pre-training.md"],
    "vision-language": ["论文笔记/多模态技术/BLIP_Bootstrapping-Language-Image-Pre-training.md"]
  }
}
```

### link_keywords.py

位于 `scripts/link_keywords.py`，功能包括：

1. **读取文本**：读取需要处理的文本内容
2. **读取笔记索引**：从 `existing_notes_index.json` 加载笔记映射
3. **替换关键词**：在文本中查找关键词，替换为wikilink
   - 不替换已存在的 wikilink（如 `[[BLIP]]`）
   - 不替换代码块中的内容
   - 匹配规则：
     - 优先匹配完整的标题关键词
     - 其次匹配 tags 中的关键词
     - 匹配时忽略大小写
     - 过滤通用词（and, for, model, learning 等）
     - 跳过 frontmatter 和标题行
4. **输出结果**：输出处理后的文本

**使用方法**：
```bash
# 首先切换到 skill 目录，然后执行脚本
cd "$SKILL_DIR"
$PYTHON scripts/link_keywords.py \
  --index existing_notes_index.json \
  --input "input.txt" \
  --output "output.txt"
```

**匹配示例**：
```
原始文本：
"这篇论文使用了BLIP和CLIP作为基线方法。"

处理后：
"这篇论文使用了[[BLIP]]和[[CLIP]]作为基线方法。"
```

**使用方法**：
```bash
# 步骤1：扫描现有笔记
cd "$SKILL_DIR"
$PYTHON scripts/scan_existing_notes.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --output existing_notes_index.json

# 步骤2：生成推荐笔记（正常流程）
# ... 使用 search_arxiv.py 搜索论文 ...

# 步骤3：链接关键词（新增步骤）
$PYTHON scripts/link_keywords.py \
  --index existing_notes_index.json \
  --input "Daily_paper/YYYY-MM-DD${NOTE_SUFFIX}.md" \
  --output "Daily_paper/YYYY-MM-DD${NOTE_SUFFIX}_linked.md"
```

**关键特性**：
- **智能匹配**：忽略大小写匹配中文环境
- **保护已有链接**：不替换已存在的wikilink
- **避免代码污染**：不替换代码块和行内代码中的内容
- **路径编码**：使用UTF-8编码确保中文路径正确
- **跳过敏感区域**：不处理 frontmatter、标题行、代码块


### 关键词链接实现（新增！）

**功能概述**：
在生成每日推荐笔记后，自动扫描现有笔记，将文本中的关键词（如BLIP、CLIP等）替换为wikilink（如[[BLIP]]）。

**实现流程**：
1. **扫描现有笔记**：扫描 `论文笔记/` 目录
   - 提取笔记的frontmatter（title、tags）
   - 从标题中提取关键词（按分隔符和常见词缀）
   - 从tags中提取关键词（按连字符分割）
   - 构建关键词到笔记路径的映射表

2. **生成推荐笔记**：正常生成推荐笔记内容

3. **链接关键词**：处理生成的笔记
   - 找到文本中的关键词
   - 用wikilink替换找到的关键词
   - 保留已有wikilink
   - 不替换代码块和行内代码中的内容

**使用方法**：
```bash
# 步骤1：扫描现有笔记
cd "$SKILL_DIR"
$PYTHON scripts/scan_existing_notes.py \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --output existing_notes_index.json

# 步骤2：生成推荐笔记（正常流程）
# ... 使用 search_arxiv.py 搜索论文 ...

# 步骤3：链接关键词（新增步骤）
$PYTHON scripts/link_keywords.py \
  --index existing_notes_index.json \
  --input "Daily_paper/YYYY-MM-DD${NOTE_SUFFIX}.md" \
  --output "Daily_paper/YYYY-MM-DD${NOTE_SUFFIX}_linked.md"
```

**关键特性**：
- **智能匹配**：忽略大小写匹配中文环境
- **保护已有链接**：不替换已存在的wikilink
- **避免代码污染**：不替换代码块和行内代码中的内容
- **路径编码**：使用UTF-8编码确保中文路径正确
