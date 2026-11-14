#!/usr/bin/env python3
# platform-check: skip-file
"""真实体验测试的「假用户」（不花 token）：像真人一样打开 skill 给用户的网页、等东西出来、点按钮、截图，
并记下「点了多久才有反应」「能不能一眼看完」。只用 Python 自带库 + 本机 Chrome / Edge / Chromium。

用法：python3 ux_page.py <网址> --script 页面剧本.json --journal 流水.jsonl --shots 截图文件夹 [--size 900x1000] [--show]

页面剧本是一个数组，按顺序做：
  {"wait": "一段字", "timeout": 180}                   等页面上出现这段字
  {"wait_count": "CSS 选择器", "n": 9, "timeout": 180}  等这种元素出现够 n 个（比如 9 张样图）
  {"click": "按钮上的字", "react": 5}                   点按钮（按字找），记下页面多久有变化，超过 react 秒算 ❌
  {"type": "CSS 选择器", "text": "要输入的字"}
  {"all_in_view": "CSS 选择器", "name": "样图一次看完"}  检查这些元素不用滚动就全在屏幕里（每个至少 120 像素宽）
  {"shot": "截图名"}
  {"sleep": 2}
  {"step": "步骤id"}                                    在流水里记一步（和 journey.json 对上）
最后一行：STATUS=done / STATUS=fail（哪一步卡住）
"""
import argparse, base64, glob, json, os, pathlib, platform, re, shutil, socket, struct, subprocess, sys, tempfile, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_log import log  # noqa: E402


def find_chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    c = []
    if platform.system() == "Darwin":
        c = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium",
             "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    elif platform.system() == "Windows":
        for b in [os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("LOCALAPPDATA", "")]:
            c += [os.path.join(b, "Google/Chrome/Application/chrome.exe"), os.path.join(b, "Microsoft/Edge/Application/msedge.exe")]
    for n in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"]:
        if shutil.which(n):
            c.append(shutil.which(n))
    c += sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium*/chrome-linux*/chrome")), reverse=True)
    for x in c:
        if x and os.path.exists(x):
            return x
    sys.exit("没找到 Chrome / Edge / Chromium\nSTATUS=fail")


class Page:
    def __init__(self, w, h, show):
        self.tmp = tempfile.mkdtemp(prefix="ux-page-")
        args = [find_chrome(), "--no-first-run", "--no-default-browser-check", "--disable-sync", "--mute-audio",
                f"--user-data-dir={self.tmp}", "--remote-debugging-port=0", f"--window-size={w},{h}", "about:blank"]
        if not show:
            args.insert(1, "--headless=new")
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            args.insert(1, "--no-sandbox")
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port, t0 = None, time.time()
        while time.time() - t0 < 30 and not port:
            p = pathlib.Path(self.tmp) / "DevToolsActivePort"
            if p.exists() and p.read_text().split():
                port = int(p.read_text().split()[0])
            time.sleep(0.05)
        if not port:
            sys.exit("Chrome 启动失败\nSTATUS=fail")
        for _ in range(100):
            try:
                pages = [t for t in json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2).read()) if t.get("type") == "page"]
                if pages:
                    break
            except Exception:
                pass
            time.sleep(0.1)
        m = re.match(r"ws://([^/:]+):(\d+)(/.*)", pages[0]["webSocketDebuggerUrl"])
        self.sock = socket.create_connection((m.group(1), int(m.group(2))), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {m.group(3)} HTTP/1.1\r\nHost: {m.group(1)}:{m.group(2)}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        self.rest = buf.split(b"\r\n\r\n", 1)[1]
        self.id = 0
        self.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)
        self.w, self.h = w, h

    def _exact(self, n):
        while len(self.rest) < n:
            c = self.sock.recv(max(65536, n - len(self.rest)))
            if not c:
                raise ConnectionError("Chrome 断开了")
            self.rest += c
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def _recv(self):
        data = b""
        while True:
            b1, b2 = self._exact(2)
            op, ln = b1 & 15, b2 & 127
            if ln == 126:
                ln = struct.unpack(">H", self._exact(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._exact(8))[0]
            pl = self._exact(ln)
            if op == 9:
                self._send(pl, 10); continue
            data += pl
            if b1 & 128:
                return data.decode("utf-8")

    def _send(self, pl, op=1):
        n = len(pl); hdr = bytes([128 | op])
        hdr += bytes([128 | n]) if n < 126 else (bytes([128 | 126]) + struct.pack(">H", n) if n < 65536 else bytes([128 | 127]) + struct.pack(">Q", n))
        mask = os.urandom(4)
        self.sock.sendall(hdr + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(pl)))

    def call(self, method, **params):
        self.id += 1; my = self.id
        self._send(json.dumps({"id": my, "method": method, "params": params}).encode())
        while True:
            msg = json.loads(self._recv())
            if msg.get("id") == my:
                return msg.get("result", {})

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        return r.get("result", {}).get("value")

    def shot(self, path):
        d = self.call("Page.captureScreenshot", format="png")["data"]
        pathlib.Path(path).write_bytes(base64.b64decode(d))

    def close(self):
        try:
            self.proc.terminate(); self.proc.wait(timeout=5)
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)


FIND_BTN = """(t=>{const els=[...document.querySelectorAll('button,a,[role=button],input[type=button],input[type=submit],label')]
 .filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&!e.disabled});
 const hit=els.find(e=>(e.innerText||e.value||'').trim()===t)||els.find(e=>(e.innerText||e.value||'').includes(t));
 if(!hit)return null; hit.scrollIntoView({block:'center'}); window.__uxChanged=0;
 if(!window.__uxObs){window.__uxObs=new MutationObserver(()=>{window.__uxChanged++});
   window.__uxObs.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true});}
 hit.click(); return (hit.innerText||hit.value||'').trim().slice(0,40);})(%s)"""

IN_VIEW = """(s=>{const els=[...document.querySelectorAll(s)].filter(e=>e.offsetParent!==null);
 const W=innerWidth,H=innerHeight; const out=els.filter(e=>{const r=e.getBoundingClientRect();
 return r.top<0||r.left<0||r.bottom>H+1||r.right>W+1||r.width<120});
 return {total:els.length,bad:out.length};})(%s)"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("--script", required=True); ap.add_argument("--journal", required=True)
    ap.add_argument("--shots", default="ux-截图"); ap.add_argument("--size", default="900x1000"); ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    w, h = [int(x) for x in a.size.lower().split("x")]
    os.makedirs(a.shots, exist_ok=True)
    acts = json.load(open(a.script, encoding="utf-8"))
    pg = Page(w, h, a.show)
    try:
        pg.call("Page.enable"); pg.call("Page.navigate", url=a.url)
        time.sleep(1)
        for i, act in enumerate(acts):
            to = act.get("timeout", 120)
            if "wait" in act:
                t0 = time.time()
                while not pg.js(f"document.body && document.body.innerText.includes({json.dumps(act['wait'])})"):
                    if time.time() - t0 > to:
                        pg.shot(os.path.join(a.shots, f"卡住_{i + 1}.png"))
                        log(a.journal, "check", f"等「{act['wait']}」", ok=False, detail=f"{to} 秒没出现")
                        print(f"第 {i + 1} 步：等了 {to} 秒，页面上没出现「{act['wait']}」\nSTATUS=fail"); return
                    time.sleep(0.5)
            elif "wait_count" in act:
                t0 = time.time(); n = act.get("n", 1)
                while (pg.js(f"document.querySelectorAll({json.dumps(act['wait_count'])}).length") or 0) < n:
                    if time.time() - t0 > to:
                        pg.shot(os.path.join(a.shots, f"卡住_{i + 1}.png"))
                        log(a.journal, "check", f"等 {n} 个 {act['wait_count']}", ok=False, detail=f"{to} 秒没出齐")
                        print(f"第 {i + 1} 步：{to} 秒内没出齐 {n} 个 {act['wait_count']}\nSTATUS=fail"); return
                    time.sleep(0.5)
            elif "click" in act:
                hit = pg.js(FIND_BTN % json.dumps(act["click"]))
                if not hit:
                    pg.shot(os.path.join(a.shots, f"找不到按钮_{i + 1}.png"))
                    log(a.journal, "check", f"找按钮「{act['click']}」", ok=False, detail="页面上没有这个按钮")
                    print(f"第 {i + 1} 步：页面上找不到按钮「{act['click']}」\nSTATUS=fail"); return
                t0 = time.time(); log(a.journal, "user_click", hit)
                lim = act.get("react", 5); took = None
                while time.time() - t0 < max(lim * 3, 15):
                    if pg.js("window.__uxChanged||0"):
                        took = round(time.time() - t0, 2); break
                    time.sleep(0.1)
                log(a.journal, "page_react", hit, seconds=took, limit=lim)
            elif "type" in act:
                pg.js(f"(e=>{{e.focus();e.value={json.dumps(act['text'])};e.dispatchEvent(new Event('input',{{bubbles:true}}))}})(document.querySelector({json.dumps(act['type'])}))")
                log(a.journal, "user_click", f"输入：{act['text'][:20]}")
            elif "all_in_view" in act:
                r = pg.js(IN_VIEW % json.dumps(act["all_in_view"])) or {"total": 0, "bad": 0}
                ok = r["total"] > 0 and r["bad"] == 0
                log(a.journal, "check", act.get("name", "一次看完"), ok=ok, detail=f"{r['total']} 个里 {r['bad']} 个要滚动或太小")
            elif "shot" in act:
                pg.shot(os.path.join(a.shots, f"{i + 1:02d}_{act['shot']}.png"))
            elif "sleep" in act:
                time.sleep(act["sleep"])
            elif "step" in act:
                log(a.journal, "step", act["step"])
        print("STATUS=done")
    finally:
        pg.close()


if __name__ == "__main__":
    main()
