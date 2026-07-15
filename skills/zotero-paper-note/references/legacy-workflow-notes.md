# Legacy Workflow Notes

These notes preserve user-tested workflow experience from the pre-reorganization skill. Current `SKILL.md` instructions take precedence. Use this file only when the active task needs detailed templates, scoring heuristics, troubleshooting notes, or historical edge-case handling. Do not reintroduce obsolete tool-specific setup, hard-coded private paths, or deprecated scripts.

Source skill: `zotero-paper-note`.

---

## Contents

- Zotero → Obsidian 论文笔记
  - 前置条件
  - 工作流程
    - 步骤1：确认论文并获取元数据
    - 步骤2：定位本地 PDF
    - 步骤3：从 PDF 提取图片和文本
- Resolve conda environment
      - 3.1 提取图片
- 方法1：提取嵌入式图片
- 方法2：如果嵌入式图片不足，渲染含图的页面为 PNG
      - 3.2 提取全文
    - 步骤4：生成 Obsidian 笔记
      - 笔记模板
- {论文完整标题}
  - 核心信息
  - 摘要翻译
  - 研究背景与动机
  - 方法概述
  - 实验结果
  - 深度分析
  - 与相关论文对比
  - 对我当前研究的启发
  - 我的综合评价
    - 步骤5：更新推荐笔记中的 Zotero 链接（可选）
  - 关键注意事项
  - 与其他 Skill 的关系

---
# Zotero → Obsidian 论文笔记

从 Zotero 中的论文（含本地 PDF）自动生成图文并茂的 Obsidian 笔记。

如果论文与海洋热浪/冷浪、海洋气候极端、渔业影响、SST 极端检测或相关知识抽取有关，先读取 `the research context file configured in $OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml`，并在最终笔记中显式加入“对我当前研究的启发”小节。

## 前置条件

- Zotero 运行中
- Obsidian vault: `$OBSIDIAN_VAULT_PATH`
- 笔记目录: `论文笔记/`
- Zotero 数据库: `$ZOTERO_DATA_DIR/zotero.sqlite`
- Python conda 环境: `paper`（含 PyMuPDF/fitz）

## 工作流程

### 步骤1：确认论文并获取元数据

1. **用户指定论文**：标题/关键词/citationKey/DOI

2. **查询 Zotero 元数据**：复制数据库避免锁，查 `items` + `itemData` 获取 item key 和元数据
   ```bash
   cp "$ZOTERO_DATA_DIR/zotero.sqlite" /tmp/zotero_query.sqlite
   ```

   查询 item key：
   ```bash
   sqlite3 /tmp/zotero_query.sqlite "SELECT i.key, i.itemID FROM items i WHERE i.itemID IN (SELECT itemID FROM itemData WHERE valueID IN (SELECT valueID FROM itemDataValues WHERE value LIKE '%关键词%')) ORDER BY i.dateAdded DESC LIMIT 20;"
   ```

3. **查询完整元数据**：
   ```bash
   sqlite3 /tmp/zotero_query.sqlite "
   SELECT f.fieldName, v.value
   FROM itemData d
   JOIN itemDataValues v ON d.valueID = v.valueID
   JOIN fields f ON d.fieldID = f.fieldID
   WHERE d.itemID = {itemID}
   ORDER BY f.fieldName;
   "
   ```

4. **查询作者**：
   ```bash
   sqlite3 /tmp/zotero_query.sqlite "
   SELECT c.firstName, c.lastName
   FROM itemCreators ic
   JOIN creators c ON ic.creatorID = c.creatorID
   WHERE ic.itemID = {itemID}
   ORDER BY ic.orderIndex;
   "
   ```

### 步骤2：定位本地 PDF

1. **查询附件路径**：
   ```bash
   sqlite3 /tmp/zotero_query.sqlite "
   SELECT ia.key, ia.contentType, ia.path
   FROM itemAttachments ia
   JOIN items i ON ia.parentItemID = i.itemID
   WHERE ia.parentItemID = {itemID} AND ia.contentType = 'application/pdf';
   "
   ```
   返回格式如：`UZVEXNY2|application/pdf|storage:Ma 等 - 2026 - xxx.pdf`

2. **定位实际文件**：附件的 `key` 字段对应 Zotero storage 子目录
   - 路径模式：`$ZOTERO_DATA_DIR/storage/{attachment_key}/{filename}`
   - 如果按 key 目录找不到，用 `find` 搜索文件名：
   ```bash
   find $ZOTERO_DATA_DIR/storage -name "*{部分文件名}*" 2>/dev/null
   ```

3. **验证 PDF**：
   ```bash
   file "{pdf_path}"
   ```
   确认是 `PDF document` 而非 `HTML document`

### 步骤3：从 PDF 提取图片和文本

```bash
# Resolve conda environment
CONDA_ENV=$(grep -E "^\s+conda_env:" "$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml" 2>/dev/null | awk '{print $2}' | tr -d '"')
if [ -z "$CONDA_ENV" ]; then CONDA_ENV="paper"; fi
PYTHON="$HOME/anaconda3/envs/$CONDA_ENV/bin/python"
```

#### 3.1 提取图片

**策略**：优先提取嵌入式图片，不足时渲染整页为 PNG。

```python
import fitz
import os

pdf_path = "{pdf_path}"
out_dir = "{images_dir}"
doc = fitz.open(pdf_path)

# 方法1：提取嵌入式图片
img_count = 0
for page_num in range(len(doc)):
    page = doc[page_num]
    images = page.get_images(full=True)
    for img in images:
        xref = img[0]
        base_image = doc.extract_image(xref)
        if base_image:
            width, height = base_image['width'], base_image['height']
            if width < 200 or height < 200:  # 跳过小图标
                continue
            img_count += 1
            ext = base_image['ext']
            with open(os.path.join(out_dir, f'fig{img_count}.{ext}'), 'wb') as f:
                f.write(base_image['image'])

# 方法2：如果嵌入式图片不足，渲染含图的页面为 PNG
if img_count < 3:
    # 找到含 "Figure" 标题的页面
    figure_pages = []
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        if any(f'Figure {i}' in text for i in range(1, 10)):
            figure_pages.append(page_num)

    # 清空之前提取的图片，重新用页面渲染
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))

    for idx, page_num in enumerate(figure_pages):
        page = doc[page_num]
        mat = fitz.Matrix(3, 3)  # 3x分辨率
        pix = page.get_pixmap(matrix=mat)
        pix.save(os.path.join(out_dir, f'fig{idx+1}_page{page_num+1}.png'))
```

#### 3.2 提取全文

```python
import fitz
doc = fitz.open(pdf_path)
all_text = ''
for i in range(len(doc)):
    all_text += doc[i].get_text()
```

读取全文用于生成详细分析笔记。按需分段读取（摘要、方法、结果、讨论）。

### 步骤4：生成 Obsidian 笔记

调用 `paper-analyze` skill 的笔记模板生成详细笔记，**必须包含**：

1. **Zotero 跳转链接**（在标题下方）
2. **提取的图片**（在对应章节中插入）
3. **完整元数据**（从 Zotero 获取）
4. **若与当前研究相关，加入“对我当前研究的启发”**，重点写：
   - 对五种 baseline 对比的启发
   - 对 MHW/MCS 指标和配图设计的启发
   - 对后续结合渔业活动或知识图谱分析的启发

#### 笔记模板

```markdown
---
date: "{今天日期}"
paper_id: "DOI:{DOI}"
title: "{论文完整标题}"
authors: "{作者列表}"
domain: "{推断的领域}"
tags:
  - 论文笔记
  - {领域标签}
  - {方法标签}
quality_score: "{X.X}/10"
created: "{今天日期}"
updated: "{今天日期}"
status: analyzed
zotero_key: "{8位item key}"
---

# {论文完整标题}

> [📄 在 Zotero 中打开](zotero://select/items/0_{zotero_key})

## 核心信息
- **论文ID**：DOI:{DOI}
- **作者**：{作者列表}
- **机构**：{从PDF提取的机构信息}
- **发布时间**：{日期}
- **期刊**：{期刊名}
- **链接**：[DOI](https://doi.org/{DOI})

## 摘要翻译
[英文摘要 + 中文翻译 + 核心要点提炼]

## 研究背景与动机
[从PDF全文提取]

## 方法概述
[从PDF全文提取，插入图片]

![[fig1_page8.png|600]]

> 图1：[图片描述]

## 实验结果
[从PDF全文提取，插入图片]

![[fig2_page9.png|600]]

> 图2：[图片描述]

## 深度分析
[基于全文的深度分析]

## 与相关论文对比
[搜索vault中已有笔记进行对比]

## 对我当前研究的启发
[如果论文与海洋热浪/冷浪、渔业影响、气候极端、SST 检测或相关知识抽取有关，则必须填写。不要只复述论文，要明确指出对当前项目的方法、指标、图表或后续渔业分析有什么可直接借鉴之处。]

## 我的综合评价
[分项评分表]

> [!tip] 关键启示
> [一句话核心启示]

> [!warning] 注意事项
> - [局限1]
> - [局限2]

> [!success] 推荐指数
> ⭐⭐⭐⭐⭐ [推荐理由]
```

### 步骤5：更新推荐笔记中的 Zotero 链接（可选）

如果该论文在每日推荐笔记中存在且 Zotero 字段为 `--`，更新为实际的 `zotero://select/items/0_{key}`。

## 关键注意事项

- **Zotero item key ≠ Better BibTeX citekey**：URI 跳转用 item key（8位，如 `3GTF9YSF`），不用 citekey
- **数据库锁**：Zotero 运行时 sqlite 被锁，必须 `cp` 后再查
- **附件 key ≠ 父条目 key**：PDF 附件有自己的 key，存储在 `/Zotero/storage/{attachment_key}/` 下
- **图片提取策略**：嵌入式图片优先（质量高），不足3张时回退到整页渲染
- **笔记文件名**：用 `{第一作者} {年份} - {中文主题}` 格式
- **图片格式**：必须使用 `![[filename.png|600]]`，禁止 `![alt](path)`

## 与其他 Skill 的关系

| Skill | 关系 |
|-------|------|
| `start-my-day` | 每日推荐，用户看到感兴趣的论文后手动导入Zotero，再用本skill生成笔记 |
| `paper-analyze` | 共用详细论文笔记模板，本skill增加了Zotero PDF提取能力 |
| `extract-paper-images` | 从arXiv提取图片，本skill从Zotero本地PDF提取图片 |
| `cnki-export` | 用户从CNKI导入论文到Zotero |
