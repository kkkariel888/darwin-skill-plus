#!/usr/bin/env python3
"""发新版本时用：一次改齐所有 AI 的版本号（Claude、Codex，以及后来加的其他 AI；通用版，任何插件市场仓库都能直接用）。
ALL_MANIFESTS：插件文件夹里每个 .xxx-plugin/plugin.json、根目录每份 marketplace.json 都会改。
用法：
  python3 tools/bump.py              所有插件最后一位 +1（1.2.3 → 1.2.4）
  python3 tools/bump.py 2.0.0        所有插件改成 2.0.0
  python3 tools/bump.py --plugin foo 只改 foo 这个插件
改完照常提合并申请；合并后 Claude app 自动同步，Claude Code / Codex 开了自动更新的下次启动自动更新。
"""
import argparse, glob, json, pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
MK = R / ".claude-plugin/marketplace.json"


def load(p): return json.loads(p.read_text(encoding="utf-8"))
def save(p, d): p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def plus1(v): parts = v.split("."); parts[-1] = str(int(parts[-1]) + 1); return ".".join(parts)


ap = argparse.ArgumentParser()
ap.add_argument("version", nargs="?")
ap.add_argument("--plugin")
a = ap.parse_args()
if not MK.exists():
    sys.exit("找不到 .claude-plugin/marketplace.json，这不是插件市场仓库")
m = load(MK)
names = [e["name"] for e in m.get("plugins", [])]
if a.plugin and a.plugin not in names:
    sys.exit(f"没有插件 {a.plugin}，现有：{', '.join(names)}")
for e in m.get("plugins", []):
    if a.plugin and e["name"] != a.plugin:
        continue
    src = e.get("source"); src = src.get("path") if isinstance(src, dict) else src
    pdir = (R / (src or f"plugins/{e['name']}")).resolve()
    cp = pdir / ".claude-plugin/plugin.json"
    cur = load(cp).get("version") or e.get("version") or "0.0.0"
    new = a.version or plus1(cur)
    for p in sorted(pdir.glob(".*/plugin.json")):
        d = load(p); d["version"] = new; save(p, d); print(f"{p.relative_to(R)} → {new}")
    if "version" in e:
        e["version"] = new
    for p in sorted(set(R.glob(".*/marketplace.json")) | set(R.glob(".*/*/marketplace.json"))):
        if p == MK:
            continue
        d = load(p); hit = False
        for x in d.get("plugins", []):
            if x.get("name") == e["name"] and "version" in x:
                x["version"] = new; hit = True
        if hit:
            save(p, d); print(f"{p.relative_to(R)} → {new}")
    print(f"{e['name']}: {cur} → {new}")
save(MK, m)
print(f"{MK.relative_to(R)} 已同步")
