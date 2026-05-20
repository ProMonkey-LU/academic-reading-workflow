#!/usr/bin/env python3
"""
Zotero 导入脚本：将推荐论文导入到 Zotero 每日阅读分类

使用 Zotero MCP 插件的 Streamable HTTP MCP 协议（port 23120）导入论文。
支持：
1. 通过 write_item 创建条目（journalArticle / preprint）
2. 通过 create_collection 创建分类
3. 通过 add_items_to_collection 添加条目到分类
4. 通过 search_library 检查已有条目避免重复
5. 返回 Zotero item key 用于笔记链接

使用方式：
  python zotero_import.py --input arxiv_filtered.json --top-n 3 --collection "MHWs"
  python zotero_import.py --arxiv-id "2602.12345" --title "Paper Title" --collection "MHWs"
  python zotero_import.py --doi "10.1234/xxx" --title "Paper Title"

依赖：Zotero 运行中，MCP 插件已安装并启用（port 23120）
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
import re
from datetime import datetime


MCP_URL = "http://127.0.0.1:23120/mcp"
_req_id = 0


def mcp_call(method, params=None):
    """发送 JSON-RPC 请求到 Zotero MCP 插件"""
    global _req_id
    _req_id += 1
    payload = {
        "jsonrpc": "2.0",
        "id": _req_id,
        "method": method,
        "params": params or {},
    }
    try:
        req = urllib.request.Request(
            MCP_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        if 'error' in result:
            print(f"MCP Error: {result['error']}", file=sys.stderr)
            return None
        return result.get('result')
    except Exception as e:
        print(f"MCP call failed: {e}", file=sys.stderr)
        return None


def mcp_tool(name, arguments):
    """调用 MCP tool，返回解析后的 data dict 或 None"""
    result = mcp_call("tools/call", {"name": name, "arguments": arguments})
    if not result:
        return None
    content = result.get('content', [])
    if content and isinstance(content, list) and len(content) > 0:
        text = content[0].get('text', '')
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_text": text}
    return None


def check_zotero_running():
    """检查 Zotero MCP 插件是否运行"""
    result = mcp_call("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "zotero-import", "version": "1.0"},
    })
    return result is not None


def search_item(query, limit=5):
    """搜索已有条目"""
    result = mcp_tool("search_library", {"q": query, "limit": limit})
    if not result:
        return []
    # search_library returns items directly or nested
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        items = result.get('items', result.get('results', []))
        return items if isinstance(items, list) else []
    return []


def find_item_by_doi(doi):
    """通过 DOI 查找已有条目"""
    if not doi:
        return None
    items = search_item(doi, limit=5)
    for item in items:
        if isinstance(item, dict):
            if item.get('DOI', '').lower() == doi.lower():
                return item.get('key')
    return None


def find_item_by_arxiv_id(arxiv_id):
    """通过 arXiv ID 查找已有条目"""
    items = search_item(arxiv_id, limit=5)
    for item in items:
        if isinstance(item, dict):
            extra = item.get('extra', '')
            url = item.get('url', '')
            if arxiv_id in extra or arxiv_id in url:
                return item.get('key')
    return None


def find_collection(name, parent_key=None):
    """查找分类"""
    result = mcp_tool("search_collections", {"q": name})
    if not result:
        return None
    collections = []
    if isinstance(result, list):
        collections = result
    elif isinstance(result, dict):
        collections = result.get('collections', result.get('results', []))
        if not isinstance(collections, list):
            collections = []

    for col in collections:
        if isinstance(col, dict):
            col_name = col.get('name', col.get('collectionName', ''))
            col_key = col.get('key', col.get('collectionKey', ''))
            if col_name == name:
                if parent_key is None or col.get('parentCollection') == parent_key:
                    return col_key
    return None


def find_or_create_collection(collection_path):
    """
    查找或创建嵌套分类

    Args:
        collection_path: 分类路径，如 "每日阅读/2026-05"

    Returns:
        collection key
    """
    parts = [p.strip() for p in collection_path.split('/') if p.strip()]
    if not parts:
        return None

    parent_key = None
    for part in parts:
        found = find_collection(part, parent_key=parent_key)
        if found:
            parent_key = found
        else:
            # 创建新分类
            args = {"name": part}
            if parent_key:
                args["parentCollection"] = parent_key
            result = mcp_tool("create_collection", args)
            if result and isinstance(result, dict):
                data = result.get('data', result)
                new_key = data.get('key', data.get('collectionKey'))
                if new_key:
                    parent_key = new_key
                else:
                    print(f"Warning: Created collection but couldn't get key", file=sys.stderr)
                    return None
            else:
                print(f"Warning: Failed to create collection '{part}'", file=sys.stderr)
                return None

    return parent_key


def create_item(item_type, fields, creators=None, tags=None, collection_key=None):
    """
    创建 Zotero 条目

    Args:
        item_type: 条目类型（journalArticle, preprint, etc.）
        fields: 元数据字段
        creators: 作者列表
        tags: 标签列表
        collection_key: 目标分类 key

    Returns:
        item key 或 None
    """
    args = {
        "action": "create",
        "itemType": item_type,
        "fields": fields,
    }
    if creators:
        args["creators"] = creators
    if tags:
        args["tags"] = tags

    result = mcp_tool("write_item", args)
    if not result:
        return None

    # result is already parsed JSON from mcp_tool
    if isinstance(result, dict):
        data = result.get('data', result)
        item_key = data.get('itemKey') or data.get('key')
        if not item_key:
            # Try regex from raw text
            text = result.get('raw_text', json.dumps(result))
            match = re.search(r'"itemKey"\s*:\s*"([A-Z0-9]{8})"', text)
            if not match:
                match = re.search(r'"key"\s*:\s*"([A-Z0-9]{8})"', text)
            if match:
                item_key = match.group(1)

        if item_key and collection_key:
            add_to_collection(item_key, collection_key)

        return item_key

    return None


def add_to_collection(item_key, collection_key):
    """将条目添加到分类"""
    result = mcp_tool("add_items_to_collection", {
        "collectionKey": collection_key,
        "itemKeys": [item_key],
    })
    return result is not None


def parse_authors(authors_str):
    """解析作者字符串为 Zotero creators 格式"""
    creators = []
    if not authors_str:
        return creators

    for a in authors_str.split(','):
        a = a.strip()
        if not a:
            continue
        parts = a.rsplit(' ', 1)
        if len(parts) == 2:
            creators.append({
                'creatorType': 'author',
                'firstName': parts[0],
                'lastName': parts[1],
            })
        else:
            creators.append({
                'creatorType': 'author',
                'lastName': a,
                'firstName': '',
            })
    return creators


def import_paper(paper, collection_key=None):
    """
    导入单篇论文到 Zotero

    Args:
        paper: 论文信息 dict
        collection_key: 目标分类 key

    Returns:
        dict with item_key, zotero_link, etc. 或 None
    """
    title = paper.get('title', 'Unknown')
    doi = paper.get('doi') or paper.get('DOI')
    arxiv_id = paper.get('arxiv_id') or paper.get('arxivId')
    # authors 可能是 str 或 list[dict]（S2 API 格式）
    authors_raw = paper.get('authors', '')
    if isinstance(authors_raw, list):
        # S2 格式: [{"name": "...", "authorId": "..."}]
        authors_str = ', '.join(
            a.get('name', '') if isinstance(a, dict) else str(a)
            for a in authors_raw if (a.get('name', '') if isinstance(a, dict) else str(a))
        )
    else:
        authors_str = authors_raw
    abstract = paper.get('summary', '') if 'summary' in paper else paper.get('abstract', '')
    pub_date = paper.get('publicationDate') or paper.get('published', '')
    source = paper.get('source', '')

    # 如果有 URL，提取 arXiv ID
    url = paper.get('url', '')
    if not arxiv_id and url:
        arxiv_match = re.search(r'(\d{4}\.\d{4,5})', url)
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)

    # 1. 先搜索已有条目
    existing_key = None
    if doi:
        existing_key = find_item_by_doi(doi)
    if not existing_key and arxiv_id:
        existing_key = find_item_by_arxiv_id(arxiv_id)

    if existing_key:
        print(f"  Found existing item: {existing_key}", file=sys.stderr)
        if collection_key:
            add_to_collection(existing_key, collection_key)
        return {
            'item_key': existing_key,
            'zotero_link': f"zotero://select/items/0_{existing_key}",
            'title': title,
            'method': 'existing',
        }

    # 2. 构建条目数据
    creators = parse_authors(authors_str)

    # 判断条目类型
    is_arxiv_doi = doi and 'arXiv' in doi
    is_arxiv_paper = bool(arxiv_id) or 'arxiv' in source.lower() or is_arxiv_doi

    if doi and not is_arxiv_doi and not is_arxiv_paper:
        # 正式发表的期刊论文
        fields = {
            'title': title,
            'DOI': doi,
            'abstractNote': abstract[:2000] if abstract else '',
            'url': url or f"https://doi.org/{doi}",
        }
        if pub_date:
            fields['date'] = str(pub_date)[:10]
        item_type = 'journalArticle'
    elif arxiv_id:
        # arXiv 预印本
        fields = {
            'title': title,
            'repository': 'arXiv',
            'archiveID': f"arXiv:{arxiv_id}",
            'url': f"https://arxiv.org/abs/{arxiv_id}",
            'abstractNote': abstract[:2000] if abstract else '',
        }
        if pub_date:
            fields['date'] = str(pub_date)[:10]
        item_type = 'preprint'
    else:
        # 其他来源
        fields = {
            'title': title,
            'abstractNote': abstract[:2000] if abstract else '',
        }
        if url:
            fields['url'] = url
        if doi:
            fields['DOI'] = doi
        if pub_date:
            fields['date'] = str(pub_date)[:10]
        item_type = 'report'

    # 3. 创建条目
    tags = ["start-my-day"]
    item_key = create_item(item_type, fields, creators=creators, tags=tags, collection_key=collection_key)

    if not item_key:
        print(f"  Failed to create item", file=sys.stderr)
        return None

    return {
        'item_key': item_key,
        'zotero_link': f"zotero://select/items/0_{item_key}",
        'title': title,
        'method': 'mcp_write_item',
    }


def main():
    parser = argparse.ArgumentParser(description='Import papers to Zotero via MCP plugin')
    parser.add_argument('--input', type=str, help='Path to arxiv_filtered.json')
    parser.add_argument('--top-n', type=int, default=3, help='Import top N papers (default 3)')
    parser.add_argument('--collection', type=str, default=None,
                        help='Collection path (e.g., "MHWs", "每日阅读/2026-05")')
    parser.add_argument('--doi', type=str, default=None, help='Single DOI to import')
    parser.add_argument('--arxiv-id', type=str, default=None, help='Single arXiv ID to import')
    parser.add_argument('--title', type=str, default='', help='Paper title (for single import)')
    parser.add_argument('--authors', type=str, default='', help='Paper authors (for single import)')
    parser.add_argument('--output', type=str, default='zotero_import_results.json',
                        help='Output JSON file for import results')

    args = parser.parse_args()

    # 检查 Zotero MCP 插件是否运行
    if not check_zotero_running():
        print("Error: Zotero MCP plugin not running (is Zotero running with MCP plugin enabled?)", file=sys.stderr)
        return 1

    # 查找或创建分类
    collection_key = None
    if args.collection:
        collection_key = find_or_create_collection(args.collection)
        if collection_key:
            print(f"Collection: {args.collection} (key: {collection_key})")
        else:
            print(f"Warning: Could not find/create collection '{args.collection}'. Items will be added to root.", file=sys.stderr)

    results = []

    # 单篇导入模式
    if args.doi:
        paper = {'doi': args.doi, 'title': args.title, 'authors': args.authors, 'source': ''}
        result = import_paper(paper, collection_key=collection_key)
        if result:
            results.append(result)
            print(f"Imported via DOI: {result.get('zotero_link', 'OK')}")

    elif args.arxiv_id:
        paper = {'arxiv_id': args.arxiv_id, 'title': args.title, 'authors': args.authors, 'source': 'arXiv'}
        result = import_paper(paper, collection_key=collection_key)
        if result:
            results.append(result)
            print(f"Imported via arXiv: {result.get('zotero_link', 'OK')}")

    # 批量导入模式
    elif args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading input file: {e}", file=sys.stderr)
            return 1

        top_papers = data.get('top_papers', data if isinstance(data, list) else [])
        papers_to_import = top_papers[:args.top_n]

        for i, paper in enumerate(papers_to_import):
            title = paper.get('title', f'Paper {i+1}')
            print(f"\nImporting {i+1}/{len(papers_to_import)}: {title[:60]}...")

            result = import_paper(paper, collection_key=collection_key)
            if result:
                result['paper_index'] = i
                result['paper_title'] = title
                results.append(result)
                print(f"  -> {result.get('zotero_link', 'OK')} (via {result['method']})")
            else:
                print(f"  -> FAILED")

            time.sleep(1)

    # 保存结果
    output_data = {
        'collection': args.collection,
        'collection_key': collection_key,
        'imported_count': len(results),
        'results': results,
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\nImport complete: {len(results)} papers processed")
    print(f"Results saved to: {args.output}")

    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
