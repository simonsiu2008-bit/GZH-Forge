# GZH-Forge 🔥

> 公众号一键锻造 Skill —— 你只说一句“给 XX 号跑一版”，剩下交给 Forge。
>
> 整合 WeWrite / xiaohu-wechat-format / md2wechat / gzh-design-skill 四家开源 Skill 的优势，
> 锻造出一条从写作到草稿箱的端到端流水线。

## 它融合了什么

| 来源 Skill | 吸收的优势 |
|---|---|
| WeWrite | 全流程编排 + **一键推草稿箱**（自动转存微信图床、封面压缩） |
| xiaohu-wechat-format | **中文排版打磨**（中英文自动补空格、半角标点转全角、外链转脚注） |
| md2wechat | Agent 友好的**内容排版语言**与 block 化思路 |
| gzh-design-skill | **主题化 design system**（人格 × 主题耦合调参） |

## 8-Stage 流水线

```
选题 → 内容理解 → 写作/润色 → 排版设计 → 中文打磨 → 视觉生成 → 推草稿箱 → 数据复盘
```

MVP 已实现核心 4 站（写作 → 排版 → 打磨 → 草稿箱），选题/视觉/复盘为扩展位。

## 快速开始

```bash
# 1. 排版（自带中文打磨 + 外链转脚注，内联样式粘贴公众号不掉格式）
python3 scripts/render.py --md article.md --theme crossborder --out preview.html --title "标题"

# 2. 推草稿箱（无凭证自动 dry-run，只做本地检查）
python3 scripts/publish.py --html preview.fragment.html --title "标题" \
    --account crossborder --cover cover.jpg
```

依赖：Python 3.10+、`requests`、`Pillow`（仅发布环节需要）。

## 账号档案（多号运营）

`accounts.json` 为每个公众号建档：**主题 × 写作人格 × 内容框架** 三位一体。

| 账号 | 主题 | 写作人格 | 框架 |
|---|---|---|---|
| crossborder 跨境号 | 跨境蓝（专业电商风） | industry-observer | 深度分析 |
| photography 拍照号 | 留白禅意（衬线大留白） | warm-editor | 清单 / 教程 |

新增账号：在 `accounts.json` 加档案 + 在 `themes/` 加一份主题 JSON 即可。

## 微信凭证配置

每个账号一个 env 文件（路径见 `accounts.json` 的 `wechat_env` 字段）：

```bash
mkdir -p envs
cat > envs/crossborder.env <<'EOF'
WECHAT_APPID=wx_xxx
WECHAT_SECRET=xxx
EOF
```

> 注意：公网 IP 需加入公众号后台 IP 白名单，否则接口报 40164。

## 安全边界（重要）

- **只推草稿箱，绝不直发**，发布前必须人工终审
- 无凭证时 publish 自动降级为 dry-run，不静默失败
- `envs/` 已被 .gitignore 排除，凭证永不入库
- 与既有旧管线完全隔离：不读取、不修改、不接管任何旧配置与产物

## 目录结构

```
gzh-forge/
├── SKILL.md            # Skill 使用说明（给 Agent 读的入口）
├── accounts.json       # 多账号档案（主题 × 人格 × 框架）
├── themes/             # 排版主题库（JSON）
├── scripts/
│   ├── render.py       # Markdown → 微信内联样式 HTML + 中文打磨
│   └── publish.py      # 图床转存 + 封面压缩 + 推草稿箱
├── samples/            # 示例稿件
├── demo/               # 渲染效果预览
├── assets/             # 示例配图
└── tools/
    └── deploy_github.py # 通过 GitHub REST API 部署/更新本仓库
```

## 部署 / 更新到 GitHub

`tools/deploy_github.py` 走 GitHub REST API 推送（不依赖 `git push`，适用于
`github.com:443` 被网络策略拦截的环境）：

```bash
export GH_PAT=github_pat_xxx   # Fine-grained Token，需 Contents: Read and write
python3 tools/deploy_github.py  # 自动建仓（或复用）+ 上传全部文件 + 建提交
```

可选环境变量：`REPO_NAME`（默认 `GZH-Forge`）、`REPO_PRIVATE`（默认 `false`）。

> **网络排障提示**：若沙箱内 `github.com` 解析异常但 `api.github.com` 可通，
> 说明是 DNS 被污染 —— 在 hosts 里把域名指到 GitHub 真实 IP 即可绕过。

## License

MIT
