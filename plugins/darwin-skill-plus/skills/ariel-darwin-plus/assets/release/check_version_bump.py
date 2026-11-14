#!/usr/bin/env python3
"""GitHub 自动检查用：插件内容改了、版本号却没涨，就报错拦下合并。
ALL_MANIFESTS：所有 AI 的 plugin.json 版本号都要一样。
用法：python3 tools/check_version_bump.py <对比的分支，比如 origin/main>
"""
import json, pathlib, subprocess, sys
R = pathlib.Path(__file__).resolve().parent.parent
base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"


def git(*a):
    return subprocess.run(["git", "-C", str(R), *a], capture_output=True, text=True).stdout


m = json.loads((R / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
bad = []
for e in m.get("plugins", []):
    src = e.get("source"); src = src.get("path") if isinstance(src, dict) else src
    rel = (src or f"plugins/{e['name']}").lstrip("./")
    changed = [c for c in git("diff", "--name-only", f"{base}...HEAD", "--", rel).splitlines() if c and "plugin.json" not in c]
    if not changed:
        continue
    now = json.loads((R / rel / ".claude-plugin/plugin.json").read_text(encoding="utf-8")).get("version")
    old_raw = git("show", f"{base}:{rel}/.claude-plugin/plugin.json")
    old = json.loads(old_raw).get("version") if old_raw.strip() else None
    vers = {now, e.get("version", now)}
    for xp in (R / rel).glob(".*/plugin.json"):
        vers.add(json.loads(xp.read_text(encoding="utf-8")).get("version"))
    if old == now:
        bad.append(f"❌ {e['name']}：改了 {len(changed)} 个文件，版本号还是 {now}。请运行 python3 tools/bump.py 后再提交。")
    elif len(vers) > 1:
        bad.append(f"❌ {e['name']}：几处版本号不一致 {sorted(map(str, vers))}。请运行 python3 tools/bump.py {now}。")
    else:
        print(f"✅ {e['name']}：{old} → {now}")
if bad:
    print("\n".join(bad)); sys.exit(1)
print("版本号检查通过")
