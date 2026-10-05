"""Prepare a historical issue for a template compatibility test; preserve the archive."""
import argparse
import re
from pathlib import Path
try:
    from .build_site import ROOT, parse_issue, render_mail_body
except ImportError:
    from build_site import ROOT, parse_issue, render_mail_body


def render_email(source: Path) -> str:
    issue = parse_issue(source)
    body = render_mail_body(source.read_text(encoding='utf-8'), issue.categories)
    template = (ROOT / 'templates/news/ai-agent-frontend-weekly-email.html').read_text(encoding='utf-8')
    head = template.split('<body', 1)[0]
    head = re.sub(r'<title>.*?</title>', '<title>AI 资讯干货｜第 %s 周</title>' % issue.start.isocalendar().week, head)
    for old, new in {'#f6f8fc':'#fafafa', '#17233b':'#171b24', '#2456cd':'#3662f4', '#607089':'#424a57', '#394a64':'#424a57', '#8090a6':'#79818f', '#cbd5e1':'#d9dde5', '#dde5f0':'#d9dde5'}.items():
        body = body.replace(old,new)
    body = body.replace('font-size:34px;line-height:1.2;', 'font-size:42px;line-height:1.2;text-align:center;')
    body = body.replace('font-size:13px;line-height:20px;font-weight:700;letter-spacing:.5px;', 'font-size:14px;line-height:22px;font-weight:400;text-align:center;')
    body = body.replace('font-size:19px;line-height:28px;font-weight:800;letter-spacing:.3px;', 'font-size:26px;line-height:36px;font-weight:800;letter-spacing:.3px;')
    body = body.replace('font-size:18px;line-height:26px;color:#171b24;', 'font-size:22px;line-height:33px;color:#171b24;')
    body = body.replace('border-radius:8px;', 'border-radius:4px;')
    return head + '<body style="margin:0;padding:0;background-color:#fafafa;" class="mail-bg mail-ink">' + body + '</body></html>\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.resolve() == args.input.resolve():
        parser.error('Output must not overwrite the historical archive')
    args.output.write_text(render_email(args.input), encoding='utf-8')
    print('Prepared test email:', args.output)
