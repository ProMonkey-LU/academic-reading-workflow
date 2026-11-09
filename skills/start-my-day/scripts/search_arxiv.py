#!/usr/bin/env python3
"""
OpenAlex + Semantic Scholar + arXiv hybrid paper search for start-my-day.
"""

import xml.etree.ElementTree as ET
import json
import re
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)


def title_to_note_filename(title: str, authors: str = "", published: str = "") -> str:
    """将论文标题转换为 Obsidian 笔记文件名，格式：作者年份 - 中文主题。

    与现有笔记命名风格保持一致，如 'Oliver 2018 - 长周期MHW趋势'。
    对于 arXiv 论文，使用第一作者姓氏+年份+简短主题关键词。
    """
    # 提取年份
    year = ""
    if published:
        year = published[:4] if len(published) >= 4 else ""

    # 提取第一作者姓氏
    first_author = ""
    if authors:
        # authors 可能是 list 或 str；S2 API 返回 list[dict]
        if isinstance(authors, list):
            first = authors[0] if authors else ""
            if isinstance(first, dict):
                first = first.get("name", "")
        else:
            first = authors.split(",")[0].strip()
        # 取姓氏（最后一个词）
        parts = first.split() if isinstance(first, str) else []
        if parts:
            first_author = parts[-1]

    # 从标题提取简短主题关键词（取前3-4个实词）
    import re as _re
    # 移除常见停用词
    stopwords = {"a", "an", "the", "of", "for", "in", "on", "and", "or", "to",
                 "with", "from", "by", "via", "using", "based", "through",
                 "its", "their", "our", "we", "is", "are", "was", "were"}
    words = _re.findall(r'[A-Za-z0-9]+', title)
    keywords = [w for w in words if w.lower() not in stopwords][:5]
    topic = " ".join(keywords)

    if first_author and year:
        return f"{first_author} {year} - {topic}"
    elif year:
        return f"{year} - {topic}"
    else:
        # 回退到原标题清理
        return _re.sub(r'[ /\\:*?"<>|]+', '_', title).strip('_')

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests library not found, using urllib for Semantic Scholar API")

# ---------------------------------------------------------------------------
# API 配置
# ---------------------------------------------------------------------------
ARXIV_NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'arxiv': 'http://arxiv.org/schemas/atom'
}

SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = "title,abstract,publicationDate,citationCount,influentialCitationCount,url,authors,authors.affiliations,externalIds,fieldsOfStudy"
OPENALEX_API_URL = "https://api.openalex.org/works"

# 默认分类关键词映射（当配置中无用户自定义关键词时使用）
ARXIV_CATEGORY_KEYWORDS = {
    "cs.AI": "artificial intelligence",
    "cs.LG": "machine learning",
    "cs.CL": "computational linguistics natural language processing",
    "cs.CV": "computer vision",
    "cs.MM": "multimedia",
    "cs.MA": "multi-agent systems",
    "cs.RO": "robotics"
}

# ---------------------------------------------------------------------------
# 评分常量  —— 修改权重时只需编辑这里
# ---------------------------------------------------------------------------

# 各维度原始评分的满分值（归一化基准）
SCORE_MAX = 3.0

# 相关性评分：关键词在标题 / 摘要中匹配的加分
RELEVANCE_TITLE_KEYWORD_BOOST = 0.5
RELEVANCE_SUMMARY_KEYWORD_BOOST = 0.3
RELEVANCE_CATEGORY_MATCH_BOOST = 1.0

# 新近性阈值（天） -> 对应评分
RECENCY_THRESHOLDS = [
    (30, 3.0),
    (90, 2.0),
    (180, 1.0),
]
RECENCY_DEFAULT = 0.0

# 热门度：高影响力引用数归一化到 0-SCORE_MAX
# 含义：达到此引用数时视为满分
POPULARITY_INFLUENTIAL_CITATION_FULL_SCORE = 100
POPULARITY_CITATION_FULL_SCORE = 100

# 综合推荐评分权重（普通论文）
WEIGHTS_NORMAL = {
    'relevance': 0.40,
    'recency': 0.25,
    'popularity': 0.25,
    'quality': 0.10,
}
# 综合推荐评分权重（高影响力论文：提高热门度，降低新近性）
WEIGHTS_HOT = {
    'relevance': 0.40,
    'recency': 0.15,
    'popularity': 0.35,
    'quality': 0.10,
}

# 近期论文加分（S2 近期窗口的论文额外加分）
RECENT_WINDOW_BONUS = 0.5

# 纯 CS 论文降权（fieldsOfStudy 仅含 Computer Science 时降权）
PURE_CS_PENALTY = -0.5

# Semantic Scholar 速率限制等待时间（秒）
S2_RATE_LIMIT_WAIT = 10
S2_CATEGORY_REQUEST_INTERVAL = 3
OPENALEX_REQUEST_INTERVAL = 1.1

# Semantic Scholar API Key（可选，仅从环境变量读取）
S2_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY")


def load_research_config(config_path: str) -> Dict:
    """
    从 YAML 文件加载研究兴趣配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        研究配置字典
    """
    import yaml
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        # 凭据不进入 YAML 或公开仓库。兼容旧配置时只给出迁移提示，
        # 不再读取其中的明文 key。
        if config.get('semantic_scholar_api_key'):
            logger.warning(
                "Ignoring deprecated semantic_scholar_api_key in YAML; "
                "set SEMANTIC_SCHOLAR_API_KEY in the environment instead"
            )
        if config.get('openalex_api_key'):
            logger.warning(
                "Ignoring deprecated openalex_api_key in YAML; "
                "set OPENALEX_API_KEY in the environment instead"
            )
        return config
    except Exception as e:
        logger.error("Error loading config: %s", e)
        # 返回默认配置
        return {
            "research_domains": {
                "大模型": {
                    "keywords": [
                        "pre-training", "foundation model", "model architecture",
                        "large language model", "LLM", "transformer"
                    ],
                    "arxiv_categories": ["cs.AI", "cs.LG", "cs.CL"],
                    "priority": 5
                }
            },
            "excluded_keywords": ["3D", "review", "workshop", "survey"]
        }


def calculate_date_windows(target_date: Optional[datetime] = None, days: int = 30) -> Tuple[datetime, datetime, datetime, datetime]:
    """
    计算两个时间窗口：最近N天和过去一年（除去最近N天）

    Args:
        target_date: 基准日期，如果为 None 则使用当前日期
        days: 最近搜索窗口的天数（默认30）

    Returns:
        (window_recent_start, window_recent_end, window_1y_start, window_1y_end)
    """
    if target_date is None:
        target_date = datetime.now()

    window_recent_start = target_date - timedelta(days=days)
    window_recent_end = target_date

    window_1y_start = target_date - timedelta(days=365)
    window_1y_end = target_date - timedelta(days=days + 1)

    return window_recent_start, window_recent_end, window_1y_start, window_1y_end


def search_arxiv_by_date_range(
    categories: List[str],
    start_date: datetime,
    end_date: datetime,
    max_results: int = 200,
    max_retries: int = 3
) -> List[Dict]:
    """
    使用 arXiv API 搜索指定日期范围内的论文
    
    Args:
        categories: arXiv 分类列表
        start_date: 开始日期
        end_date: 结束日期
        max_results: 最大结果数
        max_retries: 最大重试次数
        
    Returns:
        论文列表
    """
    # 构建分类查询
    category_query = "+OR+".join([f"cat:{cat}" for cat in categories])
    
    # 构建日期范围查询 (arXiv 使用 YYYYMMDD 格式)
    date_query = f"submittedDate:[{start_date.strftime('%Y%m%d')}0000+TO+{end_date.strftime('%Y%m%d')}2359]"
    
    # 组合查询
    full_query = f"({category_query})+AND+{date_query}"
    
    # 构建 URL
    url = (
        f"https://export.arxiv.org/api/query?"
        f"search_query={full_query}&"
        f"max_results={max_results}&"
        f"sortBy=submittedDate&"
        f"sortOrder=descending"
    )
    
    logger.info("[arXiv] Searching papers from %s to %s", start_date.date(), end_date.date())
    logger.debug("[arXiv] URL: %s...", url[:120])
    
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                xml_content = response.read().decode('utf-8')
                papers = parse_arxiv_xml(xml_content)
                logger.info("[arXiv] Found %d papers", len(papers))
                return papers
        except Exception as e:
            logger.warning("[arXiv] Error (attempt %d/%d): %s", attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2
                logger.info("[arXiv] Retrying in %d seconds...", wait_time)
                time.sleep(wait_time)
            else:
                logger.error("[arXiv] Failed after %d attempts", max_retries)
                return []
    
    return []


def search_arxiv_by_keywords(
    keywords: List[str],
    start_date: datetime,
    end_date: datetime,
    max_results: int = 100,
    max_retries: int = 3
) -> List[Dict]:
    """
    使用关键词直接搜索 arXiv 论文（不限分类）

    Args:
        keywords: 搜索关键词列表
        start_date: 开始日期
        end_date: 结束日期
        max_results: 最大结果数
        max_retries: 最大重试次数

    Returns:
        论文列表
    """
    # 构建关键词查询 (在 title 和 abstract 中搜索)
    # 多个关键词之间使用 AND 逻辑，确保每个关键词都出现
    keyword_parts = []
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        # 如果关键词包含空格，用引号包裹进行精确匹配
        if ' ' in kw:
            keyword_parts.append(f'(ti:"{kw}"+OR+abs:"{kw}")')
        else:
            keyword_parts.append(f"(ti:{kw}+OR+abs:{kw})")

    if not keyword_parts:
        return []

    # 多个关键词时使用 AND 连接（精准搜索）
    # 这确保 arxiv_domain_queries 的 AND-logic 被正确实现
    keyword_query = "+AND+".join(keyword_parts)

    # 构建日期范围查询
    date_query = f"submittedDate:[{start_date.strftime('%Y%m%d')}0000+TO+{end_date.strftime('%Y%m%d')}2359]"

    full_query = f"({keyword_query})+AND+{date_query}"

    url = (
        f"https://export.arxiv.org/api/query?"
        f"search_query={urllib.parse.quote(full_query, safe='+:')}&"
        f"max_results={max_results}&"
        f"sortBy=relevance&"
        f"sortOrder=descending"
    )

    logger.info("[arXiv] Keyword search: %s", keywords)
    logger.debug("[arXiv] URL: %s...", url[:150])

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                xml_content = response.read().decode('utf-8')
                papers = parse_arxiv_xml(xml_content)
                logger.info("[arXiv] Keyword search found %d papers", len(papers))
                return papers
        except Exception as e:
            logger.warning("[arXiv] Keyword search error (attempt %d/%d): %s", attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2
                time.sleep(wait_time)
            else:
                logger.error("[arXiv] Keyword search failed after %d attempts", max_retries)
                return []

    return []


def search_semantic_scholar_hot_papers(
    query: str,
    start_date: datetime,
    end_date: datetime,
    top_k: int = 20,
    max_retries: int = 2,
    fields_of_study: List[str] = None,
    min_citation_count: int = 0
) -> List[Dict]:
    """
    使用 Semantic Scholar API 搜索指定时间范围内的高影响力论文

    Args:
        query: 搜索关键词
        start_date: 开始日期
        end_date: 结束日期
        top_k: 返回前 K 篇高影响力论文
        max_retries: 最大重试次数
        fields_of_study: 限定研究领域列表（如 ["Environmental Science", "Physics"]）
        min_citation_count: 最低引用数门槛

    Returns:
        按高影响力引用数排序的论文列表
    """
    # 构建日期范围 (Semantic Scholar 使用 YYYY-MM-DD:YYYY-MM-DD 格式)
    date_range = f"{start_date.strftime('%Y-%m-%d')}:{end_date.strftime('%Y-%m-%d')}"

    # 构建请求参数
    params = {
        "query": query,
        "publicationDateOrYear": date_range,
        "limit": 100,  # 先拉取100篇相关度最高的
        "fields": SEMANTIC_SCHOLAR_FIELDS
    }

    # 添加 fieldsOfStudy 过滤
    if fields_of_study:
        params["fieldsOfStudy"] = ",".join(fields_of_study)

    # 添加最低引用数门槛
    if min_citation_count > 0:
        params["minCitationCount"] = min_citation_count
    
    headers = {
        "User-Agent": "StartMyDay-PaperFetcher/1.0"
    }
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY
    
    logger.info("[S2] Searching hot papers from %s to %s", start_date.date(), end_date.date())
    logger.info("[S2] Query: '%s'", query)
    
    for attempt in range(max_retries):
        try:
            if HAS_REQUESTS:
                response = requests.get(
                    SEMANTIC_SCHOLAR_API_URL,
                    params=params,
                    headers=headers,
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()
            else:
                # 使用 urllib
                query_string = urllib.parse.urlencode(params)
                url = f"{SEMANTIC_SCHOLAR_API_URL}?{query_string}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    data = json.loads(response.read().decode('utf-8'))
            
            papers = data.get("data", [])
            if not papers:
                logger.info("[S2] No papers found")
                return []
            
            # 本地二次过滤与排序
            valid_papers = []
            for p in papers:
                # 过滤掉没有标题或摘要的无效条目
                if not p.get("title") or not p.get("abstract"):
                    continue
                
                # 处理可能的 None 值
                inf_cit = p.get("influentialCitationCount") or 0
                cit = p.get("citationCount") or 0
                
                p["influentialCitationCount"] = inf_cit
                p["citationCount"] = cit
                
                # 标记来源
                p["source"] = "semantic_scholar"
                p["hot_score"] = inf_cit  # 使用高影响力引用数作为热度分数

                # 提取 affiliation 信息
                if p.get('authors') and not p.get('affiliations'):
                    affiliations = []
                    for a in p['authors']:
                        for affil in (a.get('affiliations') or []):
                            name = affil.get('name', '') if isinstance(affil, dict) else str(affil)
                            if name and name not in affiliations:
                                affiliations.append(name)
                    p['affiliations'] = affiliations
                
                valid_papers.append(p)
            
            # 按高影响力引用数倒序排列
            sorted_papers = sorted(
                valid_papers,
                key=lambda x: x["influentialCitationCount"],
                reverse=True
            )
            
            logger.info("[S2] Found %d valid papers, returning top %d", len(sorted_papers), top_k)
            return sorted_papers[:top_k]
            
        except Exception as e:
            error_msg = str(e)
            logger.warning("[S2] Error (attempt %d/%d): %s", attempt + 1, max_retries, e)
            
            # 检查是否是 429 错误（Too Many Requests）
            is_rate_limit = False
            if HAS_REQUESTS and hasattr(e, 'response') and e.response is not None:
                is_rate_limit = e.response.status_code == 429
            else:
                is_rate_limit = "429" in error_msg or "Too Many Requests" in error_msg
            
            if attempt < max_retries - 1:
                # 对于 429 错误，使用更长的等待时间
                if is_rate_limit:
                    wait_time = S2_RATE_LIMIT_WAIT
                    logger.warning("[S2] Rate limit hit. Waiting %d seconds...", wait_time)
                else:
                    wait_time = (2 ** attempt) * 2
                    logger.info("[S2] Retrying in %d seconds...", wait_time)
                time.sleep(wait_time)
            else:
                logger.error("[S2] Failed after %d attempts", max_retries)
                return []
    
    return []


def reconstruct_openalex_abstract(inverted_index: Optional[Dict]) -> str:
    """Reconstruct plain text from OpenAlex's abstract inverted index."""
    if not isinstance(inverted_index, dict):
        return ""
    positioned_words = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int):
                positioned_words.append((position, word))
    positioned_words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned_words)


def normalize_openalex_work(work: Dict) -> Optional[Dict]:
    """Map an OpenAlex work to the schema used by the shared scorer."""
    title = work.get("display_name") or work.get("title")
    abstract = reconstruct_openalex_abstract(work.get("abstract_inverted_index"))
    if not title or not abstract:
        return None

    authors = []
    affiliations = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if name:
            authors.append({"name": name})
        for institution in authorship.get("institutions") or []:
            institution_name = institution.get("display_name")
            if institution_name and institution_name not in affiliations:
                affiliations.append(institution_name)

    ids = work.get("ids") or {}
    doi = work.get("doi") or ids.get("doi")
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    external_ids = {"OpenAlex": work.get("id")}
    if doi:
        external_ids["DOI"] = doi
    for source_key, target_key in (("pmid", "PubMed"), ("pmcid", "PubMedCentral"), ("mag", "MAG")):
        if ids.get(source_key):
            external_ids[target_key] = ids[source_key]

    primary_topic = work.get("primary_topic") or {}
    field = primary_topic.get("field") or {}
    domain = primary_topic.get("domain") or {}
    fields = [name for name in (field.get("display_name"), domain.get("display_name")) if name]

    primary_location = work.get("primary_location") or {}
    landing_url = primary_location.get("landing_page_url") or work.get("doi") or work.get("id")
    pdf_url = primary_location.get("pdf_url")
    return {
        "paperId": work.get("id"),
        "title": title,
        "abstract": abstract,
        "publicationDate": work.get("publication_date"),
        "citationCount": work.get("cited_by_count") or 0,
        "influentialCitationCount": 0,
        "url": landing_url,
        "authors": authors,
        "affiliations": affiliations,
        "externalIds": external_ids,
        "fieldsOfStudy": fields,
        "openAccessPdf": {"url": pdf_url} if pdf_url else None,
        "source": "openalex",
        "hot_score": work.get("cited_by_count") or 0,
    }


def search_openalex_papers(
    query: str,
    start_date: datetime,
    end_date: datetime,
    top_k: int = 20,
    max_retries: int = 3,
    min_citation_count: int = 0,
) -> List[Dict]:
    """Search OpenAlex in keyless mode or with an optional free API key."""
    filters = [
        f"from_publication_date:{start_date.strftime('%Y-%m-%d')}",
        f"to_publication_date:{end_date.strftime('%Y-%m-%d')}",
        "has_abstract:true",
    ]
    params = {
        "search": query,
        "filter": ",".join(filters),
        "per-page": min(max(top_k * 3, 25), 100),
    }
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY

    headers = {"User-Agent": "StartMyDay-PaperFetcher/2.0"}
    logger.info("[OpenAlex] Query '%s' from %s to %s", query, start_date.date(), end_date.date())

    for attempt in range(max_retries):
        try:
            if HAS_REQUESTS:
                response = requests.get(
                    OPENALEX_API_URL,
                    params=params,
                    headers=headers,
                    timeout=20,
                )
                response.raise_for_status()
                data = response.json()
            else:
                url = f"{OPENALEX_API_URL}?{urllib.parse.urlencode(params)}"
                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=20) as response:
                    data = json.loads(response.read().decode("utf-8"))

            papers = []
            for work in data.get("results", []):
                paper = normalize_openalex_work(work)
                if paper and paper["citationCount"] >= min_citation_count:
                    papers.append(paper)
            papers.sort(key=lambda paper: paper["citationCount"], reverse=True)
            logger.info("[OpenAlex] Found %d valid papers, returning top %d", len(papers), top_k)
            return papers[:top_k]
        except Exception as exc:
            status_code = None
            retry_after = None
            if HAS_REQUESTS and getattr(exc, "response", None) is not None:
                status_code = exc.response.status_code
                retry_after = exc.response.headers.get("Retry-After")
            logger.warning(
                "[OpenAlex] Error (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                exc,
            )
            if attempt >= max_retries - 1:
                break
            if status_code == 429 and retry_after and retry_after.isdigit():
                wait_time = min(int(retry_after), 60)
            else:
                wait_time = 2 ** attempt
            time.sleep(wait_time)

    logger.error("[OpenAlex] Failed after %d attempts", max_retries)
    return []


def search_hot_papers_from_categories(
    categories: List[str],
    start_date: datetime,
    end_date: datetime,
    top_k_per_category: int = 5,
    config: Optional[Dict] = None
) -> List[Dict]:
    """
    为多个 arXiv 分类搜索高影响力论文

    Args:
        categories: arXiv 分类列表
        start_date: 开始日期
        end_date: 结束日期
        top_k_per_category: 每个分类返回的论文数
        config: 研究配置（用于提取用户自定义关键词）

    Returns:
        合并后的高影响力论文列表
    """
    all_hot_papers = []
    seen_arxiv_ids = set()

    # 从配置中提取用户自定义的搜索关键词（更精准）
    user_queries = []
    if config:
        domains = config.get('research_domains', {})
        for domain_name, domain_config in domains.items():
            keywords = domain_config.get('keywords', [])
            # 取每个域的前3个关键词组合为查询
            if keywords:
                query = ' '.join(keywords[:3])
                user_queries.append(query)

    # 如果没有用户关键词，回退到分类关键词
    if not user_queries:
        user_queries = [ARXIV_CATEGORY_KEYWORDS.get(cat, cat) for cat in categories]

    # 去重查询
    seen_queries = set()
    unique_queries = []
    for q in user_queries:
        q_lower = q.lower()
        if q_lower not in seen_queries:
            seen_queries.add(q_lower)
            unique_queries.append(q)

    for query in unique_queries:

        try:
            papers = search_semantic_scholar_hot_papers(
                query=query,
                start_date=start_date,
                end_date=end_date,
                top_k=top_k_per_category
            )
        except Exception as e:
            logger.warning("[S2] Query '%s' failed: %s — skipping", query, e)
            papers = []

        # 去重（基于 arXiv ID）
        for p in papers:
            # 安全地从 externalIds 字典中提取 ArXiv 编号
            arxiv_id = p.get("externalIds", {}).get("ArXiv") if p.get("externalIds") else None
            
            # 统一写入 arxiv_id 字段，方便最后 Step 3 的全局去重
            p["arxiv_id"] = arxiv_id
            
            if arxiv_id and arxiv_id not in seen_arxiv_ids:
                seen_arxiv_ids.add(arxiv_id)
                all_hot_papers.append(p)
            elif not arxiv_id:
                # 没有 arXiv ID 的也保留（可能是其他来源的论文）
                all_hot_papers.append(p)
        
        time.sleep(S2_CATEGORY_REQUEST_INTERVAL)
    
    # 最终按影响力引用数排序
    all_hot_papers.sort(key=lambda x: x.get("influentialCitationCount", 0), reverse=True)
    
    return all_hot_papers


def parse_arxiv_xml(xml_content: str) -> List[Dict]:
    """
    解析 arXiv XML 结果
    
    Args:
        xml_content: XML 内容
        
    Returns:
        论文列表，每篇论文包含 ID、标题、作者、摘要等信息
    """
    papers = []
    
    try:
        root = ET.fromstring(xml_content)
        
        # 查找所有 entry 元素
        for entry in root.findall('atom:entry', ARXIV_NS):
            paper = {}
            
            # 提取 ID
            id_elem = entry.find('atom:id', ARXIV_NS)
            if id_elem is not None:
                paper['id'] = id_elem.text
                # 提取 arXiv ID（从 URL 中提取）
                match = re.search(r'arXiv:(\d+\.\d+)', paper['id'])
                if match:
                    paper['arxiv_id'] = match.group(1)
                else:
                    match = re.search(r'/(\d+\.\d+)$', paper['id'])
                    if match:
                        paper['arxiv_id'] = match.group(1)
            
            # 提取标题
            title_elem = entry.find('atom:title', ARXIV_NS)
            if title_elem is not None:
                paper['title'] = title_elem.text.strip()
            
            # 提取摘要
            summary_elem = entry.find('atom:summary', ARXIV_NS)
            if summary_elem is not None:
                paper['summary'] = summary_elem.text.strip()
            
            # 提取作者（及可选的 affiliation）
            authors = []
            affiliations = []
            for author in entry.findall('atom:author', ARXIV_NS):
                name_elem = author.find('atom:name', ARXIV_NS)
                if name_elem is not None:
                    authors.append(name_elem.text)
                affil_elem = author.find('arxiv:affiliation', ARXIV_NS)
                if affil_elem is not None and affil_elem.text:
                    affil = affil_elem.text.strip()
                    if affil and affil not in affiliations:
                        affiliations.append(affil)
            paper['authors'] = authors
            paper['affiliations'] = affiliations  # 可能为空列表
            
            # 提取发布日期
            published_elem = entry.find('atom:published', ARXIV_NS)
            if published_elem is not None:
                paper['published'] = published_elem.text
                # 解析日期
                try:
                    paper['published_date'] = datetime.fromisoformat(
                        paper['published'].replace('Z', '+00:00')
                    )
                except (ValueError, TypeError):
                    paper['published_date'] = None
            
            # 提取更新日期
            updated_elem = entry.find('atom:updated', ARXIV_NS)
            if updated_elem is not None:
                paper['updated'] = updated_elem.text
            
            # 提取分类
            categories = []
            for category in entry.findall('atom:category', ARXIV_NS):
                term = category.get('term')
                if term:
                    categories.append(term)
            paper['categories'] = categories
            
            # 提取 PDF 链接
            for link in entry.findall('atom:link', ARXIV_NS):
                if link.get('title') == 'pdf':
                    paper['pdf_url'] = link.get('href')
                    break
            
            # 提取主页面链接
            if 'id' in paper:
                paper['url'] = paper['id']
            
            # 标记来源
            paper['source'] = 'arxiv'
            
            papers.append(paper)
            
    except ET.ParseError as e:
        logger.error("Error parsing XML: %s", e)
        raise
    
    return papers


def calculate_relevance_score(
    paper: Dict,
    domains: Dict,
    excluded_keywords: List[str],
    focus_keywords: List[str] = None
) -> Tuple[float, Optional[str], List[str]]:
    """
    计算论文与研究兴趣的相关性评分

    当有 focus_keywords 时，以 focus 匹配为主导（高权重），
    已有兴趣域仅作为参考加分。

    Args:
        paper: 论文信息
        domains: 研究领域配置
        excluded_keywords: 排除关键词
        focus_keywords: 用户今日关注的关键词

    Returns:
        (相关性评分, 匹配的领域, 匹配的关键词列表)
    """
    focus_keywords = focus_keywords or []
    title = paper.get('title', '').lower()
    summary = paper.get('summary', '').lower() if 'summary' in paper else paper.get('abstract', '').lower()
    categories = set(paper.get('categories', []))

    # 检查排除关键词
    for keyword in excluded_keywords:
        if keyword.lower() in title or keyword.lower() in summary:
            return 0, None, []

    # ---- Focus 关键词独立评分（主导） ----
    focus_score = 0.0
    focus_matched = []
    if focus_keywords:
        for fk in focus_keywords:
            fk_lower = fk.lower().strip()
            if not fk_lower:
                continue
            if fk_lower in title:
                focus_score += 2.0  # 标题匹配：高分
                focus_matched.append(fk)
            elif fk_lower in summary:
                focus_score += 1.0  # 摘要匹配：中分
                focus_matched.append(fk)

    # ---- 已有兴趣域评分（参考） ----
    max_domain_score = 0
    best_domain = None
    domain_matched_keywords = []

    for domain_name, domain_config in domains.items():
        score = 0
        dm_keywords = []

        keywords = domain_config.get('keywords', [])
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in title:
                score += RELEVANCE_TITLE_KEYWORD_BOOST
                dm_keywords.append(keyword)
            elif keyword_lower in summary:
                score += RELEVANCE_SUMMARY_KEYWORD_BOOST
                dm_keywords.append(keyword)

        domain_categories = domain_config.get('arxiv_categories', [])
        for cat in domain_categories:
            if cat in categories:
                score += RELEVANCE_CATEGORY_MATCH_BOOST
                dm_keywords.append(cat)

        if score > max_domain_score:
            max_domain_score = score
            best_domain = domain_name
            domain_matched_keywords = dm_keywords

    # ---- 合并评分 ----
    if focus_keywords:
        # Focus 模式：focus 为主，域匹配为辅（0.3 权重）
        total_score = focus_score + max_domain_score * 0.3
        all_matched = focus_matched + [k for k in domain_matched_keywords if k not in focus_matched]
        matched_domain = best_domain if best_domain else ("搜索结果" if focus_matched else None)
    else:
        # 普通模式：纯域评分
        total_score = max_domain_score
        all_matched = domain_matched_keywords
        matched_domain = best_domain

    return total_score, matched_domain, all_matched


def calculate_recency_score(published_date: Optional[datetime]) -> float:
    """
    根据发布日期计算新近性评分
    
    Args:
        published_date: 发布日期
        
    Returns:
        新近性评分 (0-3)
    """
    if published_date is None:
        return 0
    
    now = datetime.now(published_date.tzinfo) if published_date.tzinfo else datetime.now()
    days_diff = (now - published_date).days
    
    for max_days, score in RECENCY_THRESHOLDS:
        if days_diff <= max_days:
            return score
    return RECENCY_DEFAULT


def calculate_quality_score(summary: str) -> float:
    """
    从摘要推断质量评分

    采用更细粒度的指标：强创新词权重高于弱创新词，
    量化结果和对比实验也加分。

    Args:
        summary: 论文摘要

    Returns:
        质量评分 (0-3)
    """
    if not summary:
        return 0.0
    score = 0.0
    summary_lower = summary.lower()

    strong_innovation = [
        'state-of-the-art', 'sota', 'breakthrough', 'first',
        'surpass', 'outperform', 'pioneering'
    ]
    weak_innovation = [
        'novel', 'propose', 'introduce', 'new approach',
        'new method', 'innovative'
    ]
    method_indicators = [
        'framework', 'architecture', 'algorithm', 'mechanism',
        'pipeline', 'end-to-end'
    ]
    quantitative_indicators = [
        'outperforms', 'improves by', 'achieves', 'accuracy',
        'f1', 'bleu', 'rouge', 'beats', 'surpasses'
    ]
    experiment_indicators = [
        'experiment', 'evaluation', 'benchmark', 'ablation',
        'baseline', 'comparison'
    ]

    strong_count = sum(1 for ind in strong_innovation if ind in summary_lower)
    if strong_count >= 2:
        score += 1.0
    elif strong_count == 1:
        score += 0.7
    else:
        weak_count = sum(1 for ind in weak_innovation if ind in summary_lower)
        if weak_count > 0:
            score += 0.3

    if any(ind in summary_lower for ind in method_indicators):
        score += 0.5

    if any(ind in summary_lower for ind in quantitative_indicators):
        score += 0.8
    elif any(ind in summary_lower for ind in experiment_indicators):
        score += 0.4

    return min(score, SCORE_MAX)


def calculate_recommendation_score(
    relevance_score: float,
    recency_score: float,
    popularity_score: float,
    quality_score: float,
    is_hot_paper: bool = False
) -> float:
    """
    计算综合推荐评分

    权重定义在模块顶部常量 WEIGHTS_NORMAL / WEIGHTS_HOT 中。
    对于高影响力论文（来自 Semantic Scholar），使用 WEIGHTS_HOT 提高热门度权重。

    Args:
        relevance_score: 相关性评分 (0-SCORE_MAX)
        recency_score: 新近性评分 (0-SCORE_MAX)
        popularity_score: 热门度评分 (0-SCORE_MAX)
        quality_score: 质量评分 (0-SCORE_MAX)
        is_hot_paper: 是否是高影响力论文

    Returns:
        综合推荐评分 (0-10)
    """
    scores = {
        'relevance': relevance_score,
        'recency': recency_score,
        'popularity': popularity_score,
        'quality': quality_score,
    }
    # 归一化到 0-10 分
    normalized = {k: (v / SCORE_MAX) * 10 for k, v in scores.items()}

    weights = WEIGHTS_HOT if is_hot_paper else WEIGHTS_NORMAL
    final_score = sum(normalized[k] * weights[k] for k in weights)

    return round(final_score, 2)


def filter_and_score_papers(
    papers: List[Dict],
    config: Dict,
    target_date: Optional[datetime] = None,
    is_hot_paper_batch: bool = False,
    focus_keywords: List[str] = None
) -> List[Dict]:
    """
    筛选和评分论文

    Args:
        papers: 论文列表
        config: 研究配置
        target_date: 目标日期（用于计算新近性）
        is_hot_paper_batch: 是否是高影响力论文批次

    Returns:
        筛选和评分后的论文列表
    """
    domains = config.get('research_domains', {})
    excluded_keywords = config.get('excluded_keywords', [])

    scored_papers = []

    for paper in papers:
        # 计算相关性
        relevance, matched_domain, matched_keywords = calculate_relevance_score(
            paper, domains, excluded_keywords, focus_keywords=focus_keywords or []
        )

        # 如果相关性为0，跳过
        if relevance == 0:
            continue

        # 计算新近性
        if 'published_date' in paper:
            recency = calculate_recency_score(paper.get('published_date'))
        else:
            # 对于 Semantic Scholar 的论文，使用 publicationDate
            pub_date_str = paper.get('publicationDate')
            if pub_date_str:
                pub_date = None
                for fmt in ('%Y-%m-%d', '%Y-%m', '%Y'):
                    try:
                        pub_date = datetime.strptime(pub_date_str, fmt)
                        break
                    except (ValueError, TypeError):
                        continue
                recency = calculate_recency_score(pub_date) if pub_date else 0
            else:
                recency = 0

        # 计算热门度
        if is_hot_paper_batch:
            if paper.get('source') == 'openalex':
                citations = paper.get('citationCount', 0)
                popularity = min(
                    citations / (POPULARITY_CITATION_FULL_SCORE / SCORE_MAX),
                    SCORE_MAX,
                )
            else:
                # Semantic Scholar provides an influential-citation signal.
                inf_cit = paper.get('influentialCitationCount', 0)
                popularity = min(
                    inf_cit / (POPULARITY_INFLUENTIAL_CITATION_FULL_SCORE / SCORE_MAX),
                    SCORE_MAX,
                )
        else:
            # 普通论文（无引用数据）：基于新近性给一个中间热门度
            # 最近7天的新论文可能有更高的"潜在热度"
            if 'published_date' in paper and paper['published_date']:
                pub = paper['published_date']
                now = datetime.now(pub.tzinfo) if pub.tzinfo else datetime.now()
                days_old = (now - pub).days
                if days_old <= 7:
                    popularity = 2.0  # 非常新的论文有潜在热度
                elif days_old <= 14:
                    popularity = 1.5
                elif days_old <= 30:
                    popularity = 1.0
                else:
                    popularity = 0.5
            else:
                popularity = 0.5  # 无日期信息时给一个保守值

        # 计算质量
        summary = paper.get('summary', '') if 'summary' in paper else paper.get('abstract', '')
        quality = calculate_quality_score(summary)

        # 计算综合推荐评分
        recommendation_score = calculate_recommendation_score(
            relevance, recency, popularity, quality, is_hot_paper_batch
        )

        # 近期窗口加分：S2 recent 窗口的论文更新鲜
        if paper.get('s2_window') == 'recent':
            recommendation_score += RECENT_WINDOW_BONUS
        if paper.get('openalex_window') == 'recent':
            recommendation_score += RECENT_WINDOW_BONUS

        # 纯 CS 论文降权：fieldsOfStudy 仅含 Computer Science 时降权
        fields = paper.get('fieldsOfStudy', [])
        if isinstance(fields, list) and len(fields) == 1 and fields[0] == 'Computer Science':
            recommendation_score += PURE_CS_PENALTY

        # 添加评分信息
        paper['scores'] = {
            'relevance': round(relevance, 2),
            'recency': round(recency, 2),
            'popularity': round(popularity, 2),
            'quality': round(quality, 2),
            'recommendation': recommendation_score
        }
        paper['matched_domain'] = matched_domain
        paper['matched_keywords'] = matched_keywords
        paper['is_hot_paper'] = is_hot_paper_batch

        scored_papers.append(paper)

    # 按推荐评分排序
    scored_papers.sort(key=lambda x: x['scores']['recommendation'], reverse=True)

    return scored_papers


def paper_identity_keys(paper: Dict) -> Set[str]:
    """Build stable identifiers for cross-source deduplication."""
    keys = set()
    external_ids = paper.get("externalIds") or {}
    doi = paper.get("doi") or external_ids.get("DOI")
    if doi:
        normalized_doi = re.sub(
            r"^https?://(?:dx\.)?doi\.org/",
            "",
            str(doi),
            flags=re.IGNORECASE,
        ).strip().lower()
        if normalized_doi:
            keys.add(f"doi:{normalized_doi}")

    arxiv_id = (
        paper.get("arxiv_id")
        or paper.get("arxivId")
        or external_ids.get("ArXiv")
        or external_ids.get("ARXIV")
    )
    if arxiv_id:
        keys.add(f"arxiv:{str(arxiv_id).removeprefix('arXiv:').lower()}")

    title = paper.get("title") or ""
    normalized_title = re.sub(r"\W+", " ", title.lower(), flags=re.UNICODE).strip()
    if normalized_title:
        keys.add(f"title:{normalized_title}")
    return keys


def main():
    """主函数"""
    import argparse

    default_config = os.environ.get('OBSIDIAN_VAULT_PATH', '')
    if default_config:
        default_config = os.path.join(default_config, '99_System', 'Config', 'research_interests.yaml')

    parser = argparse.ArgumentParser(
        description='Search and filter papers with OpenAlex, Semantic Scholar, and arXiv'
    )
    parser.add_argument('--config', type=str,
                        default=default_config or None,
                        help='Path to research interests config file (or set OBSIDIAN_VAULT_PATH env var)')
    parser.add_argument('--output', type=str, default='arxiv_filtered.json',
                        help='Output JSON file path')
    parser.add_argument('--max-results', type=int, default=200,
                        help='Maximum number of results to fetch from arXiv')
    parser.add_argument('--top-n', type=int, default=10,
                        help='Number of top papers to return')
    parser.add_argument('--target-date', type=str, default=None,
                        help='Target date (YYYY-MM-DD) for filtering')
    parser.add_argument('--categories', type=str,
                        default='physics.ao-ph,cs.AI,cs.LG,cs.CV',
                        help='Comma-separated list of arXiv categories')
    parser.add_argument('--skip-hot-papers', action='store_true',
                        help='Skip searching hot papers from Semantic Scholar')
    parser.add_argument('--skip-openalex', action='store_true',
                        help='Skip OpenAlex search')
    parser.add_argument('--focus', type=str, default='',
                        help='User-specified focus keywords for today (comma-separated)')
    parser.add_argument('--days', type=int, default=30,
                        help='Number of days to search back (default 30)')
    parser.add_argument('--cnki-results', type=str, default=None,
                        help='Path to CNKI results JSON file for merging (from cnki-search skill)')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stderr,
    )

    focus_keywords = [k.strip() for k in args.focus.split(',') if k.strip()] if args.focus else []
    if focus_keywords:
        logger.info("Focus keywords: %s", focus_keywords)

    if not args.config:
        logger.error("未指定配置文件路径。请通过 --config 参数或 OBSIDIAN_VAULT_PATH 环境变量设置。")
        return 1

    logger.info("Loading config from: %s", args.config)
    config = load_research_config(args.config)

    # 解析目标日期
    target_date = None
    if args.target_date:
        try:
            target_date = datetime.strptime(args.target_date, '%Y-%m-%d')
            logger.info("Target date: %s", args.target_date)
        except ValueError:
            logger.error("Invalid target date format: %s", args.target_date)
            return 1
    else:
        target_date = datetime.now()
        logger.info("Using current date: %s", target_date.strftime('%Y-%m-%d'))

    window_30d_start, window_30d_end, window_1y_start, window_1y_end = calculate_date_windows(target_date, days=args.days)
    logger.info("Date windows:")
    logger.info("  Recent %d days: %s to %s", args.days, window_30d_start.date(), window_30d_end.date())
    logger.info("  Past year (31-365 days): %s to %s", window_1y_start.date(), window_1y_end.date())

    # 解析分类
    categories = args.categories.split(',')

    strategy = config.get('search_strategy', {})
    openalex_enabled = strategy.get('openalex_enabled', True) and not args.skip_openalex
    semantic_scholar_enabled = (
        strategy.get('semantic_scholar_enabled', True) and not args.skip_hot_papers
    )
    all_scored_papers = []
    recent_papers = []
    hot_papers = []
    focus_papers = []
    s2_papers = []
    openalex_papers = []
    arxiv_all_papers = []

    if focus_keywords:
        # ========== Focus 模式：关键词搜索为主 ==========
        logger.info("=" * 70)
        logger.info("Step 1 (Focus): Keyword-based arXiv search for: %s", focus_keywords)
        logger.info("=" * 70)

        focus_papers = search_arxiv_by_keywords(
            keywords=focus_keywords,
            start_date=window_30d_start,
            end_date=window_30d_end,
            max_results=args.max_results
        )

        if focus_papers:
            scored_focus = filter_and_score_papers(
                papers=focus_papers,
                config=config,
                target_date=target_date,
                is_hot_paper_batch=False,
                focus_keywords=focus_keywords
            )
            logger.info("Scored %d focus keyword papers", len(scored_focus))
            all_scored_papers.extend(scored_focus)
        else:
            logger.warning("No papers found for focus keywords")

        # Semantic Scholar 也按 focus 搜索（补充高引用论文）
        if semantic_scholar_enabled:
            logger.info("=" * 70)
            logger.info("Step 2 (Focus): Searching hot papers for focus keywords from Semantic Scholar")
            logger.info("=" * 70)

            focus_query = " ".join(focus_keywords)
            try:
                hot_papers = search_semantic_scholar_hot_papers(
                    query=focus_query,
                    start_date=window_1y_start,
                    end_date=window_1y_end,
                    top_k=20
                )
            except Exception as e:
                logger.warning("Semantic Scholar focus search failed (non-fatal): %s", e)
                hot_papers = []

            if hot_papers:
                scored_hot = filter_and_score_papers(
                    papers=hot_papers,
                    config=config,
                    target_date=target_date,
                    is_hot_paper_batch=True,
                    focus_keywords=focus_keywords
                )
                logger.info("Scored %d hot papers for focus", len(scored_hot))
                all_scored_papers.extend(scored_hot)

        if openalex_enabled:
            logger.info("=" * 70)
            logger.info("Step 3 (Focus): Searching OpenAlex for focus keywords")
            logger.info("=" * 70)
            try:
                openalex_papers = search_openalex_papers(
                    query=" ".join(focus_keywords),
                    start_date=window_1y_start,
                    end_date=target_date,
                    top_k=strategy.get('openalex_limit_per_query', 20),
                )
            except Exception as e:
                logger.warning("OpenAlex focus search failed (non-fatal): %s", e)
                openalex_papers = []

            for paper in openalex_papers:
                paper['openalex_domain'] = 'focus'
                paper['openalex_window'] = 'focus'
            if openalex_papers:
                scored_openalex = filter_and_score_papers(
                    papers=openalex_papers,
                    config=config,
                    target_date=target_date,
                    is_hot_paper_batch=True,
                    focus_keywords=focus_keywords,
                )
                logger.info("Scored %d OpenAlex papers for focus", len(scored_openalex))
                all_scored_papers.extend(scored_openalex)

    else:
        # ========== 普通模式：OpenAlex + S2 为主，arXiv 补充 ==========
        s2_queries_config = strategy.get('s2_queries', {})
        s2_recent_days = strategy.get('s2_recent_days', 30)
        s2_mid_days = strategy.get('s2_mid_days', 365)
        s2_hot_days = strategy.get('s2_hot_days', 730)
        s2_limit = strategy.get('s2_limit_per_query', 50)
        arxiv_mode = strategy.get('arxiv_search_mode', 'keyword')
        s2_fields = strategy.get('s2_fields_of_study', None)
        s2_min_cit = strategy.get('s2_min_citation_count', 0)

        # ---- Step 1: Semantic Scholar 领域查询（主） ----
        # 拆分为近期(30天)和中期(31-365天)两个窗口
        logger.info("=" * 70)
        logger.info("Step 1: Semantic Scholar domain-specific queries (PRIMARY)")
        logger.info("=" * 70)

        # 收集所有领域的查询
        all_s2_queries = []
        for domain_name, queries in s2_queries_config.items():
            for q in queries:
                all_s2_queries.append((domain_name, q))

        # 如果配置中没有查询模板，从领域关键词自动生成
        if not all_s2_queries:
            domains = config.get('research_domains', {})
            for domain_name, domain_config in domains.items():
                keywords = domain_config.get('keywords', [])
                if keywords:
                    query = ' '.join(keywords[:3])
                    all_s2_queries.append((domain_name, query))
        if not semantic_scholar_enabled:
            logger.info("Semantic Scholar disabled by configuration or --skip-hot-papers")
            all_s2_queries = []

        # 执行 S2 搜索 —— 拆分为近期 + 中期两个窗口
        s2_papers = []
        seen_s2_ids = set()

        # 1a. 近期窗口（最近30天）：所有论文，无引用门槛
        s2_recent_start = target_date - timedelta(days=s2_recent_days)
        s2_recent_end = target_date
        logger.info("[S2] Recent window: %s to %s", s2_recent_start.date(), s2_recent_end.date())

        for domain_name, query in all_s2_queries:
            logger.info("[S2-Recent] Domain '%s' query: '%s'", domain_name, query)
            try:
                papers = search_semantic_scholar_hot_papers(
                    query=query,
                    start_date=s2_recent_start,
                    end_date=s2_recent_end,
                    top_k=s2_limit,
                    fields_of_study=s2_fields,
                    min_citation_count=0  # 近期论文引用少属正常，不过滤
                )
            except Exception as e:
                logger.warning("[S2-Recent] Query '%s' failed: %s — skipping", query, e)
                papers = []

            for p in papers:
                pid = p.get('paperId') or p.get('externalIds', {}).get('CorpusId')
                if pid and pid not in seen_s2_ids:
                    seen_s2_ids.add(pid)
                    p['s2_domain'] = domain_name
                    p['s2_window'] = 'recent'
                    s2_papers.append(p)

            time.sleep(S2_CATEGORY_REQUEST_INTERVAL)

        # 1b. 中期窗口（31-365天）：要求有引用
        s2_mid_start = target_date - timedelta(days=s2_mid_days)
        s2_mid_end = target_date - timedelta(days=s2_recent_days + 1)
        logger.info("[S2] Mid-term window: %s to %s", s2_mid_start.date(), s2_mid_end.date())

        for domain_name, query in all_s2_queries:
            logger.info("[S2-Mid] Domain '%s' query: '%s'", domain_name, query)
            try:
                papers = search_semantic_scholar_hot_papers(
                    query=query,
                    start_date=s2_mid_start,
                    end_date=s2_mid_end,
                    top_k=s2_limit,
                    fields_of_study=s2_fields,
                    min_citation_count=max(s2_min_cit, 5)  # 中期论文至少5引用
                )
            except Exception as e:
                logger.warning("[S2-Mid] Query '%s' failed: %s — skipping", query, e)
                papers = []

            for p in papers:
                pid = p.get('paperId') or p.get('externalIds', {}).get('CorpusId')
                if pid and pid not in seen_s2_ids:
                    seen_s2_ids.add(pid)
                    p['s2_domain'] = domain_name
                    p['s2_window'] = 'mid'
                    s2_papers.append(p)

            time.sleep(S2_CATEGORY_REQUEST_INTERVAL)

        if s2_papers:
            scored_s2 = filter_and_score_papers(
                papers=s2_papers,
                config=config,
                target_date=target_date,
                is_hot_paper_batch=True,
            )
            logger.info("Scored %d S2 papers", len(scored_s2))
            all_scored_papers.extend(scored_s2)
        else:
            logger.warning("No papers found from Semantic Scholar")

        # ---- Step 2: OpenAlex 领域查询（主） ----
        if openalex_enabled:
            logger.info("=" * 70)
            logger.info("Step 2: OpenAlex domain-specific queries (PRIMARY)")
            logger.info("=" * 70)

            openalex_queries_config = strategy.get('openalex_queries', s2_queries_config)
            openalex_limit = strategy.get('openalex_limit_per_query', 25)
            openalex_min_cit = strategy.get('openalex_min_citation_count', 0)
            all_openalex_queries = []
            for domain_name, queries in openalex_queries_config.items():
                for query in queries:
                    all_openalex_queries.append((domain_name, query))
            if not all_openalex_queries:
                all_openalex_queries = list(all_s2_queries)

            seen_openalex_ids = set()
            for window_name, start_date, end_date, min_citations in (
                ('recent', s2_recent_start, s2_recent_end, 0),
                ('mid', s2_mid_start, s2_mid_end, max(openalex_min_cit, 5)),
            ):
                logger.info(
                    "[OpenAlex] %s window: %s to %s",
                    window_name,
                    start_date.date(),
                    end_date.date(),
                )
                for domain_name, query in all_openalex_queries:
                    try:
                        papers = search_openalex_papers(
                            query=query,
                            start_date=start_date,
                            end_date=end_date,
                            top_k=openalex_limit,
                            min_citation_count=min_citations,
                        )
                    except Exception as e:
                        logger.warning("[OpenAlex] Query '%s' failed: %s -- skipping", query, e)
                        papers = []
                    for paper in papers:
                        paper_id = paper.get('paperId')
                        if paper_id and paper_id not in seen_openalex_ids:
                            seen_openalex_ids.add(paper_id)
                            paper['openalex_domain'] = domain_name
                            paper['openalex_window'] = window_name
                            openalex_papers.append(paper)
                    time.sleep(OPENALEX_REQUEST_INTERVAL)

            if openalex_papers:
                scored_openalex = filter_and_score_papers(
                    papers=openalex_papers,
                    config=config,
                    target_date=target_date,
                    is_hot_paper_batch=True,
                )
                logger.info("Scored %d OpenAlex papers", len(scored_openalex))
                all_scored_papers.extend(scored_openalex)
            else:
                logger.warning("No papers found from OpenAlex")

        # ---- Step 3: arXiv 关键词搜索（补充） ----
        logger.info("=" * 70)
        logger.info("Step 3: arXiv keyword search (SUPPLEMENTARY)")
        logger.info("=" * 70)

        if arxiv_mode == 'keyword' or strategy.get('arxiv_use_domain_keywords', True):
            # 优先使用配置中的 arxiv_domain_queries（AND-logic 精准查询）
            domain_queries = strategy.get('arxiv_domain_queries', {})
            if domain_queries:
                logger.info("[arXiv] Using domain-specific AND-logic queries from config")
                for domain_name, queries in domain_queries.items():
                    for query_str in queries:
                        logger.info("[arXiv] Domain '%s' query: '%s'", domain_name, query_str)
                        try:
                            # 将 AND-logic 字符串拆分为关键词列表
                            # 格式如 "marine heatwave AND fishery" → ["marine heatwave", "fishery"]
                            kw_list = [k.strip() for k in query_str.split(' AND ') if k.strip()]
                            papers = search_arxiv_by_keywords(
                                keywords=kw_list,
                                start_date=window_30d_start,
                                end_date=window_30d_end,
                                max_results=min(args.max_results, 50)  # 每个查询限制50篇
                            )
                            for p in papers:
                                p['arxiv_domain'] = domain_name
                            arxiv_all_papers.extend(papers)
                        except Exception as e:
                            logger.warning("[arXiv] Domain query '%s' failed: %s", query_str, e)
                        time.sleep(3)  # arXiv API 请求间隔
            else:
                # 回退：从领域关键词提取 arXiv 搜索词
                arxiv_keywords = []
                domains = config.get('research_domains', {})
                for domain_name, domain_config in domains.items():
                    kws = domain_config.get('keywords', [])
                    en_kws = [k for k in kws if re.match(r'^[A-Za-z]', k)]
                    arxiv_keywords.extend(en_kws[:5])

                if arxiv_keywords:
                    logger.info("[arXiv] Fallback keyword search with: %s", arxiv_keywords[:10])
                    arxiv_all_papers = search_arxiv_by_keywords(
                        keywords=arxiv_keywords,
                        start_date=window_30d_start,
                        end_date=window_30d_end,
                        max_results=args.max_results
                    )

            if arxiv_all_papers:
                scored_kw = filter_and_score_papers(
                    papers=arxiv_all_papers,
                    config=config,
                    target_date=target_date,
                    is_hot_paper_batch=False,
                )
                logger.info("Scored %d arXiv papers", len(scored_kw))
                all_scored_papers.extend(scored_kw)
        else:
            # 回退到分类搜索
            recent_papers = search_arxiv_by_date_range(
                categories=categories,
                start_date=window_30d_start,
                end_date=window_30d_end,
                max_results=args.max_results
            )
            if recent_papers:
                scored_recent = filter_and_score_papers(
                    papers=recent_papers,
                    config=config,
                    target_date=target_date,
                    is_hot_paper_batch=False,
                )
                logger.info("Scored %d arXiv category papers", len(scored_recent))
                all_scored_papers.extend(scored_recent)

    # ========== 第三步：合并CNKI结果（如有） ==========
    cnki_papers_count = 0
    if args.cnki_results:
        try:
            with open(args.cnki_results, 'r', encoding='utf-8') as f:
                cnki_data = json.load(f)
            cnki_papers = cnki_data if isinstance(cnki_data, list) else cnki_data.get('papers', [])
            for p in cnki_papers:
                p['source'] = 'cnki'
                p['s2_window'] = 'recent'
            scored_cnki = filter_and_score_papers(
                papers=cnki_papers,
                config=config,
                target_date=target_date,
                is_hot_paper_batch=False,
            )
            cnki_papers_count = len(scored_cnki)
            logger.info("Scored %d CNKI papers", cnki_papers_count)
            all_scored_papers.extend(scored_cnki)
        except Exception as e:
            logger.warning("Failed to load/merge CNKI results from '%s': %s", args.cnki_results, e)

    # ========== 第四步：合并结果并排序 ==========
    logger.info("=" * 70)
    logger.info("Step 4: Merging and ranking results (OpenAlex + S2 + arXiv + CNKI)")
    logger.info("=" * 70)
    
    # 按推荐评分排序
    all_scored_papers.sort(key=lambda x: x['scores']['recommendation'], reverse=True)
    
    # DOI、arXiv ID 和标准化标题任一相同即视为同一论文。
    seen_identity_keys = set()
    unique_papers = []
    for p in all_scored_papers:
        identity_keys = paper_identity_keys(p)
        if not identity_keys or seen_identity_keys.intersection(identity_keys):
            continue
        seen_identity_keys.update(identity_keys)
        unique_papers.append(p)
    
    logger.info("Total unique papers after deduplication: %d", len(unique_papers))

    if len(unique_papers) == 0:
        logger.warning("No papers matched the criteria!")
        return 1

    # 取前 N 篇
    top_papers = unique_papers[:args.top_n]

    # 为每篇论文补充 note_filename，与 generate_note.py 的文件名规则保持一致
    # 这样 start-my-day 生成的 wikilink 可以直接使用此字段，无需自行推断
    for paper in top_papers:
        paper['note_filename'] = title_to_note_filename(
            paper.get('title', ''),
            paper.get('authors', ''),
            paper.get('published') or paper.get('publicationDate', '')
        )

    source_counts = {}
    for paper in unique_papers:
        source = paper.get('source', 'unknown')
        source_counts[source] = source_counts.get(source, 0) + 1

    arxiv_count = len(focus_papers) if focus_keywords else len(arxiv_all_papers) + len(recent_papers)

    # 准备输出
    output = {
        'target_date': args.target_date or target_date.strftime('%Y-%m-%d'),
        'date_windows': {
            'recent_30d': {
                'start': window_30d_start.strftime('%Y-%m-%d'),
                'end': window_30d_end.strftime('%Y-%m-%d')
            },
            'past_year': {
                'start': window_1y_start.strftime('%Y-%m-%d'),
                'end': window_1y_end.strftime('%Y-%m-%d')
            }
        },
        'total_openalex': len(openalex_papers),
        'total_s2': len(hot_papers) if focus_keywords else len(s2_papers),
        'total_arxiv': arxiv_count,
        'total_cnki': cnki_papers_count,
        'source_counts': source_counts,
        'total_unique': len(unique_papers),
        'top_papers': top_papers
    }

    # 保存结果
    json_str = json.dumps(output, ensure_ascii=False, indent=2, default=str)
    if args.output == '-' or args.output == '/dev/stdout':
        sys.stdout.write(json_str)
        sys.stdout.write('\n')
    else:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(json_str)
        logger.info("Results saved to: %s", args.output)
        # 同时输出到 stdout
        print(json_str)

    logger.info("Top %d papers:", len(top_papers))
    for i, p in enumerate(top_papers, 1):
        hot_marker = " [HOT]" if p.get('is_hot_paper') else ""
        logger.info("  %d. %s... (Score: %s)%s", i, p.get('title', 'N/A')[:60], p['scores']['recommendation'], hot_marker)

    return 0


if __name__ == '__main__':
    sys.exit(main())
