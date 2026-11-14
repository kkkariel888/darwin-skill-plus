#!/usr/bin/env python3
"""开工前查新版本：有新版就把新版 skill 下载下来，这一次直接用新版干活（只用 Python 自带库）。
任何 agent 都一样：Claude Code 终端、Claude 桌面 app（Code 页面 / Cowork）、Codex。
复制进 skill 的 scripts/ 后，只改下面 REPO 和 MARKET 两行。

最后一行：
  STATUS=latest   已是最新，照常干活
  STATUS=live     有新版，已下载到 LIVE_SKILL_DIR=<文件夹>：读那里的 SKILL.md，这次按新版做
  STATUS=updated  有新版，临时下载没成功，但插件已更新，下次对话生效
  STATUS=outdated 有新版，没能下载也没能更新，先用现在这版
  STATUS=offline  查不到（没网），先用现在这版
"""
import io, json, os, shutil, subprocess, tarfile, tempfile, urllib.request

REPO = "kkkariel888/darwin-skill-plus"        # GitHub 仓库，比如 kkkariel888/ariel-broll-video
MARKET = "darwin-skill-plus"              # .claude-plugin/marketplace.json 里的 name
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
PJ = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".claude-plugin", "plugin.json"))
LIVE_MARK = os.path.join(SKILL_DIR, ".live.json")   # 临时下载的新版里才有，记着它是哪个插件、哪个版本
UA = {"User-Agent": "skill-update-check"}


def local():
    for p in (LIVE_MARK, PJ):
        try:
            d = json.load(open(p, encoding="utf-8"))
            if d.get("name"):
                return d
        except Exception:
            pass
    return {}


def vt(v):
    return tuple(int(x) if x.isdigit() else 0 for x in str(v).split("."))


def get(url, timeout=15):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120).returncode == 0
    except Exception:
        return False


def cache_root():
    for d in (os.path.join(os.path.expanduser("~"), ".cache", "skill-live"), os.path.join(tempfile.gettempdir(), "skill-live")):
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:
            pass
    return None


def download(skill_rel, dest):
    """只下 skill 那一个文件夹：先用 GitHub 文件列表逐个下，不行再下整个仓库压缩包挑出来。"""
    tmp = dest + ".part"
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        tree = json.loads(get(f"https://api.github.com/repos/{REPO}/git/trees/HEAD?recursive=1"))
        files = [t["path"] for t in tree.get("tree", []) if t.get("type") == "blob" and t["path"].startswith(skill_rel + "/")]
        if not files:
            raise RuntimeError("empty")
        def one(f):
            out = os.path.join(tmp, f[len(skill_rel) + 1:])
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "wb").write(get(f"https://raw.githubusercontent.com/{REPO}/HEAD/{f}", 30))
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(one, files))   # 同时下，哪个失败就整体失败、改走压缩包
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        data = get(f"https://codeload.github.com/{REPO}/tar.gz/HEAD", 120)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
            for m in t.getmembers():
                parts = m.name.split("/", 1)
                if len(parts) == 2 and parts[1].startswith(skill_rel + "/") and m.isfile():
                    out = os.path.join(tmp, parts[1][len(skill_rel) + 1:])
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    open(out, "wb").write(t.extractfile(m).read())
    if not os.path.exists(os.path.join(tmp, "SKILL.md")):
        raise RuntimeError("下载的新版里没有 SKILL.md")
    shutil.rmtree(dest, ignore_errors=True)
    os.rename(tmp, dest)


def main():
    me = local(); plugin = me.get("name", ""); mine = me.get("version", "0")
    if not plugin:
        print("读不到本插件的版本号，跳过检查。\nSTATUS=offline"); return
    try:
        latest = json.loads(get(f"https://raw.githubusercontent.com/{REPO}/HEAD/plugins/{plugin}/.claude-plugin/plugin.json", 8)).get("version")
    except Exception:
        latest = None
    if not latest:
        print("查不到新版本（可能没网），先用现在这版。\nSTATUS=offline"); return
    if vt(latest) <= vt(mine):
        print(f"已是最新版 {mine}。\nSTATUS=latest"); return

    # 1. 这一次就用新版：下到缓存，告诉 agent 去读
    skill_rel = me.get("skill_rel") or f"plugins/{plugin}/skills/{os.path.basename(SKILL_DIR)}"
    root = cache_root()
    if root:
        dest = os.path.join(root, REPO.replace("/", "__"), latest)
        try:
            if not os.path.exists(os.path.join(dest, "SKILL.md")):
                download(skill_rel, dest)
            json.dump({"name": plugin, "version": latest, "skill_rel": skill_rel},
                      open(os.path.join(dest, ".live.json"), "w", encoding="utf-8"))
            # 2. 能更新的顺手在后台更新（Claude Code 终端 / Codex），不让用户等；下次对话直接就是新版
            bg = []
            if shutil.which("claude"):
                bg.append(f'claude plugin marketplace update {MARKET} && claude plugin update {plugin}@{MARKET}')
            if shutil.which("codex"):
                bg.append(f'codex plugin marketplace upgrade {MARKET}')
            for c in bg:
                try:
                    subprocess.Popen(c, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                except Exception:
                    pass
            print(f"发现新版本 {latest}（现在 {mine}），已下载，这次直接用新版。")
            print(f"LIVE_SKILL_DIR={dest}")
            print("STATUS=live"); return
        except Exception as e:
            print(f"新版临时下载失败：{e}")

    done = False
    if shutil.which("claude"):
        done = (run(["claude", "plugin", "marketplace", "update", MARKET]) and
                run(["claude", "plugin", "update", f"{plugin}@{MARKET}"])) or done
    if shutil.which("codex"):
        done = run(["codex", "plugin", "marketplace", "upgrade", MARKET]) or done
    if done:
        print(f"发现新版本 {latest}（现在 {mine}），已自动更新，下次开新对话生效。\nSTATUS=updated")
    else:
        print(f"发现新版本 {latest}（现在 {mine}），这次先用现在这版。\nSTATUS=outdated")


if __name__ == "__main__":
    main()
