#!/usr/bin/env python3
# GZH-Forge · render —— Markdown → 微信公众号内联样式 HTML
# 能力来源：gzh-design-skill 的全内联样式思路 + xiaohu 的中文打磨 + md2wechat 的 CLI 风格
import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------- 中文打磨（来自 xiaohu-wechat-format 的能力） ----------

def polish_text(text: str) -> str:
    # 1. 中英文之间补空格（lookahead 不会重复加）
    text = re.sub(r'(?<=[\u4e00-\u9fff])(?=[A-Za-z0-9])', ' ', text)
    text = re.sub(r'(?<=[A-Za-z0-9])(?=[\u4e00-\u9fff])', ' ', text)
    # 2. 中文语境中的半角标点转全角
    text = re.sub(r'(?<=[\u4e00-\u9fff]),(?=[\u4e00-\u9fff])', '，', text)
    text = re.sub(r'(?<=[\u4e00-\u9fff]);(?=[\u4e00-\u9fff])', '；', text)
    text = re.sub(r'(?<=[\u4e00-\u9fff]):(?=[\u4e00-\u9fff])', '：', text)
    text = re.sub(r'(?<=[\u4e00-\u9fff])\?(?=[\u4e00-\u9fff])', '？', text)
    text = re.sub(r'(?<=[\u4e00-\u9fff])!(?=[\u4e00-\u9fff])', '！', text)
    # 3. 行尾多余空格
    text = re.sub(r'[ \t]+$', '', text, flags=re.M)
    return text


def polish_preserve_code(text: str) -> str:
    """对代码块外的内容做打磨，代码块内保持原样。"""
    parts = re.split(r'(```.*?```)', text, flags=re.S)
    out = []
    for i, part in enumerate(parts):
        out.append(part if part.startswith('```') else polish_text(part))
    return ''.join(out)


# ---------- 行内渲染 ----------

def inline_md(src: str, theme: dict, footnotes: list) -> str:
    s = html.escape(src)

    def img_repl(m):
        alt, url = m.group(1), m.group(2)
        return f'<img src="{url}" alt="{html.escape(alt)}" style="{theme["img"]}">'

    def link_repl(m):
        text, url = m.group(1), m.group(2)
        if url.startswith('http'):
            footnotes.append((text, url))
            n = len(footnotes)
            return f'{text}<sup style="{theme["footnoteSup"]}">[{n}]</sup>'
        return f'<span style="{theme["link"]}">{text}</span>'

    s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)', img_repl, s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link_repl, s)
    s = re.sub(r'\*\*([^*]+)\*\*',
               lambda m: f'<strong style="{theme["strong"]}">{m.group(1)}</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)',
               lambda m: f'<em style="{theme["em"]}">{m.group(1)}</em>', s)
    s = re.sub(r'`([^`\n]+)`',
               lambda m: f'<code style="{theme["inlineCode"]}">{m.group(1)}</code>', s)
    return s


# ---------- 块级渲染 ----------

def render(md_text: str, theme: dict):
    footnotes = []
    lines = md_text.split('\n')
    out = []
    list_buf = None  # (tag, items)
    in_code = False
    code_buf = []
    code_lang = ''

    def flush_list():
        nonlocal list_buf
        if list_buf:
            tag, items = list_buf
            lis = ''.join(f'<li style="{theme["li"]}">{it}</li>' for it in items)
            out.append(f'<{tag} style="{theme[tag]}">{lis}</{tag}>')
            list_buf = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('```'):
            flush_list()
            if not in_code:
                in_code, code_buf, code_lang = True, [], stripped[3:].strip()
            else:
                in_code = False
                code = '\n'.join(code_buf)
                out.append(
                    f'<pre style="{theme["codeBlock"]}"><code>{html.escape(code)}</code></pre>')
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if not stripped:
            flush_list()
            i += 1
            continue

        if stripped.startswith('#'):
            flush_list()
            level = len(stripped) - len(stripped.lstrip('#'))
            text = stripped.lstrip('#').strip()
            if level <= 1:
                out.append(f'<h1 style="{theme["h1"]}">{inline_md(text, theme, footnotes)}</h1>')
            elif level == 2:
                out.append(f'<h2 style="{theme["h2"]}">{inline_md(text, theme, footnotes)}</h2>')
            else:
                out.append(f'<h3 style="{theme["h3"]}">{inline_md(text, theme, footnotes)}</h3>')
        elif stripped.startswith('>'):
            flush_list()
            text = stripped.lstrip('> ').strip()
            out.append(f'<blockquote style="{theme["blockquote"]}">{inline_md(text, theme, footnotes)}</blockquote>')
        elif re.match(r'^[-*+] ', stripped):
            if not list_buf or list_buf[0] != 'ul':
                flush_list()
                list_buf = ['ul', []]
            list_buf[1].append(inline_md(stripped[2:].strip(), theme, footnotes))
        elif re.match(r'^\d+[.、]\s*', stripped):
            if not list_buf or list_buf[0] != 'ol':
                flush_list()
                list_buf = ['ol', []]
            m = re.match(r'^\d+[.、]\s*(.*)$', stripped)
            list_buf[1].append(inline_md(m.group(1), theme, footnotes))
        elif stripped in ('---', '***', '___'):
            flush_list()
            out.append(f'<hr style="{theme["hr"]}"/>')
        else:
            flush_list()
            out.append(f'<p style="{theme["p"]}">{inline_md(stripped, theme, footnotes)}</p>')
        i += 1

    flush_list()

    if footnotes:
        items = ''.join(
            f'<p style="{theme["footnoteItem"]}">[{n}] {t}：{html.escape(u)}</p>'
            for n, (t, u) in enumerate(footnotes, 1))
        out.append(
            f'<section style="{theme["footnoteBox"]}">'
            f'<p style="{theme["footnoteItem"]};color:#666;"><strong>参考链接（公众号内无法点击，请复制到浏览器打开）</strong></p>'
            f'{items}</section>')

    body = '\n'.join(out)
    return f'<section id="gzh-forge-article" style="{theme["section"]}">\n{body}\n</section>'


# ---------- 预览页（一键复制，来自 gzh-design-skill 的思路） ----------

PREVIEW_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ · GZH-Forge 预览</title>
<style>
  body {{ margin:0; background:#f2f3f5; font-family:-apple-system,'PingFang SC',sans-serif; }}
  .bar {{ position:sticky; top:0; z-index:9; background:#181b24; color:#fff; padding:10px 16px;
         display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
  .bar b {{ font-size:14px; }}
  .bar .meta {{ font-size:12px; color:#8a93a6; }}
  .btn {{ background:#ff7849; color:#fff; border:none; border-radius:6px; padding:8px 18px;
         font-size:14px; cursor:pointer; }}
  .btn.ok {{ background:#4caf50; }}
  .stage {{ max-width:414px; margin:24px auto; background:#fff; border-radius:12px;
           box-shadow:0 2px 12px rgba(0,0,0,.08); overflow:hidden; }}
  .foot {{ text-align:center; color:#9aa; font-size:12px; padding:16px; }}
</style>
</head>
<body>
<div class="bar">
  <b>GZH-Forge</b>
  <span class="meta">__THEME_NAME__ · 手机宽度预览</span>
  <button class="btn" id="copyBtn">一键复制到公众号</button>
</div>
<div class="stage">
__ARTICLE__
</div>
<div class="foot">复制后到公众号编辑器 ⌘/Ctrl+V 粘贴 · 样式全内联，不会掉格式</div>
<script>
const btn = document.getElementById('copyBtn');
btn.onclick = async () => {
  const stage = document.querySelector('.stage');
  try {
    const item = new ClipboardItem({
      'text/html': new Blob([stage.innerHTML], {{type: 'text/html'}}),
      'text/plain': new Blob([stage.innerText], {{type: 'text/plain'}})
    });
    await navigator.clipboard.write([item]);
    btn.textContent = '已复制，去公众号粘贴吧'; btn.classList.add('ok');
  } catch (e) {
    const range = document.createRange(); range.selectNodeContents(stage);
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(range);
    document.execCommand('copy'); sel.removeAllRanges();
    btn.textContent = '已复制（兼容模式）'; btn.classList.add('ok');
  }
  setTimeout(() => {{ btn.textContent = '一键复制到公众号'; btn.classList.remove('ok'); }}, 3000);
};
</script>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser(description='GZH-Forge render: Markdown → 微信内联样式 HTML')
    ap.add_argument('--md', required=True, help='Markdown 文件路径')
    ap.add_argument('--theme', required=True, help='主题名（themes/ 目录下）或 JSON 路径')
    ap.add_argument('--out', required=True, help='输出预览 HTML 路径')
    ap.add_argument('--title', default='未命名', help='文章标题')
    ap.add_argument('--no-polish', action='store_true', help='跳过中文打磨')
    args = ap.parse_args()

    theme_path = Path(args.theme)
    if not theme_path.exists():
        theme_path = ROOT / 'themes' / f'{args.theme}.json'
    if not theme_path.exists():
        print(f'[error] 主题不存在: {args.theme}', file=sys.stderr)
        sys.exit(1)
    theme = json.loads(theme_path.read_text(encoding='utf-8'))

    md_text = Path(args.md).read_text(encoding='utf-8')
    if not args.no_polish:
        md_text = polish_preserve_code(md_text)

    article = render(md_text, theme)
    page = (PREVIEW_TMPL
            .replace('__TITLE__', html.escape(args.title))
            .replace('__THEME_NAME__', html.escape(theme.get('name', args.theme)))
            .replace('__ARTICLE__', article))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding='utf-8')

    frag_path = out_path.with_name(out_path.stem + '.fragment.html')
    frag_path.write_text(article, encoding='utf-8')

    print(json.dumps({
        'success': True,
        'preview': str(out_path),
        'fragment': str(frag_path),
        'theme': theme.get('name', args.theme),
        'polish': not args.no_polish,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
