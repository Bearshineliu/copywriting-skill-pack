#!/usr/bin/env python3
"""
说唱 / Rap 口播字数与节奏核对工具（零第三方依赖）
配合 references/rap-conversion-guide.md 使用。

用法示例:
  python3 scripts/count_rap.py rap_draft.txt --target 60
  python3 scripts/count_rap.py --text "【HOOK｜0–8s】\n这波海克斯真强 // 拿完直接起飞光" --target 30
  cat rap_draft.txt | python3 scripts/count_rap.py --target 45
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RE_SECTION_HEADER = re.compile(r"^\s*【[^】]+】\s*$")
RE_CJK = re.compile(r"[\u4e00-\u9fff]")
RE_ALNUM = re.compile(r"[A-Za-z0-9]+")


def count_syllables(text: str) -> tuple[int, int]:
    """返回 (纯汉字数, 汉字+数字/英文词块估算音节数)。"""
    cjk = len(RE_CJK.findall(text))
    alnum = len(RE_ALNUM.findall(text))
    return cjk, cjk + alnum


def analyze(content: str, target_sec: int):
    total_cjk = 0
    total_units = 0
    warnings = []
    line_stats = []

    for lineno, raw_line in enumerate(content.splitlines(), 1):
        line = raw_line.strip()
        if not line or RE_SECTION_HEADER.match(line) or line.startswith("#") or line.startswith(">"):
            continue
        # 按 // 切分拍句
        segments = [seg.strip() for seg in line.split("//") if seg.strip()]
        for seg in segments:
            # 去掉行内括号注释（如 (重复)）
            clean_seg = re.sub(r"[（(][^）)]*[）)]", "", seg)
            cjk, units = count_syllables(clean_seg)
            if units == 0:
                continue
            total_cjk += cjk
            total_units += units
            line_stats.append((lineno, seg, cjk, units))
            if units < 5 or units > 9:
                warnings.append(f"  - 第 {lineno} 行「{seg}」：{cjk} 汉字（约 {units} 拍，建议每句 6–8 字）")

    sec_slow = total_units / 5.0
    sec_fast = total_units / 5.5
    with_buffer_low = sec_fast + 8
    with_buffer_high = sec_slow + 10

    target_chars = max(0, (target_sec - 10) * 5)
    print(f"纯汉字数：{total_cjk} 字（含数字/英文按音节计约 {total_units} 字）")
    print(f"歌词净时长（按 5.0–5.5 字/秒）：{sec_fast:.1f}s – {sec_slow:.1f}s")
    print(f"加上过门/留白（8–10s）：{with_buffer_low:.1f}s – {with_buffer_high:.1f}s")
    print(f"目标时长：{target_sec}s（推荐歌词字数约 {target_chars} 字）")

    if with_buffer_low > target_sec + 3:
        print(f"⚠️  字数偏多：建议删减约 {int(total_units - target_chars)} 字信息点，不要靠加速硬塞。")
    elif with_buffer_high < target_sec - 5:
        print(f"ℹ️  时长偏短：可用 Hook 重复一遍补满 {target_sec}s，不要注水内容。")
    else:
        print("✅ 字数与目标时长匹配良好。")

    if warnings:
        print(f"\n切句长度提醒（共 {len(warnings)} 句超出 5–9 字舒适区间）：")
        for w in warnings[:15]:
            print(w)
        if len(warnings) > 15:
            print(f"  ...（其余 {len(warnings) - 15} 句已省略）")
    else:
        print("\n✅ 所有切句长度均在舒适节奏区间内。")


def main():
    parser = argparse.ArgumentParser(description="说唱 / Rap 口播字数与节奏核对工具")
    parser.add_argument("file", nargs="?", help="说唱稿文件路径（留空则读取 --text 或 stdin）")
    parser.add_argument("--text", "-t", help="直接传入说唱稿文本")
    parser.add_argument("--target", "-s", type=int, default=60, help="目标视频时长（秒，默认 60）")
    args = parser.parse_args()

    if args.text:
        content = args.text.replace("\\n", "\n")
    elif args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    analyze(content, args.target)


if __name__ == "__main__":
    main()
