#!/usr/bin/env python3
"""真实体验测试的记账本（只用 Python 自带库，不花 token）：真跑时每发生一件用户看得见的事，就记一行带时间的流水。

用法：python3 ux_log.py <流水.jsonl> <类型> [说明]
类型：
  start          开始计时（用户刚把需求发出去）
  say  "话"      AI 对用户说了一句话（任何用户看得见的回复、进度）
  step 步骤id    走到了剧本里的某一步（id 要和 journey.json 的 steps 对上）
  ask  "问题"    AI 停下来问用户（从这里到用户回答的时间不算 AI 慢）
  user_msg "话"  用户发了一条消息
  user_click "按钮"  用户点了一下（ux_page.py 会自己记，不用手记）
  end            全部做完
"""
import json, sys, time


def log(path, kind, name="", **extra):
    rec = {"t": round(time.time(), 3), "kind": kind, "name": name}
    rec.update(extra)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    log(sys.argv[1], sys.argv[2], " ".join(sys.argv[3:]))
