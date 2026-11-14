#!/usr/bin/env python3
# platform-check: skip-file
"""平台适配补齐（会改文件，只用 Python 自带库）：把作者要的每个 AI 的安装文件、README 装法补齐。
只补缺的，不动已有的；代码层面的问题（只认 Mac、依赖、网络）不在这里改，看 platform_check.py 的说明手动改。

用法：python3 platform_fix.py <仓库根目录> [--platforms claude-desktop,codex] [--add cowork] [--repo 用户名/仓库名]
  --platforms  这个项目要适配哪些 AI（会记进仓库根目录 agent-platforms.json，以后体检照它查）
  --add        在现有的基础上再加几个
不填就按 agent-platforms.json，没有就按默认（Claude 桌面 app 的 Code 页面 + Codex）。
最后一行：STATUS=changed（改了文件）/ STATUS=ok（本来就齐）/ STATUS=error
"""
import argparse, json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from platforms_lib import REPO_FILE, lj, plugin_dirs, registry, targets  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
changed = []


def save(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def note(root, p, what):
    changed.append(f"{os.path.relpath(p, root)}：{what}")


def repo_name(root, arg):
    if arg:
        return arg
    try:
        u = subprocess.run(["git", "-C", root, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
        m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", u)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "<GitHub 用户名>/" + os.path.basename(root)


def make(kind, root, market, pn, pd, cm_entry):
    cp = lj(os.path.join(pd, ".claude-plugin/plugin.json")) or {}
    ver = cp.get("version") or cm_entry.get("version") or "0.1.0"
    desc = cp.get("description") or cm_entry.get("description") or ""
    author = (cp.get("author") or {}).get("name") or (market.get("owner") or {}).get("name") or ""
    rel = "./" + os.path.relpath(pd, root)
    disp = (market.get("metadata") or {}).get("displayName") or pn
    if kind == "claude-plugin":
        return {"name": pn, "version": ver, "description": desc, "author": {"name": author}, "license": cp.get("license", "MIT")}
    if kind == "codex-plugin":
        return {"name": pn, "version": ver, "description": desc, "skills": "./skills",
                "interface": {"displayName": disp, "shortDescription": desc[:40], "developerName": author, "category": "Productivity"}}
    if kind == "codex-entry":
        return {"name": pn, "source": {"source": "local", "path": rel},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"}
    return None


def fix_install(root, spec, plugins):
    cm_path = os.path.join(root, ".claude-plugin/marketplace.json")
    market = lj(cm_path) or {}
    entries = {e.get("name"): e for e in market.get("plugins") or []}
    for it in spec.get("install", []):
        kind = it.get("make", "")
        if it.get("scope") == "root":
            f = os.path.join(root, it["file"])
            if kind == "claude-market":
                if not market:
                    changed.append("❗ 没有 .claude-plugin/marketplace.json：整个仓库还不是插件市场结构，先按 references/plugin-layout.md 搭好再跑")
                continue
            if kind == "codex-market":
                d = lj(f) or {"name": market.get("name") or os.path.basename(root),
                              "interface": {"displayName": (market.get("metadata") or {}).get("displayName") or market.get("name", "")},
                              "plugins": []}
                have = {e.get("name") for e in d.get("plugins", [])}
                new = [make("codex-entry", root, market, pn, pd, entries.get(pn, {})) for pn, pd in plugins if pn not in have]
                if new or not os.path.exists(f):
                    d["plugins"] = d.get("plugins", []) + new
                    save(f, d); note(root, f, "补上 " + ("、".join(e["name"] for e in new) or "清单"))
                continue
            if kind.startswith("copy:") and lj(f) is None:
                srcd = lj(os.path.join(root, kind[5:]))
                if srcd is not None:
                    save(f, srcd); note(root, f, f"照 {kind[5:]} 抄了一份")
                else:
                    changed.append(f"❗ {it['file']}：要照抄的 {kind[5:]} 不存在")
            elif lj(f) is None:
                changed.append(f"❗ {it['file']}：规范表没写怎么生成（make），照 {spec.get('name')} 官方文档手写")
        else:
            for pn, pd in plugins:
                f = os.path.join(pd, it["file"])
                if lj(f) is not None:
                    continue
                if kind.startswith("copy:"):
                    d = lj(os.path.join(pd, kind[5:]))
                else:
                    d = make(kind, root, market, pn, pd, entries.get(pn, {}))
                if d is None:
                    changed.append(f"❗ {os.path.relpath(f, root)}：不知道怎么生成，照 {spec.get('name')} 官方文档手写")
                    continue
                save(f, d); note(root, f, f"新建（{spec.get('name')} 安装用）")


def fix_readme(root, spec, repo, plugins):
    p = os.path.join(root, "README.md")
    s = open(p, encoding="utf-8").read() if os.path.exists(p) else f"# {os.path.basename(root)}\n"
    if spec.get("mention") and re.search(spec["mention"], s):
        return
    market = (lj(os.path.join(root, ".claude-plugin/marketplace.json")) or {}).get("name") or repo.split("/")[-1]
    plugin = plugins[0][0] if plugins else repo.split("/")[-1]
    block = spec.get("readme") or f"**{spec.get('name')}**：（照官方文档写安装步骤）"
    block = block.replace("{repo}", repo).replace("{plugin}", plugin).replace("{market}", market).strip() + "\n\n"
    warn = re.search(r"^> ⚠️ 直接下载.*$", s, re.M)
    sec = re.search(r"^(#{2,3}) [^\n]*安装[^\n]*\n", s, re.M)
    if warn:
        s = s[:warn.start()] + block + s[warn.start():]
    elif sec:
        lv = len(sec.group(1))
        nxt = re.search(r"^#{1,%d} " % lv, s[sec.end():], re.M)
        at = sec.end() + nxt.start() if nxt else len(s)
        s = s[:at].rstrip("\n") + "\n\n" + block + s[at:]
    else:
        s = s.rstrip("\n") + "\n\n## 安装\n\n" + block
    open(p, "w", encoding="utf-8").write(s)
    note(root, p, f"加上 {spec.get('name')} 的装法")


def fix_tools(root):
    for name in ("bump.py", "check_version_bump.py"):
        dst = os.path.join(root, "tools", name)
        src = next((x for x in (os.path.join(ASSETS, name), os.path.join(ASSETS, "release", name)) if os.path.exists(x)), "")
        if os.path.exists(dst) and "ALL_MANIFESTS" not in open(dst, encoding="utf-8").read() and os.path.exists(src):
            shutil.copyfile(src, dst); note(root, dst, "换成新版（新加的 AI 的版本号也一起改）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("--platforms"); ap.add_argument("--add"); ap.add_argument("--repo")
    a = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(a.root))
    plats, reg, _ = targets(root, a.platforms)
    if a.add:
        plats += [p.strip() for p in a.add.split(",") if p.strip() and p.strip() not in plats]
    unknown = [p for p in plats if p not in reg]
    if unknown:
        print(f"规范表里没有：{unknown}。先读它的官方文档，把安装规范写进仓库根目录 {REPO_FILE} 的 custom（格式照 assets/platforms.json）。")
        print("STATUS=error"); sys.exit(1)
    _, _, mine = registry(root)
    default = (lj(os.path.join(ASSETS, "platforms.json")) or {}).get("default", [])
    if a.platforms or a.add or mine:
        if mine.get("targets") != plats:
            mine["targets"] = plats
            save(os.path.join(root, REPO_FILE), mine); note(root, os.path.join(root, REPO_FILE), "记下要适配：" + "、".join(plats))
    plugins = plugin_dirs(root)
    repo = repo_name(root, a.repo)
    for p in plats:
        fix_install(root, reg[p], plugins)
    plugins = plugin_dirs(root)
    for p in plats:
        fix_readme(root, reg[p], repo, plugins)
    fix_tools(root)
    print("要适配：" + "、".join(reg[p]["name"] for p in plats) + ("（默认）" if plats == default and not mine else ""))
    for c in changed:
        print(("" if c.startswith("❗") else "✏️ ") + c)
    if any(c.startswith("❗") for c in changed):
        print("STATUS=error"); sys.exit(1)
    print("STATUS=" + ("changed" if changed else "ok"))


if __name__ == "__main__":
    main()
