#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 GitHub REST API 部署 GZH-Forge（沙箱内 github.com:443 被封，走 api.github.com）"""
import os, sys, json, base64, subprocess, urllib.request, urllib.parse, urllib.error

TOKEN = os.environ["GH_PAT"]
REPO_DIR = "/workspace/gzh-forge"
REPO_NAME = os.environ.get("REPO_NAME", "GZH-Forge")
PRIVATE = os.environ.get("REPO_PRIVATE", "false").lower() == "true"
DESC = "公众号一键锻造 Skill —— 融合 4 家开源排版 Skill 优势的 8-Stage 工作流（写作→排版→中文打磨→配图→推草稿箱）"

API = "https://api.github.com"


def call(method, path, payload=None, ok=(200, 201, 204)):
    url = API + path if path.startswith("/") else path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.github+json",
        "User-Agent": "gzh-forge-deploy",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            return r.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}


def main():
    # 0. 身份
    st, me = call("GET", "/user")
    if st != 200:
        sys.exit(f"身份验证失败: {st} {me}")
    owner = me["login"]
    print(f"[1/5] 身份 OK: {owner}")

    # 1. 建仓（已存在则复用）
    st, repo = call("GET", f"/repos/{owner}/{REPO_NAME}")
    if st == 200:
        print(f"[2/5] 仓库已存在，复用: {repo['html_url']}")
    else:
        st, repo = call("POST", "/user/repos", {
            "name": REPO_NAME,
            "description": DESC,
            "private": PRIVATE,
            "has_issues": True,
            "has_wiki": False,
            "auto_init": False,
        })
        if st not in (200, 201):
            sys.exit(f"建仓失败: {st} {json.dumps(repo, ensure_ascii=False)[:400]}")
        print(f"[2/5] 仓库已创建: {repo['html_url']} (private={PRIVATE})")

    branch = repo.get("default_branch") or "main"

    # 1b. 空仓库需要一次种子提交，Git Data API 才可用
    st, seed = call("GET", f"/repos/{owner}/{REPO_NAME}/contents/.seed")
    if st != 200:
        st, seed = call("PUT", f"/repos/{owner}/{REPO_NAME}/contents/.seed", {
            "message": "chore: initialize repository",
            "content": base64.b64encode(b"GZH-Forge\n").decode(),
            "branch": branch,
        })
        if st not in (200, 201):
            sys.exit(f"种子提交失败: {st} {seed}")
        print(f"[2b/5] 种子提交完成，分支 {branch} 就绪")

    # 2. 收集本地文件
    os.chdir(REPO_DIR)
    files = subprocess.check_output(
        ["git", "-c", "core.quotepath=false", "ls-files"], text=True).split("\n")
    files = [f for f in files if f.strip()]
    print(f"[3/5] 待上传 {len(files)} 个文件")

    # 3. 上传 blob
    tree = []
    total_bytes = 0
    for i, path in enumerate(files, 1):
        raw = open(path, "rb").read()
        total_bytes += len(raw)
        st, blob = call("POST", f"/repos/{owner}/{REPO_NAME}/git/blobs", {
            "content": base64.b64encode(raw).decode(),
            "encoding": "base64",
        })
        if st not in (200, 201):
            sys.exit(f"blob 上传失败 {path}: {st} {blob}")
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print(f"      ({i}/{len(files)}) {path}  {len(raw)//1024}KB")
    print(f"      合计 {total_bytes/1024/1024:.2f} MB")

    # 4. 建 tree + commit
    msg = subprocess.check_output(["git", "log", "-1", "--pretty=%B"], text=True).strip()
    st, t = call("POST", f"/repos/{owner}/{REPO_NAME}/git/trees", {"tree": tree})
    if st not in (200, 201):
        sys.exit(f"tree 失败: {st} {t}")
    st, c = call("POST", f"/repos/{owner}/{REPO_NAME}/git/commits",
                 {"message": msg, "tree": t["sha"], "parents": []})
    if st not in (200, 201):
        sys.exit(f"commit 失败: {st} {c}")
    print(f"[4/5] 提交已创建: {c['sha'][:10]}")

    # 5. 建/更新分支引用
    st, ref = call("GET", f"/repos/{owner}/{REPO_NAME}/git/ref/heads/{branch}")
    if st == 200:
        st, ref = call("PATCH", f"/repos/{owner}/{REPO_NAME}/git/refs/heads/{branch}",
                       {"sha": c["sha"], "force": True})
    else:
        st, ref = call("POST", f"/repos/{owner}/{REPO_NAME}/git/refs",
                       {"ref": f"refs/heads/{branch}", "sha": c["sha"]})
    if st not in (200, 201):
        sys.exit(f"分支引用失败: {st} {ref}")
    print(f"[5/5] 分支 {branch} 已指向 {c['sha'][:10]}")

    # 收尾：默认分支 + topics
    call("PATCH", f"/repos/{owner}/{REPO_NAME}", {"default_branch": branch})
    call("PUT", f"/repos/{owner}/{REPO_NAME}/topics",
         {"names": ["wechat", "mp-wechat", "markdown", "typesetting", "skill", "ai-agent", "wechat-official-account"]})

    st, final = call("GET", f"/repos/{owner}/{REPO_NAME}")
    print("\n=== 部署完成 ===")
    print("仓库地址:", final.get("html_url"))
    print("文件数:", len(files))
    print("大小:", f"{total_bytes/1024/1024:.2f} MB")
    print("可见性:", "Private" if final.get("private") else "Public")


if __name__ == "__main__":
    main()
