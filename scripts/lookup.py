#!/usr/bin/env python3
"""
copywriting-skill-pack 模板检索与精确提取工具（零第三方依赖）

用法示例:
  python3 scripts/lookup.py search --q 种草 --dir 变现
  python3 scripts/lookup.py search --track 美妆 --with-case --limit 10
  python3 scripts/lookup.py get T01 M04
  python3 scripts/lookup.py get P05 --brief
  python3 scripts/lookup.py list --dir 流量
  python3 scripts/lookup.py stats
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REFS_DIR = Path(__file__).resolve().parent.parent / "references"

DIR_MAP = {
    "T": ("流量", "traffic-templates.md"),
    "P": ("人设", "persona-templates.md"),
    "G": ("涨粉", "growth-templates.md"),
    "M": ("变现", "monetization-templates.md"),
}

DIR_ALIASES = {
    "流量": "T", "traffic": "T", "t": "T",
    "人设": "P", "persona": "P", "p": "P",
    "涨粉": "G", "growth": "G", "g": "G",
    "变现": "M", "monetization": "M", "m": "M",
}


def parse_file(prefix: str, direction: str, filename: str):
    path = REFS_DIR / filename
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?=^### [TPGM]\d{2}\. )", text, flags=re.M)[1:]
    items = []
    for block in blocks:
        m_id = re.match(r"^### ([TPGM]\d{2})\.\s*(.+)$", block.splitlines()[0])
        if not m_id:
            continue
        tid = m_id.group(1)

        def field(key: str) -> str:
            m = re.search(rf"^- \*\*{key}\*\*：(.+)$", block, re.M)
            return m.group(1).strip() if m else ""

        has_case = "<summary>📖 原文案例" in block
        items.append({
            "id": tid,
            "prefix": prefix,
            "direction": direction,
            "name": field("模版名称"),
            "type": field("模版类型"),
            "topic": field("模版选题"),
            "track": field("所属赛道"),
            "format": field("呈现建议"),
            "structure": field("模版结构"),
            "has_case": has_case,
            "raw": block.strip(),
        })
    return items


def load_all(dir_filter: str | None = None):
    prefixes = list(DIR_MAP.keys())
    if dir_filter:
        key = DIR_ALIASES.get(dir_filter.strip().lower())
        if not key:
            print(f"未知方向：{dir_filter}（可选：流量/人设/涨粉/变现 或 T/P/G/M）", file=sys.stderr)
            sys.exit(1)
        prefixes = [key]
    results = []
    for p in prefixes:
        cn, fn = DIR_MAP[p]
        results.extend(parse_file(p, cn, fn))
    return results


def print_table(items):
    if not items:
        print("未找到匹配的模板。")
        return
    print("| ID | 方向 | 模版名称 | 模版选题 | 赛道 | 呈现 | 案例 | 模版结构 |")
    print("|---|---|---|---|---|---|---|---|")
    for it in items:
        case_flag = "有" if it["has_case"] else "无"
        row = [
            it["id"], it["direction"], it["name"], it["topic"],
            it["track"], it["format"], case_flag, it["structure"]
        ]
        row = [c.replace("|", "｜") for c in row]
        print("| " + " | ".join(row) + " |")


def cmd_search(args):
    items = load_all(args.dir)
    if args.with_case:
        items = [it for it in items if it["has_case"]]
    if args.track:
        kw = args.track.lower()
        items = [it for it in items if kw in it["track"].lower()]
    if args.format:
        kw = args.format.lower()
        items = [it for it in items if kw in it["format"].lower()]
    if args.q:
        keywords = [k.lower() for k in re.split(r"[\s,，]+", args.q.strip()) if k]
        scored = []
        for it in items:
            hay_meta = f"{it['id']} {it['name']} {it['topic']} {it['track']} {it['format']} {it['structure']}".lower()
            hay_full = it["raw"].lower() if args.fulltext else hay_meta
            if all(k in hay_full for k in keywords):
                score = sum(3 if k in it["name"].lower() else (2 if k in hay_meta else 1) for k in keywords)
                if it["has_case"]:
                    score += 0.5
                scored.append((score, it))
        scored.sort(key=lambda x: -x[0])
        items = [it for _, it in scored]

    total = len(items)
    shown = items[: args.limit] if args.limit > 0 else items
    print(f"匹配到 {total} 个模板（展示前 {len(shown)} 个）：\n")
    print_table(shown)


def extract_brief(raw: str) -> str:
    """仅保留标题、元数据字段和原文案例（拆片演示），跳过大段注意事项/裂变思路。"""
    parts = re.split(r"(?=<details>)", raw)
    out = [parts[0].rstrip()]
    for p in parts[1:]:
        if "原文案例" in p.splitlines()[1:3].__str__():
            out.append(p.strip())
    return "\n\n".join(out)


def cmd_get(args):
    all_items = {it["id"]: it for it in load_all()}
    by_name = {}
    for it in all_items.values():
        by_name.setdefault(it["name"], []).append(it)

    not_found = []
    for target in args.ids:
        t_upper = target.strip().upper()
        if t_upper in all_items:
            it = all_items[t_upper]
            print(extract_brief(it["raw"]) if args.brief else it["raw"])
            print("\n---\n")
        elif target.strip() in by_name:
            matches = by_name[target.strip()]
            if len(matches) > 1:
                print(f"模板名「{target}」存在 {len(matches)} 个同名条目，请用唯一 ID 精确提取：\n")
                print_table(matches)
                print()
            else:
                it = matches[0]
                print(extract_brief(it["raw"]) if args.brief else it["raw"])
                print("\n---\n")
        else:
            not_found.append(target)

    if not_found:
        print(f"未找到：{', '.join(not_found)}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args):
    items = load_all(args.dir)
    if args.with_case:
        items = [it for it in items if it["has_case"]]
    print(f"共 {len(items)} 个模板：\n")
    print_table(items)


def cmd_stats(_args):
    items = load_all()
    print(f"总模板数：{len(items)}（有原文案例：{sum(1 for i in items if i['has_case'])}，缺案例：{sum(1 for i in items if not i['has_case'])}）\n")
    by_dir = Counter(i["direction"] for i in items)
    print("各方向数量：", dict(by_dir))
    by_fmt = Counter(i["format"] for i in items).most_common(10)
    print("Top 10 呈现建议：", by_fmt)
    by_track = Counter(i["track"] for i in items).most_common(12)
    print("Top 12 所属赛道：", by_track)


def main():
    parser = argparse.ArgumentParser(description="copywriting-skill-pack 模板检索与提取工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="按方向/关键词/赛道/呈现形式检索模板")
    p_search.add_argument("--dir", "-d", help="方向：流量/人设/涨粉/变现 或 T/P/G/M")
    p_search.add_argument("--q", "-q", help="关键词（空格或逗号分隔表示 AND）")
    p_search.add_argument("--track", help="赛道筛选，如：美妆、职场、摄影")
    p_search.add_argument("--format", help="呈现建议筛选，如：口播、Vlog、图文")
    p_search.add_argument("--with-case", action="store_true", help="只看包含原文案例的模板")
    p_search.add_argument("--fulltext", action="store_true", help="在全文（含案例/注意事项）中检索，默认仅检索元数据")
    p_search.add_argument("--limit", "-n", type=int, default=15, help="最多展示条数（默认 15，0 为不限）")
    p_search.set_defaults(func=cmd_search)

    p_get = sub.add_parser("get", help="按唯一 ID（或模板名）精确提取完整模板内容")
    p_get.add_argument("ids", nargs="+", help="模板 ID，如 T01 P05 M12")
    p_get.add_argument("--brief", action="store_true", help="精简模式：仅输出元数据 + 原文案例")
    p_get.set_defaults(func=cmd_get)

    p_list = sub.add_parser("list", help="列出某方向（或全部）模板清单")
    p_list.add_argument("--dir", "-d", help="方向：流量/人设/涨粉/变现 或 T/P/G/M")
    p_list.add_argument("--with-case", action="store_true", help="只看包含原文案例的模板")
    p_list.set_defaults(func=cmd_list)

    p_stats = sub.add_parser("stats", help="查看模板库统计信息")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
