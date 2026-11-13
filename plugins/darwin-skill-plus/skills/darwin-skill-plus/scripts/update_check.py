#!/usr/bin/env python3
"""每次开工前查一下有没有新版本，有就自己更新（只用 Python 自带库）。
复制进 skill 的 scripts/ 后，只改下面 REPO 和 MARKET 两行。
打印一行结论，最后一行 STATUS=latest / updated / outdated / offline。没网就跳过，不影响干活。
"""
import json, os, shutil, subprocess, urllib.request

REPO = "kkkariel888/darwin-skill-plus"        # GitHub 仓库，比如 kkkariel888/ariel-broll-video
MARKET = "darwin-skill-plus"              # .claude-plugin/marketplace.json 里的 name
HERE = os.path.dirname(os.path.abspath(__file__))
PJ = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".claude-plugin", "plugin.json"))


def local():
    try:
        return json.load(open(PJ, encoding="utf-8"))
    except Exception:
        return {}


def vt(v):
    return tuple(int(x) if x.isdigit() else 0 for x in str(v).split("."))


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=180).returncode == 0
    except Exception:
        return False


def main():
    me = local(); plugin = me.get("name", ""); mine = me.get("version", "0")
    raw = f"https://raw.githubusercontent.com/{REPO}/HEAD/plugins/{plugin}/.claude-plugin/plugin.json"
    try:
        with urllib.request.urlopen(raw, timeout=6) as r:
            latest = json.loads(r.read().decode("utf-8")).get("version")
    except Exception:
        latest = None
    if not latest:
        print("查不到新版本（可能没网），先用现在这版。\nSTATUS=offline"); return
    if vt(latest) <= vt(mine):
        print(f"已是最新版 {mine}。\nSTATUS=latest"); return
    done = False
    if shutil.which("claude"):
        done = (run(["claude", "plugin", "marketplace", "update", MARKET]) and
                run(["claude", "plugin", "update", f"{plugin}@{MARKET}"])) or done
    if shutil.which("codex"):
        done = run(["codex", "plugin", "marketplace", "upgrade", MARKET]) or done
    if done:
        print(f"发现新版本 {latest}（现在 {mine}），已自动更新，下次开新对话生效。\nSTATUS=updated")
    else:
        print(f"发现新版本 {latest}（现在 {mine}）。Claude 桌面 app / 网页版会自动同步；"
              f"其他情况请让 AI 帮你更新插件 {plugin}@{MARKET}。\nSTATUS=outdated")


if __name__ == "__main__":
    main()
