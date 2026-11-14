#!/usr/bin/env python3
"""真实体验测试的成绩单（不花 token）：拿体验剧本里的标准，对照真跑记下的流水和最后的文件夹，逐条打 ✅ / ❌。

用法：python3 ux_report.py <journey.json> <流水.jsonl> [--folder 交付文件夹] [--prev 上次成绩.json] [--out 成绩单]
输出 <out>.md（给人看）和 <out>.json（下次对比用）。最后一行 STATUS=PASS / FAIL。
"""
import argparse, fnmatch, json, os, sys

DEFAULT = {"first_feedback_s": 10, "silent_wait_s": 30, "click_response_s": 5, "user_clicks": 20, "user_messages": 3}


def load_journal(p):
    out = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return sorted(out, key=lambda r: r["t"])


def fmt(s):
    if s is None:
        return "—"
    return f"{s:.0f} 秒" if s < 90 else f"{s / 60:.1f} 分钟"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey"); ap.add_argument("journal")
    ap.add_argument("--folder"); ap.add_argument("--prev"); ap.add_argument("--out", default="体验成绩单")
    a = ap.parse_args()
    J = json.load(open(a.journey, encoding="utf-8"))
    lim = dict(DEFAULT); lim.update(J.get("limits") or {})
    ev = load_journal(a.journal)
    if not ev:
        print("流水是空的，没法打分\nSTATUS=FAIL"); sys.exit(1)
    rows = []   # (标准, 结果, ok)

    def row(name, val, ok, note=""):
        rows.append({"name": name, "value": val, "ok": ok, "note": note})

    t_start = next((e["t"] for e in ev if e["kind"] == "start"), ev[0]["t"])
    t_end = next((e["t"] for e in reversed(ev) if e["kind"] == "end"), ev[-1]["t"])
    ended = any(e["kind"] == "end" for e in ev)
    total = t_end - t_start

    # 1. 开工多久有反应
    first = next((e["t"] - t_start for e in ev if e["kind"] in ("say", "step") and e["t"] >= t_start), None)
    row("开工多久有第一句反馈", fmt(first), first is not None and first <= lim["first_feedback_s"], f"标准 ≤ {lim['first_feedback_s']} 秒")

    # 2. 最长干等（AI 在干活、但用户什么都看不到的时间；等用户回答的时间不算）
    gaps, waiting_user, last = [], False, t_start
    for e in ev:
        if e["t"] < t_start:
            continue
        if e["kind"] == "ask":
            gaps.append((e["t"] - last, e["name"])); waiting_user = True; last = e["t"]; continue
        if e["kind"] in ("user_msg", "user_click"):
            waiting_user = False; last = e["t"]; continue
        if e["kind"] in ("say", "step", "end") and not waiting_user:
            gaps.append((e["t"] - last, e["name"])); last = e["t"]
    worst = max(gaps, default=(0, ""))
    row("最长干等（用户看不到任何进度）", fmt(worst[0]) + (f"（在「{worst[1]}」之前）" if worst[1] else ""),
        worst[0] <= lim["silent_wait_s"], f"标准 ≤ {lim['silent_wait_s']} 秒，超过就要显示进度")

    # 3. 每一步花的时间
    seen = {}
    for e in ev:
        if e["kind"] == "step" and e["name"] not in seen:
            seen[e["name"]] = e["t"]
    for st in J.get("steps", []):
        sid = st["id"]
        if sid not in seen:
            row(f"步骤：{st.get('name', sid)}", "没走到", False, "流程卡住或漏了这一步")
            continue
        frm = st.get("from", "start")
        t0 = t_start if frm == "start" else seen.get(frm)
        took = seen[sid] - t0 if t0 is not None else None
        b = st.get("budget_s")
        row(f"步骤：{st.get('name', sid)}", fmt(took), took is not None and (b is None or took <= b),
            f"标准 ≤ {fmt(b)}" + ("" if frm == "start" else f"（从「{frm}」算起）") if b else "只记录")

    # 4. 页面点了多久有反应
    reacts = [e for e in ev if e["kind"] == "page_react"]
    slow = [e for e in reacts if e.get("seconds") is None or e["seconds"] > e.get("limit", lim["click_response_s"])]
    if reacts:
        row("页面点了有没有反应", f"点了 {len(reacts)} 次，{len(slow)} 次没反应或太慢" + (f"（{'、'.join(e['name'] for e in slow[:3])}）" if slow else ""),
            not slow, f"标准 ≤ {lim['click_response_s']} 秒")

    # 5. 用户要动几下手
    clicks = sum(1 for e in ev if e["kind"] == "user_click")
    msgs = sum(1 for e in ev if e["kind"] == "user_msg")
    row("用户点了几下", f"{clicks} 下", clicks <= lim["user_clicks"], f"标准 ≤ {lim['user_clicks']}")
    row("用户发了几条消息", f"{msgs} 条", msgs <= lim["user_messages"], f"标准 ≤ {lim['user_messages']}（第一条需求不算）")
    asks = [e["name"] for e in ev if e["kind"] == "ask"]
    if asks:
        row("AI 停下来问了几次", f"{len(asks)} 次", len(asks) <= lim.get("asks", 99), "问了：" + "；".join(asks[:5]))

    # 6. 页面上的检查（一次看完之类）
    for e in ev:
        if e["kind"] == "check":
            row(e["name"], e.get("detail", ""), bool(e.get("ok")))

    # 7. 文件夹里留下了什么
    if a.folder and os.path.isdir(a.folder):
        allow = (J.get("deliver") or {}).get("allow", [])
        files = []
        for d, ds, fs in os.walk(a.folder):
            ds[:] = [x for x in ds if not x.startswith(".")]
            for f in fs:
                if not f.startswith("."):
                    files.append(os.path.relpath(os.path.join(d, f), a.folder))
        extra = [f for f in files if not any(fnmatch.fnmatch(f, p) for p in allow)]
        want = (J.get("deliver") or {}).get("must", [])
        missing = [p for p in want if not any(fnmatch.fnmatch(f, p) for f in files)]
        row("文件夹里只有用户要的东西", f"{len(files)} 个文件，多余 {len(extra)} 个" + (f"：{'、'.join(extra[:5])}" if extra else ""), not extra)
        if want:
            row("该交的东西都在", "缺：" + "、".join(missing) if missing else "都在", not missing)

    row("从头走到尾", fmt(total) if ended else f"没走完（停在 {fmt(total)}）", ended and (J.get("total_budget_s") is None or total <= J["total_budget_s"]),
        f"标准 ≤ {fmt(J['total_budget_s'])}" if J.get("total_budget_s") else "")

    prev = None
    if a.prev and os.path.exists(a.prev):
        prev = {r["name"]: r for r in json.load(open(a.prev, encoding="utf-8")).get("rows", [])}
    ok = all(r["ok"] for r in rows)
    lines = [f"# 体验成绩单：{J.get('project', '')}", "", f"用户：{J.get('user', '小白')}　总耗时：{fmt(total)}　点了 {clicks} 下　发了 {msgs} 条消息", "",
             "| 标准 | 这次 | 结果 |" + (" 上次 |" if prev else ""), "|---|---|---|" + ("---|" if prev else "")]
    for r in rows:
        p = prev.get(r["name"]) if prev else None
        lines.append(f"| {r['name']} | {r['value']} | {'✅' if r['ok'] else '❌'} {r['note']} |" + (f" {p['value'] if p else '—'} |" if prev else ""))
    bad = [r for r in rows if not r["ok"]]
    lines += ["", f"**{'全部达标' if ok else f'{len(bad)} 条不达标，按最高优先级修'}**"]
    open(a.out + ".md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump({"project": J.get("project"), "total_s": total, "clicks": clicks, "messages": msgs, "rows": rows},
              open(a.out + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n".join(lines))
    print("STATUS=" + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
