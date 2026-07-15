#!/usr/bin/env python3
"""
扫描 Obsidian vault 中的论文笔记，构建关键词索引
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def extract_frontmatter(content):
    """从 markdown 内容中提取 frontmatter"""
    if not content.startswith('---'):
        return {}
    end = content.find('---', 3)
    if end == -1:
        return {}
    fm_text = content[3:end].strip()
    result = {}
    for line in fm_text.split('\n'):
        line = line.strip()
        if ':' in line and not line.startswith('-'):
            key, _, val = line.partition(':')
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and val:
                result[key] = val
    return result


def extract_title_keywords(title):
    """从标题中提取关键词"""
    if not title:
        return []
    # 按常见分隔符拆分
    parts = re.split(r'[:\-\s_|,;]+', title)
    keywords = []
    for p in parts:
        p = p.strip()
        if len(p) >= 3 and not p.lower() in ('the', 'and', 'for', 'with', 'from', 'using', 'based', 'via', 'over', 'into', 'through'):
            keywords.append(p)
    return keywords


def extract_tag_keywords(tags_str):
    """从 tags 字符串中提取关键词"""
    if not tags_str:
        return []
    # Handle list format [tag1, tag2]
    tags = re.findall(r'[\w\-]+', tags_str)
    return [t for t in tags if len(t) >= 3]


def scan_notes(vault_path, papers_dir_name='论文笔记'):
    """扫描论文笔记目录"""
    papers_dir = os.path.join(vault_path, papers_dir_name)
    if not os.path.isdir(papers_dir):
        print(f"Warning: {papers_dir} not found", file=sys.stderr)
        return [], {}

    notes = []
    keyword_to_notes = {}

    for root, dirs, files in os.walk(papers_dir):
        for fname in files:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, vault_path)

            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue

            fm = extract_frontmatter(content)
            title = fm.get('title', '')
            tags_str = fm.get('tags', '')

            # 提取关键词
            title_kws = extract_title_keywords(title)
            tag_kws = extract_tag_keywords(tags_str)

            all_kws = list(set(title_kws + tag_kws))

            note_info = {
                'path': rel_path,
                'filename': fname,
                'title': title,
                'title_keywords': title_kws,
                'tags': tag_kws,
            }
            notes.append(note_info)

            for kw in all_kws:
                kw_lower = kw.lower()
                if kw_lower not in keyword_to_notes:
                    keyword_to_notes[kw_lower] = []
                keyword_to_notes[kw_lower].append(rel_path)

    return notes, keyword_to_notes


def main():
    parser = argparse.ArgumentParser(description='Scan existing paper notes in Obsidian vault')
    parser.add_argument('--vault', type=str, required=True, help='Path to Obsidian vault')
    parser.add_argument('--papers-dir', type=str, default='论文笔记',
                        help='Paper note directory relative to the vault')
    parser.add_argument('--output', type=str, required=True, help='Output JSON file path')

    args = parser.parse_args()

    notes, keyword_to_notes = scan_notes(args.vault, args.papers_dir)

    result = {
        'notes': notes,
        'keyword_to_notes': keyword_to_notes,
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Scanned {len(notes)} notes, {len(keyword_to_notes)} keywords", file=sys.stderr)


if __name__ == '__main__':
    main()
