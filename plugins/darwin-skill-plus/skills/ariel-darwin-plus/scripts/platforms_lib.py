# platform-check: skip-file
"""平台规范表的公共读取（platform_check.py / platform_fix.py 共用，只用 Python 自带库）。
要适配哪些 AI：命令行 --platforms > 仓库根目录 agent-platforms.json 的 targets > 规范表 default（Code 页面 + Codex）。
仓库自己加的新 AI 规范写在 agent-platforms.json 的 custom 里，格式和 assets/platforms.json 一样。"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(os.path.dirname(HERE), "assets", "platforms.json")
REPO_FILE = "agent-platforms.json"


def lj(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def registry(root):
    reg = lj(REG) or {"default": ["claude-desktop", "codex"], "platforms": {}}
    mine = lj(os.path.join(root, REPO_FILE)) or {}
    plats = dict(reg.get("platforms", {}))
    plats.update(mine.get("custom") or {})
    return reg, plats, mine


def targets(root, arg=None):
    reg, plats, mine = registry(root)
    if arg:
        t = [p.strip() for p in arg.split(",") if p.strip()]
        src = "这次指定"
    elif mine.get("targets"):
        t, src = list(mine["targets"]), f"仓库里 {REPO_FILE} 写的"
    else:
        t, src = list(reg.get("default", [])), "默认"
    return t, plats, src


def plugin_dirs(root):
    """[(插件名, 插件文件夹)]：以 Claude 市场清单为准，没有就看 plugins/*/。"""
    m = lj(os.path.join(root, ".claude-plugin/marketplace.json")) or {}
    out = []
    for e in m.get("plugins") or []:
        src = e.get("source")
        src = src.get("path") if isinstance(src, dict) else src
        out.append((e.get("name", "?"), os.path.normpath(os.path.join(root, src or f"plugins/{e.get('name')}"))))
    if not out and os.path.isdir(os.path.join(root, "plugins")):
        for n in sorted(os.listdir(os.path.join(root, "plugins"))):
            d = os.path.join(root, "plugins", n)
            if os.path.isdir(os.path.join(d, "skills")):
                out.append((n, d))
    return out
