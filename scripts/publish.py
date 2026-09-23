#!/usr/bin/env python3
# GZH-Forge · publish —— 图片转存 + 封面压缩 + 推送草稿箱（只推草稿，绝不直发）
# 无凭证时自动 dry-run；旧管线配置不读取、不修改。
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WECHAT_API = 'https://api.weixin.qq.com'


def load_env(env_path: Path) -> dict:
    cfg = {}
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                cfg[k.strip()] = v.strip()
    return cfg


def main():
    ap = argparse.ArgumentParser(description='GZH-Forge publish: 推送到微信草稿箱')
    ap.add_argument('--html', required=True, help='render 产物（fragment 或 preview 均可）')
    ap.add_argument('--title', required=True)
    ap.add_argument('--account', required=True, help='accounts.json 中的账号 key')
    ap.add_argument('--cover', help='封面图路径（建议 2.35:1，需 ≤64KB）')
    ap.add_argument('--digest', default='', help='摘要，可留空')
    args = ap.parse_args()

    accounts = json.loads((ROOT / 'accounts.json').read_text(encoding='utf-8'))
    if args.account not in accounts:
        print(f'[error] 未知账号: {args.account}，可用: {list(accounts)}', file=sys.stderr)
        sys.exit(1)
    account = accounts[args.account]

    env = {**os.environ}
    env.update(load_env(ROOT / account['wechat_env']))
    appid = env.get('WECHAT_APPID')
    secret = env.get('WECHAT_SECRET')

    content = Path(args.html).read_text(encoding='utf-8')

    if not (appid and secret):
        print(json.dumps({
            'success': True,
            'mode': 'dry-run',
            'account': account['name'],
            'title': args.title,
            'html_bytes': len(content.encode('utf-8')),
            'cover': args.cover or '(未提供，将默认取正文第一张图)',
            'hint': f'未找到 {account["wechat_env"]}，仅本地校验。配置 WECHAT_APPID/WECHAT_SECRET 后重跑即可推草稿箱。',
            'checks': {
                'has_inline_style': 'style="' in content,
                'has_img': '<img' in content,
                'title_ok': bool(args.title.strip()),
            },
        }, ensure_ascii=False, indent=2))
        return

    # ---- 真实发布路径（需要凭证 + IP 白名单） ----
    try:
        import requests
    except ImportError:
        print('[error] 缺少 requests：pip3 install requests', file=sys.stderr)
        sys.exit(1)

    # 1. access_token
    r = requests.get(f'{WECHAT_API}/cgi-bin/token',
                     params={'grant_type': 'client_credential', 'appid': appid, 'secret': secret},
                     timeout=15)
    token = r.json().get('access_token')
    if not token:
        print(f'[error] 获取 token 失败: {r.json()}', file=sys.stderr)
        sys.exit(1)

    # 2. 封面（永久素材 thumb_media_id 是草稿必需字段）
    thumb_media_id = ''
    if args.cover and Path(args.cover).exists():
        size = Path(args.cover).stat().st_size
        if size > 64 * 1024:
            print(f'[warn] 封面 {size/1024:.0f}KB 超过 64KB，建议先压缩', file=sys.stderr)
        with open(args.cover, 'rb') as f:
            up = requests.post(f'{WECHAT_API}/cgi-bin/material/add_material',
                               params={'access_token': token, 'type': 'image'},
                               files={'media': f}, timeout=30)
        thumb_media_id = up.json().get('media_id', '')
        if not thumb_media_id:
            print(f'[warn] 封面上传失败: {up.json()}', file=sys.stderr)

    # 3. 正文图片转存微信图床（外链图必被屏蔽；本地图直接上传）
    import re
    urls = sorted(set(re.findall(r'src="([^"]+)"', content)))
    replaced = 0
    for u in urls:
        if 'mmbiz.qpic.cn' in u:
            continue
        # 本地图片：直接读文件上传
        if not u.startswith('http'):
            local = Path(u) if Path(u).is_absolute() else (ROOT / u)
            if local.exists():
                with open(local, 'rb') as f:
                    up = requests.post(f'{WECHAT_API}/cgi-bin/media/uploadimg',
                                       params={'access_token': token},
                                       files={'media': (local.name, f)}, timeout=30)
                    wx_url = up.json().get('url')
                    if wx_url:
                        content = content.replace(u, wx_url)
                        replaced += 1
                    else:
                        print(f'[warn] 本地图上传失败 {local.name}: {up.json()}', file=sys.stderr)
            else:
                print(f'[warn] 本地图片不存在: {u}', file=sys.stderr)
            continue
        try:
            img_bytes = requests.get(u, timeout=20).content
            up = requests.post(f'{WECHAT_API}/cgi-bin/media/uploadimg',
                               params={'access_token': token},
                               files={'media': ('img.jpg', img_bytes)}, timeout=30)
            wx_url = up.json().get('url')
            if wx_url:
                content = content.replace(u, wx_url)
                replaced += 1
        except Exception as e:
            print(f'[warn] 图片转存失败 {u}: {e}', file=sys.stderr)

    # 4. 推草稿箱（draft/add）
    article = {
        'title': args.title,
        'author': env.get('WECHAT_AUTHOR', account['name']),
        'content': content,
        'digest': args.digest or args.title,
        'need_open_comment': 1,
        'only_fans_can_comment': 0,
    }
    if thumb_media_id:
        article['thumb_media_id'] = thumb_media_id
    r = requests.post(f'{WECHAT_API}/cgi-bin/draft/add',
                      params={'access_token': token},
                      json={'articles': [article]}, timeout=30)
    data = r.json()
    print(json.dumps({
        'success': data.get('errcode') in (0, None),
        'mode': 'publish',
        'account': account['name'],
        'media_id': data.get('media_id', ''),
        'images_migrated': replaced,
        'resp': data,
        'note': '已推送到草稿箱，请人工终审后再群发。绝不直发。',
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
