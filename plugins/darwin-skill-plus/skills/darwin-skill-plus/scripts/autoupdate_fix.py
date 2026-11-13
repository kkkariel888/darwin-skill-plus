#!/usr/bin/env python3
"""达尔文增强版：优化完自动补齐「用户能自动更新」要的东西（只用 Python 自带库）。
只改本地文件，不提交、不推送。

用法：python3 autoupdate_fix.py <仓库根目录> --base <优化开始前的 commit> [--repo 用户名/仓库名]
做的事（缺什么补什么，已经有的不动）：
  1. tools/bump.py（没有，或写死了插件名 → 换成通用版）
  2. tools/check_version_bump.py + .github/workflows/version-check.yml（GitHub 自动检查忘涨版本号）
  3. .gitignore（没有就建）
  4. skill 的 scripts/update_check.py（开工查新版本；需要 --repo 或能从 origin 读出仓库名）
  5. 版本号：几处不一致 → 改齐；相比 --base 改了内容但没涨 → 最后一位 +1
最后一行：FIX=DONE / FIX=NEED_LAYOUT（不是插件市场结构，要照 references/auto-update-layout.md 搭）/ FIX=ERROR
README 的安装说明、SKILL.md 开工那一行由 agent 照 references 补（要读懂原文再加，不适合脚本硬插）。
"""
import argparse, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets", "release"))
done = []


def git(root, *a):
    r = subprocess.run(["git", "-C", root, *a], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def lj(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def sj(p, d):
    open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def copy(src, dst, root, why):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(ASSETS, src), dst)
    done.append(f"{why}：{os.path.relpath(dst, root)}")


def plus1(v):
    p = str(v).split(".")
    p[-1] = str(int(p[-1]) + 1) if p[-1].isdigit() else "1"
    return ".".join(p)


def vt(v):
    return tuple(int(x) if x.isdigit() else 0 for x in str(v).split("."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--base", required=True)
    ap.add_argument("--repo", default=None)
    a = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(a.root))
    mk_path = os.path.join(root, ".claude-plugin/marketplace.json")
    mk = lj(mk_path)
    if not mk or not mk.get("plugins"):
        print("不是插件市场结构（没有 .claude-plugin/marketplace.json），脚本不动文件。\nFIX=NEED_LAYOUT")
        return
    if git(root, "rev-parse", "--verify", "-q", a.base) is None:
        print(f"找不到 --base {a.base}\nFIX=ERROR")
        sys.exit(1)

    # 1-3 工具和配置
    bump = os.path.join(root, "tools/bump.py")
    if not os.path.exists(bump):
        copy("bump.py", bump, root, "加一键改版本号")
    elif re.search(r"plugins/[A-Za-z0-9_-]+/\.claude-plugin", open(bump, encoding="utf-8").read()):
        copy("bump.py", bump, root, "换成通用版一键改版本号")
    if not os.path.exists(os.path.join(root, "tools/check_version_bump.py")):
        copy("check_version_bump.py", os.path.join(root, "tools/check_version_bump.py"), root, "加版本号检查脚本")
    wf_dir = os.path.join(root, ".github/workflows")
    wf_all = "".join(open(os.path.join(wf_dir, f), encoding="utf-8").read() for f in os.listdir(wf_dir)) if os.path.isdir(wf_dir) else ""
    if "check_version_bump" not in wf_all:
        copy("version-check.yml", os.path.join(wf_dir, "version-check.yml"), root, "加 GitHub 自动检查")
    gi = os.path.join(root, ".gitignore")
    if not os.path.exists(gi):
        open(gi, "w").write(".DS_Store\n__pycache__/\n.env\nnode_modules/\n")
        done.append("加 .gitignore")

    repo = a.repo
    if not repo:
        url = (git(root, "remote", "get-url", "origin") or "").strip()
        m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
        repo = m.group(1) if m else None

    for e in mk["plugins"]:
        name = e.get("name")
        src = e.get("source"); src = src.get("path") if isinstance(src, dict) else src
        rel = os.path.normpath(src or f"plugins/{name}")
        pdir = os.path.join(root, rel)
        cp_path = os.path.join(pdir, ".claude-plugin/plugin.json")
        xp_path = os.path.join(pdir, ".codex-plugin/plugin.json")
        cp = lj(cp_path)
        if not cp:
            print(f"[{name}] 缺 plugin.json\nFIX=NEED_LAYOUT")
            return

        # 4 开工查新版本
        for sk in sorted(os.listdir(os.path.join(pdir, "skills"))) if os.path.isdir(os.path.join(pdir, "skills")) else []:
            uc = os.path.join(pdir, "skills", sk, "scripts", "update_check.py")
            if not os.path.exists(uc) and repo:
                os.makedirs(os.path.dirname(uc), exist_ok=True)
                t = open(os.path.join(ASSETS, "update_check.py"), encoding="utf-8").read()
                t = t.replace("__OWNER__/__REPO__", repo).replace("__MARKET__", mk.get("name", ""))
                open(uc, "w", encoding="utf-8").write(t)
                done.append(f"[{name}] 加开工查新版本脚本：{os.path.relpath(uc, root)}（SKILL.md 开工那一行要 agent 补）")

        # 5 版本号
        xp = lj(xp_path)
        vers = [v for v in [cp.get("version"), e.get("version"), (xp or {}).get("version")] if v]
        cur = max(vers, key=vt) if vers else "0.1.0"
        changed = [c for c in (git(root, "diff", "--name-only", f"{a.base}..HEAD", "--", rel) or "").splitlines()
                   + (git(root, "diff", "--name-only", "--", rel) or "").splitlines() if c and "plugin.json" not in c]
        old_raw = git(root, "show", f"{a.base}:{rel}/.claude-plugin/plugin.json")
        try:
            old = json.loads(old_raw).get("version") if old_raw else None
        except Exception:
            old = None
        new = plus1(cur) if (changed and old and vt(cur) <= vt(old)) else cur
        if not cp.get("version") or len(set(vers)) > 1 or new != cur:
            cp["version"] = new; sj(cp_path, cp)
            if xp is not None:
                xp["version"] = new; sj(xp_path, xp)
            if "version" in e:
                e["version"] = new
            sj(mk_path, mk)
            why = f"改了 {len(changed)} 个文件，版本号 {old} → {new}" if new != cur else f"版本号几处改齐为 {new}"
            done.append(f"[{name}] {why}")
        else:
            done.append(f"[{name}] 版本号 {cur} 不用动")

    print("\n".join("✔ " + d for d in done) if done else "什么都不缺，没改文件。")
    print("FIX=DONE")


if __name__ == "__main__":
    main()
