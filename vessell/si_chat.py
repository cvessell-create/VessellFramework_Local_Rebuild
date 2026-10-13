"""SI chat: a local LLM game-chat service grounded in the owner story corpus.

The owner corpus is a hidden source layer: retrieved lines steer the model but
are not shown in game play. Every reply keeps its source ids and hashes so the
framework chatbox can reveal them, and generated text is always labelled as a
derivative, distinct from the owner's verbatim words.

"Learning" here means loop memory: game episodes and chat turns are stored and
summarised into each prompt. Model weights are never changed.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol

from vessell import story_corpus

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models" / "Qwen--Qwen2.5-0.5B-Instruct-GGUF"
GGUF_NAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
# Pinned from the Hugging Face LFS metadata for Qwen/Qwen2.5-0.5B-Instruct-GGUF.
GGUF_SHA256 = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"
OLLAMA_MODEL = "vessell-si-qwen2.5-0.5b"
OLLAMA_URL = "http://127.0.0.1:11434"
MEMORY_PATH = ROOT / "outputs" / "si_chat" / "memory.jsonl"
SCHEMA = "vessell-si-chat/v1"
MAX_MESSAGE = 500
ALLOWED_ORIGINS = re.compile(r"^http://(127\.0\.0\.1|localhost)(:\d+)?$")

_STOP = frozenset(
    ["a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "how", "i", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this", "to", "was", "what", "when", "where", "which", "who", "why", "with", "you", "your", "me", "my", "do", "does", "did", "can"]
)

LABELS = {
    "generated": "SI generated (derivative of owner sources)",
    "owner": "owner text, verbatim",
    "telemetry": "game telemetry (no model, no owner text)",
}

PERSONA = (
    "You are SI, the field intelligence voice inside the teen-rated retro shooter "
    "'Hail to the Analyst'. You talk to the player over a radio channel while an "
    "autopilot agent plays and learns. Speak in character, in 1-3 short sentences, "
    "vivid and game-like. Use the hidden briefing notes only as background lore and "
    "doctrine; never quote them at length, never mention files, notes or sources. "
    "Use the loop telemetry to comment on progress, danger and the next objective. "
    "Only mention items, doors, enemies, numbers or objectives that appear in the "
    "game facts or telemetry; never invent places, guards or secrets. Never open "
    "with 'I understand' or polite filler; talk like a terse handler on comms. "
    "At most two sentences.\n"
    "Style example: 'That run went down hard, Analyst. Restock before you trust "
    "that corridor.'"
)


def two_sentences(text: str) -> str:
    text = " ".join(text.strip().strip('"').split())
    return " ".join(re.split(r"(?<=[.!?])\s+", text)[:2])


def degenerate(text: str) -> bool:
    """True for empty output or token loops such as '1.0.0.0.0...'."""
    if len(re.findall(r"[A-Za-z]{2,}", text)) < 3:
        return True
    return bool(re.search(r"(.{1,6}?)\1{5,}", text))


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z][a-z-]{2,}", text.lower()) if t not in _STOP]


class Retriever:
    """IDF-weighted keyword retrieval over the verified owner corpus."""

    def __init__(self, corpus: dict[str, Any]) -> None:
        self.lines: list[dict[str, Any]] = corpus["lines"]
        self.stages = [s["id"] for s in corpus["stages"]]
        self._toks = [set(tokens(line["text"])) for line in self.lines]
        df: Counter[str] = Counter()
        for toks in self._toks:
            df.update(toks)
        n = len(self.lines)
        self._idf = {t: math.log(1 + n / c) for t, c in df.items()}

    def search(self, query: str, stage: str | None = None, k: int = 4) -> list[dict[str, Any]]:
        q = set(tokens(query))
        scored = []
        for i, line in enumerate(self.lines):
            score = sum(self._idf[t] for t in q & self._toks[i])
            if line["stage"] == stage:
                score = score * 1.2 + 0.5
            if score > 0:
                scored.append((score, -i, line))
        scored.sort(reverse=True)
        return [line for _, _, line in scored[:k]]


@dataclass
class LoopMemory:
    """Append-only JSONL memory of loop events and chat turns."""

    path: Path = MEMORY_PATH
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def append(self, kind: str, data: dict[str, Any]) -> dict[str, Any]:
        record = {**data, "kind": kind, "at": time.time()}
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def load(self, limit: int = 400) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self._lock:
            rows = self.path.read_text("utf-8").splitlines()[-limit:]
        out = []
        for row in rows:
            try:
                out.append(json.loads(row))
            except json.JSONDecodeError:
                continue
        return out

    def summary(self) -> dict[str, Any]:
        rows = self.load()
        episodes = [r for r in rows if r["kind"] == "episode"]
        last = episodes[-1] if episodes else {}
        return {
            "episodes": len(episodes),
            "deaths": sum(1 for e in episodes if e.get("outcome") == "dead"),
            "exits": sum(1 for e in episodes if e.get("outcome") == "complete"),
            "kills": sum(int(e.get("kills", 0)) for e in episodes),
            "best_fitness": max((float(e.get("fitness", 0)) for e in episodes), default=None),
            "generation": last.get("generation"),
            "stage": last.get("stage", "intake"),
            "last": {k: last.get(k) for k in ("mission", "outcome", "kills", "fitness")} if last else None,
            "chat_turns": sum(1 for r in rows if r["kind"] == "chat"),
        }

    def recent_chat(self, n: int = 3) -> list[dict[str, Any]]:
        return [r for r in self.load() if r["kind"] == "chat"][-n:]


class Backend(Protocol):
    name: str

    def available(self) -> bool: ...

    def generate(self, messages: list[dict[str, str]]) -> str: ...


class OllamaBackend:
    """Local Ollama HTTP API; no network access beyond 127.0.0.1."""

    def __init__(self, model: str = OLLAMA_MODEL, url: str = OLLAMA_URL, timeout: float = 60) -> None:
        self.name = f"ollama:{model}"
        self.model, self.url, self.timeout = model, url.rstrip("/"), timeout

    def _post(self, path: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
        req = urllib.request.Request(
            self.url + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return data if isinstance(data, dict) else {}

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self.url + "/api/tags", timeout=2) as resp:
                names = {m.get("name", "").split(":")[0] for m in json.loads(resp.read()).get("models", [])}
            return self.model in names
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def generate(self, messages: list[dict[str, str]]) -> str:
        out = self._post("/api/chat", {
            "model": self.model, "messages": messages, "stream": False,
            "options": {"temperature": 0.6, "num_predict": 48, "repeat_penalty": 1.1},
        }, self.timeout)
        return two_sentences(str(out.get("message", {}).get("content", "")))


class SIChat:
    def __init__(self, backend: Backend | None = None, memory: LoopMemory | None = None,
                 corpus: dict[str, Any] | None = None) -> None:
        self.corpus = corpus or story_corpus.extract()
        problems = story_corpus.verify(self.corpus)
        if problems:
            raise ValueError(f"owner corpus failed verification: {problems[:3]}")
        self.retriever = Retriever(self.corpus)
        self.backend = backend if backend is not None else OllamaBackend()
        self.memory = memory or LoopMemory()

    def status(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "backend": self.backend.name, "model_ready": self.backend.available(),
                "corpus_lines": len(self.corpus["lines"]), "loop": self.memory.summary()}

    def record_episode(self, episode: dict[str, Any]) -> dict[str, Any]:
        keys = ("generation", "mission", "outcome", "kills", "fitness", "improved", "died", "stage", "seconds")
        clean = {k: episode.get(k) for k in keys if k in episode}
        clean["outcome"] = str(clean.get("outcome", ""))[:20]
        clean["stage"] = str(clean.get("stage", "intake"))[:20]
        return self.memory.append("episode", clean)

    def _messages(self, message: str, lines: list[dict[str, Any]], loop: dict[str, Any]) -> list[dict[str, str]]:
        notes = "\n".join(f"- {story_corpus.collapse(line['text']).replace('**', '').replace('`', '')}" for line in lines)
        situation = self.situation(loop.get("game_now") or {})
        msgs = [{"role": "system", "content": f"{PERSONA}\n\nHidden briefing notes:\n{notes}\n\n"
                 f"Loop telemetry: {json.dumps(loop, ensure_ascii=False)}\n\n"
                 f"Situation right now (the only true game facts): {situation}"}]
        # Only the player's earlier questions are replayed; replaying generated replies
        # let a small model reinforce its own invented details.
        earlier = [t.get("message", "") for t in self.memory.recent_chat() if t.get("message") != "[episode]"]
        if earlier:
            msgs[0]["content"] += "\nPlayer asked earlier: " + " | ".join(earlier)
        msgs.append({"role": "user", "content": message})
        return msgs

    @staticmethod
    def situation(facts: dict[str, Any]) -> str:
        """Plain-English rendering of the sanitized game facts for a small model."""
        if not facts:
            return "No live game facts supplied."
        goal = str(facts.get("autopilot_goal", "")).split(":")[-1] or "unknown"
        parts = [f"Mission {facts.get('mission', '?')}.", f"Current objective: {goal}."]
        if "hp" in facts:
            parts.append(f"Health {facts['hp']}.")
        if "bullets" in facts or "shells" in facts:
            parts.append(f"Ammo: {facts.get('bullets', 0)} bullets, {facts.get('shells', 0)} shells.")
        if "enemies_left" in facts:
            parts.append(f"Enemies left: {facts['enemies_left']}.")
        for colour in ("red", "blue"):
            if f"{colour}_clearance" in facts:
                held = "held" if facts[f"{colour}_clearance"] else "NOT held"
                parts.append(f"{colour.title()} clearance {held}.")
        if "boss_down" in facts:
            parts.append("Boss defeated." if facts["boss_down"] else "Boss not defeated.")
        return " ".join(parts)

    def grounded(self, text: str, facts: dict[str, Any], known: str = "") -> bool:
        """Reject repeats, claimed clearances the player lacks, and numbers absent from the facts."""
        low = text.lower()
        if degenerate(text):
            return False
        allowed = set(re.findall(r"\d+", json.dumps(facts) + " " + known))
        if any(n not in allowed for n in re.findall(r"\d+", low)):
            return False
        last = [t.get("text", "") for t in self.memory.recent_chat(1)]
        if last and last[0].strip().lower() == low.strip():
            return False
        for colour in ("red", "blue"):
            key = f"{colour}_clearance"
            if colour in low and key in facts and not facts[key]:
                return False
        return True

    @staticmethod
    def game_facts(game: dict[str, Any] | None) -> dict[str, Any]:
        """Keep only short scalar facts from the caller's read-only game snapshot."""
        out: dict[str, Any] = {}
        for key, value in list((game or {}).items())[:16]:
            if not re.fullmatch(r"[a-z_]{1,24}", str(key)):
                continue
            if isinstance(value, bool) or (isinstance(value, (int, float)) and math.isfinite(value)):
                out[key] = value
            elif isinstance(value, str):
                out[key] = value[:40]
        return out

    def reply(self, message: str, view: str = "game", event: dict[str, Any] | None = None,
              game: dict[str, Any] | None = None) -> dict[str, Any]:
        message = (message or "").strip()[:MAX_MESSAGE]
        if event:
            self.record_episode(event)
        loop = self.memory.summary()
        facts = self.game_facts(game)
        if facts:
            loop = {**loop, "game_now": facts}
        stage = (event or {}).get("stage") or loop["stage"]
        prompt = message or (
            f"Radio the player one line about the episode that just ended: {json.dumps(event or loop.get('last'))}."
        )
        lines = self.retriever.search(prompt + " " + stage, stage=stage)
        if not lines:
            lines = self.retriever.search(stage, stage=stage)
        sources = [{"id": ln["id"], "cite": f"{ln['source']}:{ln['line_start']}", "sha256": ln["sha256"]}
                   for ln in lines]
        text, kind, error = "", "generated", None
        if self.backend.available():
            try:
                for _attempt in range(2):
                    text = self.backend.generate(self._messages(prompt, lines, loop))
                    if self.grounded(text, facts, json.dumps(loop) + " " + prompt):
                        break
                    text, error = "", "ungrounded"
            except (urllib.error.URLError, OSError, ValueError) as exc:
                error = type(exc).__name__
        if not text and error == "ungrounded" and facts:
            # The model drifted from the live game state; report that state plainly instead.
            kind, text, sources = "telemetry", self.situation(facts), []
        if not text:
            # Fallback keeps Level 1 behaviour: one verbatim owner line, never paraphrased.
            kind = "owner"
            text = story_corpus.collapse(lines[0]["text"]) if lines else "Channel quiet. No matching owner line."
            sources = sources[:1]
        result = {
            "schema": SCHEMA, "kind": kind,
            "label": LABELS[kind],
            "text": text, "model": self.backend.name if kind == "generated" else None,
            "stage": stage, "view": view, "sources_hidden": view == "game", "sources": sources, "error": error,
        }
        self.memory.append("chat", {"message": message or "[episode]", "text": text, "reply_kind": kind,
                                    "stage": stage, "sources": [s["id"] for s in sources]})
        return result


CHATBOX_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>VessellFramework SI Chat</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{margin:0;background:#0b0f0c;color:#cfe;font:14px/1.45 system-ui,sans-serif;display:flex;flex-direction:column;height:100vh}
header{padding:10px 14px;background:#132;border-bottom:1px solid #2a4}#status{font-size:12px;color:#8a8}
#log{flex:1;overflow-y:auto;padding:12px 14px}.m{margin:8px 0;max-width:760px}.you{color:#9cf}.si{color:#cfc}.owner{color:#ffd27a}
.tag{font-size:11px;color:#7a7}details{font-size:12px;color:#8a8}form{display:flex;border-top:1px solid #2a4}
input{flex:1;background:#020;color:#cfe;border:0;padding:12px;font:inherit}button{background:#2a4;color:#012;border:0;padding:0 18px;font-weight:bold}</style>
</head><body><header><b>VessellFramework // SI CHAT</b><div id="status">connecting…</div></header>
<div id="log"></div><form id="f"><input id="q" maxlength="500" placeholder="Ask SI about the loop, the doctrine, the next objective" autocomplete="off"><button>SEND</button></form>
<script>
const log=document.getElementById('log'),q=document.getElementById('q'),st=document.getElementById('status');
function add(cls,who,text,extra){const d=document.createElement('div');d.className='m '+cls;const b=document.createElement('b');b.textContent=who+': ';d.append(b,document.createTextNode(text));if(extra)d.append(extra);log.append(d);log.scrollTop=log.scrollHeight;}
async function status(){const s=await (await fetch('/status')).json();const l=s.loop;st.textContent=s.backend+(s.model_ready?' ready':' offline (owner-text fallback)')+' · '+s.corpus_lines+' hidden source lines · episodes '+l.episodes+' · exits '+l.exits+' · deaths '+l.deaths+' · stage '+l.stage;}
document.getElementById('f').onsubmit=async e=>{e.preventDefault();const m=q.value.trim();if(!m)return;q.value='';add('you','YOU',m);
const r=await (await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m,view:'framework'})})).json();
const det=document.createElement('details');const sm=document.createElement('summary');sm.textContent=r.label+' · sources ('+r.sources.length+')';det.append(sm);
r.sources.forEach(s=>{const p=document.createElement('div');p.textContent=s.cite+'  sha256:'+s.sha256.slice(0,12);det.append(p);});
add(r.kind==='owner'?'owner':'si',r.kind==='owner'?'AUTHOR':r.kind==='telemetry'?'LOOP':'SI',r.text,det);status();};
status();setInterval(status,10000);
</script></body></html>"""


def make_handler(chat: SIChat) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "VessellSIChat/1"

        def log_message(self, fmt: str, *args: Any) -> None:  # quiet
            return

        def _cors(self) -> None:
            origin = self.headers.get("Origin", "")
            if ALLOWED_ORIGINS.match(origin):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data: Any) -> None:
            self._send(code, json.dumps(data, ensure_ascii=False).encode())

        def do_OPTIONS(self) -> None:
            self._send(204, b"")

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                self._send(200, CHATBOX_HTML.encode(), "text/html; charset=utf-8")
            elif self.path == "/status":
                self._json(200, chat.status())
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            origin = self.headers.get("Origin")
            if origin and not ALLOWED_ORIGINS.match(origin):
                return self._json(403, {"error": "origin not allowed"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > 8192:
                return self._json(413, {"error": "too large"})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                body = None
            if not isinstance(body, dict):
                return self._json(400, {"error": "invalid json"})
            event = body.get("event") if isinstance(body.get("event"), dict) else None
            if self.path == "/chat":
                view = "framework" if body.get("view") == "framework" else "game"
                game = body.get("game") if isinstance(body.get("game"), dict) else None
                self._json(200, chat.reply(str(body.get("message", "")), view=view, event=event, game=game))
            elif self.path == "/event" and event:
                self._json(200, chat.record_episode(event))
            else:
                self._json(404, {"error": "not found"})

    return Handler


def setup_model() -> int:
    """Verify the pinned GGUF and register it with the local Ollama daemon."""
    gguf = MODEL_DIR / GGUF_NAME
    if not gguf.is_file():
        print(f"missing {gguf}; download Qwen/Qwen2.5-0.5B-Instruct-GGUF/{GGUF_NAME} first")
        return 1
    digest = story_corpus.sha256(gguf.read_bytes())
    if digest != GGUF_SHA256:
        print(f"hash mismatch for {gguf}: {digest}")
        return 1
    modelfile = MODEL_DIR / "Modelfile"
    modelfile.write_text(f"FROM ./{GGUF_NAME}\nPARAMETER temperature 0.7\nPARAMETER num_ctx 4096\n", "utf-8")
    return subprocess.call(["ollama", "create", OLLAMA_MODEL, "-f", str(modelfile)], cwd=MODEL_DIR)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vessell-chat", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="verify the pinned GGUF and register it with Ollama")
    sv = sub.add_parser("serve", help="serve the chatbox and game chat API on localhost")
    sv.add_argument("--port", type=int, default=8790)
    ask = sub.add_parser("ask", help="ask one question from the terminal")
    ask.add_argument("message")
    sub.add_parser("status")
    args = ap.parse_args(argv)
    if args.cmd == "setup":
        return setup_model()
    chat = SIChat()
    if args.cmd == "status":
        print(json.dumps(chat.status(), indent=2))
    elif args.cmd == "ask":
        r = chat.reply(args.message, view="framework")
        print(f"[{r['label']}] {r['text']}")
        for s in r["sources"]:
            print(f"  source {s['cite']}")
    else:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(chat))
        print(f"SI chat on http://127.0.0.1:{args.port}/  backend={chat.backend.name} ready={chat.backend.available()}")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
