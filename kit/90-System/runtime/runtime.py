#!/usr/bin/env python3
# Super-agent 运行时骨架：Router + 3 Worker 常驻进程
# 职责：心跳登记（heartbeats 表）、任务队列（task_queue 表）、事件留痕（50-Events/）
# 任务处理器为占位实现：只登记、不改动用户内容文件；真正处理逻辑后续挂到 HANDLERS
# 用法: python3 runtime.py        （建议由 systemd 托管，见 super-brain.service）
import json
import os
import re
import signal
import sqlite3
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # 仓库根目录
DB = Path(__file__).parent / "state.db"
INBOX = ROOT / "00-Inbox"
EVENTS_DIR = ROOT / "50-Events"
HEARTBEAT_INTERVAL = 60        # 心跳间隔（秒）；watchdog 判死线 15 分钟
SCAN_INTERVAL = 60             # Router 扫描 Inbox 间隔
WORKERS = ["chat-worker", "code-worker", "knowledge-worker"]
TASK_ROUTING = {"inbox-triage": "knowledge-worker"}   # 任务类型 → 负责 Worker

stop = threading.Event()


def db():
    conn = sqlite3.connect(DB, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")  # 读写并发更稳
    conn.execute("""CREATE TABLE IF NOT EXISTS heartbeats(
        agent TEXT PRIMARY KEY, ts INTEGER, note TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS task_queue(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT, payload TEXT, status TEXT DEFAULT 'pending',
        created_at INTEGER, claimed_by TEXT, claimed_at INTEGER,
        done_at INTEGER, result TEXT,
        UNIQUE(type, payload))""")
    conn.commit()
    return conn


def log_event(kind, **fields):
    EVENTS_DIR.mkdir(exist_ok=True)
    line = json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                       "kind": kind, **fields}, ensure_ascii=False)
    with open(EVENTS_DIR / f"runtime-{time.strftime('%Y-%m-%d')}.jsonl", "a") as f:
        f.write(line + "\n")


def heartbeat(conn, agent, note=""):
    conn.execute("INSERT INTO heartbeats(agent,ts,note) VALUES(?,?,?) "
                 "ON CONFLICT(agent) DO UPDATE SET ts=excluded.ts, note=excluded.note",
                 (agent, int(time.time()), note))
    conn.commit()


LLM_CONF = Path(__file__).parent / "llm.json"   # 不入库，仅存服务器
KNOWLEDGE = ROOT / "10-Knowledge"
CATEGORIES = ["Concepts", "Decisions", "Playbooks"]

TRIAGE_PROMPT = """你是知识库整理员。用户给你一篇收集箱笔记，请整理归档。
只输出一个 JSON 对象（不要输出其他内容）：
{
  "category": "Concepts | Decisions | Playbooks 三选一（概念知识→Concepts，决策/结论→Decisions，流程/方法/模板→Playbooks）",
  "title": "简洁标题（可含中文，不要扩展名）",
  "summary": "一句话摘要（30字内）",
  "content": "整理后的 Markdown 正文：保留全部原始信息，理顺结构，去除口语冗余"
}"""


def load_llm():
    try:
        return json.loads(LLM_CONF.read_text(encoding="utf-8"))
    except Exception:
        return None


def call_llm(conf, content):
    body = json.dumps({
        "model": conf.get("model", "deepseek-chat"),
        "temperature": 0.2,
        "max_tokens": 3000,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": TRIAGE_PROMPT},
            {"role": "user", "content": content[:8000]},
        ],
    }).encode()
    req = urllib.request.Request(
        conf.get("base_url", "https://api.deepseek.com").rstrip("/") + "/v1/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + conf["api_key"],
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]


def handle_inbox(path_rel):
    src = ROOT / path_rel
    if not src.exists():
        return "源文件已不存在，跳过"
    conf = load_llm()
    if not conf or not conf.get("api_key"):
        return f"未配置 LLM，仅登记：{path_rel}（文件保持原位）"
    raw = call_llm(conf, src.read_text(encoding="utf-8", errors="replace"))
    info = json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip())
    cat = info.get("category") if info.get("category") in CATEGORIES else "Concepts"
    title = re.sub(r'[\\/:*?"<>|\s]+', "-", (info.get("title") or src.stem).strip())[:60].strip("-") or src.stem
    dest_dir = KNOWLEDGE / cat
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest, i = dest_dir / f"{title}.md", 1
    while dest.exists():
        i += 1
        dest = dest_dir / f"{title}-{i}.md"
    dest.write_text(
        f"# {info.get('title', title)}\n\n"
        f"> {info.get('summary', '')}\n"
        f"> 来源：{path_rel} ｜ {time.strftime('%Y-%m-%d')} 由 knowledge-worker 自动整理\n\n"
        f"{info.get('content', '').strip()}\n",
        encoding="utf-8")
    src.unlink()
    return f"已整理 → {dest.relative_to(ROOT)}（{info.get('summary', '')}）"


def handle(task_type, payload):
    if task_type == "inbox-triage":
        return handle_inbox(payload)
    return "无处理器，已跳过"


def router_loop():
    conn = db()
    while not stop.is_set():
        heartbeat(conn, "router", "scanning")
        if INBOX.exists():
            for f in sorted(INBOX.glob("*.md")):
                if f.name == "README.md":
                    continue
                cur = conn.execute(
                    "INSERT OR IGNORE INTO task_queue(type,payload,created_at) VALUES(?,?,?)",
                    ("inbox-triage", str(f.relative_to(ROOT)), int(time.time())))
                if cur.rowcount:
                    log_event("task_enqueued", type="inbox-triage", payload=str(f.relative_to(ROOT)))
            conn.commit()  # 立即提交，避免长事务锁库阻塞 Worker 心跳
        stop.wait(SCAN_INTERVAL)


def worker_loop(name):
    conn = db()
    my_types = [t for t, w in TASK_ROUTING.items() if w == name]
    while not stop.is_set():
        heartbeat(conn, name, "idle")
        for t in my_types:
            row = conn.execute(
                "SELECT id,payload FROM task_queue WHERE type=? AND status='pending' ORDER BY id LIMIT 1",
                (t,)).fetchone()
            if not row:
                continue
            tid, payload = row
            conn.execute("UPDATE task_queue SET status='doing', claimed_by=?, claimed_at=? WHERE id=?",
                         (name, int(time.time()), tid))
            conn.commit()
            log_event("task_claimed", id=tid, type=t, by=name)
            try:
                result = handle(t, payload)
                conn.execute("UPDATE task_queue SET status='done', done_at=?, result=? WHERE id=?",
                             (int(time.time()), result, tid))
                log_event("task_done", id=tid, type=t, by=name, result=result)
            except Exception as e:  # noqa
                conn.execute("UPDATE task_queue SET status='failed', done_at=?, result=? WHERE id=?",
                             (int(time.time()), str(e)[:200], tid))
                log_event("task_failed", id=tid, type=t, by=name, error=str(e)[:200])
            conn.commit()
        stop.wait(5)


def guard(fn, name):
    try:
        fn()
    except Exception as e:  # noqa
        log_event("thread_crashed", thread=name, error=str(e)[:300])


def main():
    db().close()  # 先建表，避免线程并发初始化竞争
    threads = [threading.Thread(target=guard, args=(router_loop, "router"), name="router", daemon=True)]
    threads += [threading.Thread(target=guard, args=(lambda w=w: worker_loop(w), w), name=w, daemon=True)
                for w in WORKERS]
    for t in threads:
        t.start()
    log_event("runtime_started", agents=["router"] + WORKERS, pid=os.getpid())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    while not stop.is_set():
        stop.wait(1)
    log_event("runtime_stopped", pid=os.getpid())


if __name__ == "__main__":
    sys.exit(main())
