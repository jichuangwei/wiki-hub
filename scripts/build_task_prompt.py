#!/usr/bin/env python3
"""Generate a cloud prompt that reads the email template through GitHub."""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/reports/ai-agent-frontend-weekly-email.html"
OUTPUT = ROOT / "automation/weekly-report-prompt.txt"


def compact(value: str) -> str:
    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    return re.sub(r">\s+<", "><", value).strip()


def template_fragments() -> dict[str, str]:
    source = TEMPLATE.read_text(encoding="utf-8")
    section_start = source.index("<!-- SECTION 1:")
    item_start = source.index("<!-- BEGIN NEWS ITEM: S1, item 1 -->")
    item_end = source.index("<!-- END NEWS ITEM: S1, item 1 -->")
    section = compact(source[section_start:item_start]).replace("01&nbsp;·&nbsp;AI/大模型", "{{SECTION_LABEL}}")
    item = source[item_start:item_end]
    images_start = item.index("<!-- 配图槽位：")
    images_end = item.index("<p style=", images_start)
    item = item[:images_start] + "{{OPTIONAL_IMAGES}}" + item[images_end:]
    item = re.sub(r"<p[^>]*><strong[^>]*>适用场景 / 理由：</strong>.*?</p>", "{{OPTIONAL_PRODUCT_SCENARIO}}", item)
    item = re.sub(r'<a href="\{\{S1_N1_SOURCE_URL\}\}">.*?</a>', "{{SOURCE_LINKS}}", item)
    item = compact(item).replace("S1_N1_", "")
    tail = source.index("<!-- END NEWS ITEM: S5, item 1 -->")
    shell = compact(source[:section_start] + "{{SECTIONS_HTML}}" + source[tail:])
    scenario = '<p style="margin:0 0 10px;font-size:14px;line-height:23px;color:#607089;"><strong style="color:#17233b;">适用场景 / 理由：</strong>{{PRODUCT_SCENARIO}}</p>'
    images = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;table-layout:fixed;margin:0 0 13px;"><tr>'
    for index, padding in enumerate(("0 4px 0 0", "0 2px", "0 0 0 4px"), 1):
        images += f'<td width="33.33%" valign="top" style="width:33.33%;padding:{padding};">{{{{IMAGE_{index}}}}}</td>'
    images += "</tr></table>"
    image = '<img src="{{IMAGE_URL}}" height="200" alt="{{IMAGE_ALT}}" style="display:block;width:100%;height:200px;object-fit:cover;border:0;">'
    return dict((
        ("邮件主模板", shell), ("栏目模板", section), ("NEWS ITEM 资讯模板", item),
        ("产品适用场景模板", scenario), ("配图模板", images), ("单张图片模板", image),
    ))


def build_prompt() -> str:
    prompt = (ROOT / "automation/weekly-report-instructions.md").read_text(encoding="utf-8")
    if len(prompt) > 20000:
        raise ValueError(f"Cloud task prompt exceeds 20000 characters: {len(prompt)}")
    return prompt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    prompt = build_prompt()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != prompt:
            raise SystemExit("Cloud prompt is stale; run python3 scripts/build_task_prompt.py")
    else:
        OUTPUT.write_text(prompt, encoding="utf-8")
    print(f"{'Checked' if args.check else 'Generated'} {OUTPUT}: {len(prompt)} / 20000 characters")
