#!/usr/bin/env python3
"""开源发布检查：看一个仓库能不能让用户「装一次、自动更新」，顺便查开源前的基本功。
只用 Python 自带库，只读不改。

用法：python3 check_repo.py <仓库目录> [--base origin/main] [--json]
输出：每项一行 ✅ / ❌ / ⚠️ / ℹ️，最后一行 STATUS=PASS / WARN / FAIL。有 ❌ 时退出码为 1。
"""
import argparse, glob, json, os, re, subprocess, sys

R = []  # (level, id, text, fix)


def add(level, cid, text, fix=""):
    R.append((level, cid, text, fix))


def rd(p):
    try:
        return open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""


def lj(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def git(root, *a):
    try:
        r = subprocess.run(["git", "-C", root, *a], capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def tracked(root):
    out = git(root, "ls-files")
    if out is not None:
        return [l for l in out.splitlines() if l]
    res = []
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in (".git", "node_modules", ".venv", "dist", "build")]
        res += [os.path.relpath(os.path.join(d, f), root) for f in fs]
    return res


def workflows(root):
    return "\n".join(rd(p) for p in glob.glob(os.path.join(root, ".github/workflows/*.y*ml")))


# ---------- 判断仓库是什么 ----------
def detect(root, files):
    t = []
    if os.path.exists(os.path.join(root, ".claude-plugin/marketplace.json")) or \
       glob.glob(os.path.join(root, "plugins/*/.claude-plugin/plugin.json")) or \
       any(f.endswith("SKILL.md") for f in files):
        t.append("plugin")
    pj = lj(os.path.join(root, "package.json"))
    if pj and not pj.get("private"):
        t.append("node")
    if os.path.exists(os.path.join(root, "pyproject.toml")) or os.path.exists(os.path.join(root, "setup.py")):
        t.append("python")
    mf = lj(os.path.join(root, "manifest.json"))
    if mf and "manifest_version" in mf:
        t.append("browser-ext")
    if any(f.endswith(".xcodeproj/project.pbxproj") for f in files):
        t.append("mac-app")
    if glob.glob(os.path.join(root, "Formula/*.rb")) or glob.glob(os.path.join(root, "Casks/*.rb")):
        t.append("homebrew-tap")
    if "plugin" not in t and (os.path.exists(os.path.join(root, "index.html")) or
                              any(os.path.exists(os.path.join(root, x)) for x in
                                  ("vercel.json", "netlify.toml", "CNAME", "vite.config.js", "vite.config.ts",
                                   "next.config.js", "next.config.mjs"))):
        t.append("web")
    return t or ["scripts"]


# ---------- 插件 / skill：自动更新 ----------
def check_plugin(root, base, files):
    mk_c = os.path.join(root, ".claude-plugin/marketplace.json")
    mk_x = os.path.join(root, ".agents/plugins/marketplace.json")
    m = lj(mk_c)
    if not m:
        if any(f.endswith("SKILL.md") for f in files):
            add("FAIL", "P1", "有 SKILL.md，但没有插件市场清单 .claude-plugin/marketplace.json：用户只能手动复制，永远不会自动更新",
                "照 references/plugin-layout.md 把仓库改成插件市场结构")
        else:
            add("FAIL", "P1", ".claude-plugin/marketplace.json 读不出来（不存在或不是合法 JSON）", "修好这个文件")
        return
    plugins = m.get("plugins") or []
    if not plugins:
        add("FAIL", "P1", "marketplace.json 里 plugins 是空的", "把插件写进 plugins 列表")
        return
    add("PASS", "P1", f"Claude 插件市场清单在，里面有 {len(plugins)} 个插件：" + "、".join(p.get('name', '?') for p in plugins))
    codex_ok = os.path.exists(mk_x)
    if not codex_ok:
        add("WARN", "P1", "没有 Codex 的插件市场清单 .agents/plugins/marketplace.json：Codex 用户装不了、也收不到更新",
            "照 references/plugin-layout.md 补上 Codex 两个文件")

    for e in plugins:
        name = e.get("name", "?")
        src = e.get("source")
        src = src.get("path") if isinstance(src, dict) else src
        pdir = os.path.normpath(os.path.join(root, src or f"plugins/{name}"))
        cp = lj(os.path.join(pdir, ".claude-plugin/plugin.json"))
        xp = lj(os.path.join(pdir, ".codex-plugin/plugin.json"))
        if not cp:
            add("FAIL", "P1", f"[{name}] 缺 {os.path.relpath(pdir, root)}/.claude-plugin/plugin.json", "补上，写 name 和 version")
            continue
        skills = glob.glob(os.path.join(pdir, "skills/*/SKILL.md"))
        if not skills:
            add("FAIL", "P1", f"[{name}] skills/<名字>/SKILL.md 一个都没有，Claude 找不到 skill", "SKILL.md 必须放在插件目录的 skills/<名字>/ 下")
        if codex_ok and not xp:
            add("WARN", "P1", f"[{name}] 缺 .codex-plugin/plugin.json", "补上，version 和 Claude 那份一样")

        # P2 版本号在不在、一不一致
        vers = {"plugin.json": cp.get("version")}
        if "version" in e:
            vers["marketplace.json"] = e.get("version")
        if xp:
            vers["codex plugin.json"] = xp.get("version")
        if not cp.get("version"):
            add("FAIL", "P2", f"[{name}] plugin.json 没写 version：每次提交都会被当成新版本，或者根本不更新，不可控",
                "写上 \"version\": \"1.0.0\"")
        elif len(set(vers.values())) > 1:
            add("FAIL", "P2", f"[{name}] 几处版本号不一致：" + "，".join(f"{k}={v}" for k, v in vers.items()) +
                "（plugin.json 优先，别处写旧号会让人误判）", "跑 python3 tools/bump.py <版本号> 一次改齐")
        else:
            add("PASS", "P2", f"[{name}] 版本号 {cp.get('version')}，各处一致")

        # P3 改了内容有没有涨版本
        if base:
            rel = os.path.relpath(pdir, root)
            changed = git(root, "diff", "--name-only", f"{base}...HEAD", "--", rel)
            if changed is None:
                add("INFO", "P3", f"[{name}] 没法和 {base} 比较（分支不存在或浅克隆），跳过「改了有没有涨版本」", "先 git fetch")
            else:
                content = [c for c in changed.splitlines() if c and "plugin.json" not in c]
                old = git(root, "show", f"{base}:{rel}/.claude-plugin/plugin.json")
                oldv = None
                try:
                    oldv = json.loads(old).get("version") if old else None
                except Exception:
                    pass
                if content and oldv == cp.get("version"):
                    add("FAIL", "P3", f"[{name}] 相比 {base} 改了 {len(content)} 个文件，版本号还是 {oldv}：合并后用户收不到这次更新",
                        "跑 python3 tools/bump.py（不写版本号就最后一位 +1）")
                elif content:
                    add("PASS", "P3", f"[{name}] 改了内容，版本号已从 {oldv} 涨到 {cp.get('version')}")
                else:
                    add("PASS", "P3", f"[{name}] 相比 {base} 没改插件内容")

    # P4 README 安装方式
    readme = rd(os.path.join(root, "README.md")) + rd(os.path.join(root, "README_EN.md"))
    if not readme:
        add("FAIL", "P4", "没有 README.md", "写一个，安装方式放最前面")
    else:
        if not re.search(r"marketplace|插件市场|Add marketplace", readme, re.I):
            add("FAIL", "P4", "README 没写插件市场的装法：用户会手动复制，收不到更新", "首推 marketplace 装法，模板见 references/readme-install.md")
        else:
            add("PASS", "P4", "README 写了插件市场装法")
        manual = re.search(r"\.claude/skills/|\.codex/skills/|解压后|手动复制|下载 ?zip", readme, re.I)
        if manual and not re.search(r"不会自动更新|won'?t auto-?update|no auto-?update", readme, re.I):
            add("WARN", "P4", "README 有手动复制/下载 zip 的装法，但没提醒「这样装不会自动更新」", "在那段旁边加一句提醒")
        cc_note = True
        for mm in re.finditer(r"/plugin install|claude plugin install|codex plugin add", readme):
            near = readme[max(0, mm.start() - 300): mm.end() + 400]
            if not re.search(r"Enable auto-?update|autoUpdate|打开自动更新|开启自动更新", near, re.I):
                cc_note = False
        if not cc_note:
            add("WARN", "P4", "README 的 Claude Code / Codex 命令行装法旁边，没教用户打开自动更新（Claude Code 第三方插件市场默认不自动更新）",
                "在那段下面加一句：/plugin → Marketplaces → 选中这个市场 → Enable auto-update")

    # P5 开工前查新版本
    allsrc = "\n".join(rd(os.path.join(root, f)) for f in files if f.endswith((".py", ".sh", ".mjs", ".js", "SKILL.md"))
                       and os.path.getsize(os.path.join(root, f)) < 400000)
    if re.search(r"raw\.githubusercontent\.com/.+plugin\.json|update_check", allsrc):
        add("PASS", "P5", "skill 开工前会自己查新版本（兜底层）")
    else:
        add("WARN", "P5", "skill 开工前不会自己查新版本：用户没开自动更新时就一直用旧版",
            "复制 assets/update_check.py 进 skill 的 scripts/，SKILL.md 第 0 步加一行调用")

    # P6 一键改版本号
    if os.path.exists(os.path.join(root, "tools/bump.py")):
        if re.search(r"plugins/[A-Za-z0-9_-]+/\.claude-plugin", rd(os.path.join(root, "tools/bump.py"))):
            add("WARN", "P6", "tools/bump.py 里写死了某个插件名：加第二个插件或复制到别的仓库就不能直接用", "换成 assets/bump.py（自动找所有插件）")
        else:
            add("PASS", "P6", "有 tools/bump.py 一键改版本号")
    else:
        add("WARN", "P6", "没有一键改版本号的工具，几处版本号容易改漏", "复制 assets/bump.py 到 tools/bump.py")

    # P7 CI 拦截忘涨版本
    if "check_version_bump" in workflows(root):
        add("PASS", "P7", "GitHub 上有自动检查：改了内容没涨版本号会被拦下")
    else:
        add("WARN", "P7", "没有 GitHub 自动检查，忘了涨版本号也能合并", "复制 assets/version-check.yml 和 assets/check_version_bump.py")


# ---------- 其他类型：有没有自动发货渠道 ----------
def check_channel(root, t):
    wf = workflows(root)
    if t == "node":
        ok = re.search(r"npm publish|changesets/action|semantic-release", wf)
        add("PASS" if ok else "WARN", "C1", "npm 包：" + ("有自动发布到 npm 的流程" if ok else "没配自动发布到 npm，用户 npm 更新拿不到新版"),
            "" if ok else "见 references/channels.md 的 Node 一节")
    elif t == "python":
        ok = re.search(r"pypa/gh-action-pypi-publish|twine upload|uv publish|poetry publish", wf)
        add("PASS" if ok else "WARN", "C1", "Python 包：" + ("有自动发布到 PyPI 的流程" if ok else "没配自动发布到 PyPI"),
            "" if ok else "见 references/channels.md 的 Python 一节")
    elif t == "web":
        ok = re.search(r"deploy-pages|peaceiris/actions-gh-pages|vercel|netlify", wf) or \
            any(os.path.exists(os.path.join(root, x)) for x in ("vercel.json", "netlify.toml"))
        add("PASS" if ok else "WARN", "C1", "网页：" + ("推送后会自动上线" if ok else "没看到自动上线配置（GitHub Pages / Vercel 等）"),
            "" if ok else "复制 assets/pages.yml 到 .github/workflows/，见 references/channels.md 的网页一节")
    elif t == "browser-ext":
        add("INFO", "C1", "浏览器插件：上架 Chrome 应用商店后由商店自动更新；GitHub 下载安装的不会更新", "见 references/channels.md")
    elif t == "mac-app":
        ok = re.search(r"SUFeedURL|Sparkle", "\n".join(rd(p) for p in glob.glob(os.path.join(root, "**/Info.plist"), recursive=True)))
        add("PASS" if ok else "WARN", "C1", "Mac 应用：" + ("接了 Sparkle 自动更新" if ok else "没接应用内自动更新（Sparkle）也没看到 Homebrew Cask"),
            "" if ok else "见 references/channels.md 的 Mac 一节")
    elif t == "homebrew-tap":
        add("PASS", "C1", "Homebrew tap：用户 brew upgrade 即可更新")
    elif t == "scripts":
        add("INFO", "C1", "脚本 / 模板 / 文档类：没有能自动推给用户的渠道，用户只能 git pull",
            "可选：加 assets/update_check.py 那种「有新版就提醒」；或改做成插件 / 网页")


# ---------- 开源基本功 ----------
SECRET = re.compile(r"(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}|sk-[A-Za-z0-9_-]{32,}|sk-ant-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|xox[bprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
HOMEP = re.compile(r"(/Users/(?!<|\$|USER|you|me|name|xxx)[A-Za-z0-9._-]+/|/home/(?!<|\$|user|you)[A-Za-z0-9._-]+/|C:\\\\Users\\\\[A-Za-z0-9._-]+)")


def check_basics(root, files):
    lic = [f for f in files if re.match(r"(?i)^(license|licence|copying)(\.|$)", os.path.basename(f)) and "/" not in f]
    add("PASS" if lic else "FAIL", "G1", "LICENSE " + ("在：" + lic[0] if lic else "没有：别人在法律上不能用你的代码"),
        "" if lic else "加一个 LICENSE（个人项目常用 MIT）")
    add("PASS" if os.path.exists(os.path.join(root, "README.md")) else "FAIL", "G2",
        "README.md " + ("在" if os.path.exists(os.path.join(root, "README.md")) else "没有"))
    leaks, homes = [], []
    for f in files:
        p = os.path.join(root, f)
        if not os.path.isfile(p) or os.path.getsize(p) > 2_000_000:
            continue
        s = rd(p)
        if SECRET.search(s):
            leaks.append(f)
        if HOMEP.search(s):
            homes.append(f)
    if leaks:
        add("FAIL", "G3", "疑似密钥 / token 在这些文件里：" + "、".join(leaks[:5]), "删掉并作废那个密钥；已推送过的要当作已泄露")
    else:
        add("PASS", "G3", "没扫到密钥 / token")
    if homes:
        add("WARN", "G4", "有写死的个人电脑路径（会暴露用户名、别人电脑上也跑不通）：" + "、".join(homes[:5]), "改成 ~ 或相对路径")
    else:
        add("PASS", "G4", "没有写死的个人电脑路径")
    envs = [f for f in files if re.search(r"(^|/)\.env($|\.)", f) and not f.endswith((".example", ".sample"))]
    if envs:
        add("FAIL", "G5", "这些 .env 文件被提交了：" + "、".join(envs), "从 git 里删掉并加进 .gitignore")
    elif not os.path.exists(os.path.join(root, ".gitignore")):
        add("WARN", "G5", "没有 .gitignore", "加一个，至少忽略 .env、.DS_Store")
    else:
        add("PASS", "G5", ".gitignore 在，没有提交 .env")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--base", default=None, help="和哪个分支比（默认远程主分支 origin/HEAD，其次 origin/main、origin/master）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(a.root))
    if not os.path.isdir(root):
        print(f"找不到目录：{root}\nSTATUS=FAIL")
        sys.exit(1)
    base = a.base
    if base is None:
        head = (git(root, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD") or "").strip()
        for cand in [head, "origin/main", "origin/master"]:
            if cand and git(root, "rev-parse", "--verify", "-q", cand):
                base = cand
                break
    files = tracked(root)
    if not base:
        add("INFO", "P3", "没有远程主分支可比较，跳过「改了内容有没有涨版本号」", "git fetch 后再跑，或用 --base 指定")
    types = detect(root, files)
    add("INFO", "T0", "这个仓库是：" + "、".join(types))
    for t in types:
        if t == "plugin":
            check_plugin(root, base, files)
        else:
            check_channel(root, t)
    check_basics(root, files)

    status = "FAIL" if any(r[0] == "FAIL" for r in R) else "WARN" if any(r[0] == "WARN" for r in R) else "PASS"
    if a.json:
        print(json.dumps({"types": types, "status": status,
                          "items": [dict(zip(("level", "id", "text", "fix"), r)) for r in R]}, ensure_ascii=False, indent=2))
    else:
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}
        for lv, cid, text, fix in R:
            print(f"{icon[lv]} {cid} {text}" + (f"\n     → {fix}" if fix and lv != "PASS" else ""))
        print(f"STATUS={status}")
    sys.exit(1 if status == "FAIL" else 0)


if __name__ == "__main__":
    main()
