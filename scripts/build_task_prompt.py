#!/usr/bin/env python3
"""Generate the cloud task launcher for the repository skill."""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/news/ai-agent-frontend-weekly-email.html"
SKILL = ROOT / "skills/ai-agent-frontend-weekly/SKILL.md"
OUTPUT = ROOT / "skills/ai-agent-frontend-weekly/cloud-task-prompt.txt"


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
    scenario = '<p class="mail-muted" style="margin:0 0 10px;font-size:14px;line-height:23px;color:#607089;"><strong class="mail-ink" style="color:#17233b;">适用场景 / 理由：</strong>{{PRODUCT_SCENARIO}}</p>'
    images = '<div style="width:100%;font-size:0;line-height:0;margin:0 0 13px;">'
    for index, padding in enumerate(("0 4px 4px 0", "0 0 4px 4px"), 1):
        images += f'<div class="image-slot" style="display:inline-block;vertical-align:top;width:50%;min-width:180px;max-width:420px;"><div style="padding:{padding};">{{{{IMAGE_{index}}}}}</div></div>'
    images += "</div>"
    image = '<img src="{{IMAGE_URL}}" height="200" alt="{{IMAGE_ALT}}" style="display:block;width:100%;max-width:420px;height:200px;object-fit:cover;border:0;">'
    return dict((
        ("邮件主模板", shell), ("栏目模板", section), ("NEWS ITEM 资讯模板", item),
        ("产品适用场景模板", scenario), ("配图模板", images), ("单张图片模板", image),
    ))


def build_prompt() -> str:
    prompt = f"""每周一 09:00（Asia/Shanghai）制作上一完整自然周（周一至周日）的 AI × Agent × 前端周报：沿用模板固定五类，每类 2–4 条，共 10–20 条；重点资讯的深入分析放在对应资讯内，不追加独立深度栏目。测试指定周次时使用指定日期，不改正式任务定时设置。

开始前，通过已连接的 GitHub 读取 jichuangwei/wiki-hub 的 main 分支中 {SKILL.relative_to(ROOT)} 的完整内容，并按该 skill 执行；再读取 {TEMPLATE.relative_to(ROOT)} 的完整 HTML，记录模板 blob SHA。仓库中的 skill 和模板是本次运行的规则与排版源，不使用旧缓存或记忆代替。任一文件读取失败，停止发布和发信并说明原因。

发布、线上核验和 HTML 邮件发送均遵守 skill。邮件服务为 Gmail，仅使用独立 BCC 字段，To 和 CC 留空。BCC 收件人只从此云任务的私有配置获取，不从仓库、周报正文或历史邮件猜测；缺少明确私有收件配置时，可完成发布，但不得发送邮件，并报告原因。不要将收件地址写入仓库、HTML、发布参数或公开结果。

发布前必须确认当前任务可调用 get_publication_by_week、publish_weekly_report 和 get_publication_status。先按周查询现有记录，再按 skill 选择复用、首次发布或经用户明确批准的修订；不能因同周冲突而普通重试或覆盖。

本提示词不包含私有收件地址。更新云任务时，在任务的私有配置中保留或填写 BCC 收件人；仓库文件的变动不会自动更新云任务提示词或连接。
"""
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
