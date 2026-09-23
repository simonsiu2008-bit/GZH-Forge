# GZH-Forge · 公众号一键锻造 Skill（MVP）

> 整合 WeWrite / xiaohu-wechat-format / md2wechat / gzh-design-skill 四家优势的端到端流水线。
> 你只说一句"给 XX 号跑一版"，剩下交给 Forge。

## 管线（8 Stage）

1. `topic` 热点选题（可选，P1）
2. `understand` 内容理解 → 匹配账号主题（本 MVP 通过 accounts.json 的 content_type 预置）
3. `write` 写作/润色（写作人格 + 框架由 Agent 按账号档案执行）
4. `design` 排版（`scripts/render.py`，主题内联样式，粘贴公众号不掉格式）
5. `polish` 中文打磨（中英文间距、半角标点转全角、外链转脚注，已内置于 render）
6. `visual` 视觉生成（封面，P1，可用外部生成后传 `--cover`）
7. `publish` 推草稿箱（`scripts/publish.py`，需账号 env；无凭证时自动 dry-run）
8. `feedback` 数据复盘（P2，发布后人工回填）

## 快速开始

```bash
# 排版（自动做中文打磨 + 外链转脚注）
python3 scripts/render.py --md article.md --theme crossborder --out preview.html --title "标题"

# 推草稿箱（需先配 env，见 accounts.json 每个账号的 wechat_env 字段）
python3 scripts/publish.py --html preview.html --title "标题" --account crossborder --cover cover.jpg
```

## 账号档案

见 `accounts.json`：

| 账号 | 主题 | 写作人格 | 框架 |
|---|---|---|---|
| crossborder 跨境号 | 跨境蓝（专业电商风） | industry-observer | 深度分析 |
| photography 拍照号 | 留白禅意（衬线大留白） | warm-editor | 清单/教程 |

## 边界约定（重要）

- **旧管线（WeWrite / md2wechat / 既有脚本等）保持独立运行**：本 Skill 不读取、不修改、不接管任何旧版本配置与产物，两套并行，互不影响。
- 只推**草稿箱**，绝不直发；发布前必须留人工终审。
- 无微信凭证时 publish 自动降级为 dry-run，只做本地检查。

## 微信凭证配置

每个账号一个 env 文件（如 `envs/crossborder.env`）：

```
WECHAT_APPID=wx_xxx
WECHAT_SECRET=xxx
```

另注意：公网 IP 需加入公众号后台 IP 白名单，否则报 40164。
