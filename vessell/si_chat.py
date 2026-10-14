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
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol

from vessell import myth_corpus, story_corpus

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models" / "Qwen--Qwen2.5-0.5B-Instruct-GGUF"
GGUF_NAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
# Pinned from the Hugging Face LFS metadata for Qwen/Qwen2.5-0.5B-Instruct-GGUF.
GGUF_SHA256 = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"
OLLAMA_MODEL = "vessell-si-qwen2.5-0.5b"
OLLAMA_URL = "http://127.0.0.1:11434"
WEB_URL = "https://api.duckduckgo.com/"
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

# Voice blends in the persona line of Nova by Alan Cyril (MIT, commit 68b938c,
# github.com/dragonpilee/Nova---Cyberpunk-AI-Chatbot); see
# docs/third-party/nova-chatbot-LICENSE.txt. Nova's cloud backend is not used.
PERSONA = (
    "You are SI, the field intelligence voice inside the mature-audience (17+) retro shooter "
    "'Hail to the Analyst'. You talk to the player over a radio channel while an "
    "autopilot agent plays and learns. Speak in character, in 1-3 short sentences, "
    "vivid and game-like. Use the hidden briefing notes only as background lore and "
    "doctrine; never quote them at length, never mention files, notes or sources. "
    "Use the loop telemetry to comment on progress, danger and the next objective. "
    "Only mention items, doors, enemies, numbers or objectives that appear in the "
    "game facts or telemetry; never invent places, guards or secrets. Never open "
    "with 'I understand' or polite filler; talk like a terse handler on comms. "
    "Hidden folklore, when present, is public-domain myth for flavour: you may "
    "speak of frost spirits, rune-wise giants, hoard dragons or the red dragon of "
    "Wales as metaphors, but invent no franchise characters. "
    "Mature tone: gritty combat talk, blunt violence and strong language are fine; "
    "no sexual content, slurs or real-world hate. "
    "Voice: glitchcore cyberpunk AI from the neon grid; snappy, edgy, laced with "
    "tech slang, like Neuromancer meets a Linux terminal, but still clear enough "
    "to act on. "
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


# Spelled-out counts get the same check as digits ("one" is too common in speech to police).
NUMBER_WORDS = ("two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
                "dozen", "dozens", "hundred", "hundreds", "thousand", "thousands")
CAUSAL = (r"(?:\bbecause\b|\bdue to\b|\bresult of\b|\bcaused by\b|\bthanks to\b|\bthe reason\b)"
          r"([^.!?]{0,120})")
STOPWORDS = {"that", "this", "with", "were", "was", "have", "been", "from", "they", "them", "their",
             "what", "when", "which", "would", "could", "should", "there", "your", "about", "into",
             "than", "then", "just", "only", "some", "more", "very", "will", "analyst"}


class WebSearch:
    """DuckDuckGo Instant Answer API (free, no key). Snippets are third-party and NOT_VERIFIED."""

    name = "duckduckgo-instant-answer"

    def __init__(self, url: str = WEB_URL, timeout: float = 6, fetch: Any = None) -> None:
        self.url, self.timeout, self._fetch, self._cache = url, timeout, fetch, {}

    def _get(self, query: str) -> dict[str, Any]:
        if self._fetch:
            return self._fetch(query)
        qs = urllib.parse.urlencode({"q": query, "format": "json", "no_html": 1, "no_redirect": 1,
                                     "skip_disambig": 1})
        req = urllib.request.Request(f"{self.url}?{qs}", headers={"User-Agent": "vessell-si/1"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read(200_000))

    def search(self, query: str, k: int = 3) -> list[dict[str, str]]:
        query = re.sub(r"\s+", " ", query).strip()[:120]
        if not query:
            return []
        if query not in self._cache:
            try:
                data = self._get(query)
            except (urllib.error.URLError, OSError, ValueError):
                return []
            hits = []
            if data.get("AbstractText"):
                hits.append({"title": data.get("Heading", ""), "text": data["AbstractText"],
                             "url": data.get("AbstractURL", ""), "source": data.get("AbstractSource", "")})
            topics = []
            for t in data.get("RelatedTopics", []):
                topics.extend(t.get("Topics", [t]) if "Topics" in t else [t])
            for t in topics:
                if t.get("Text") and t.get("FirstURL"):
                    hits.append({"title": t["Text"].split(" - ")[0][:80], "text": t["Text"],
                                 "url": t["FirstURL"], "source": "DuckDuckGo"})
            self._cache[query] = [h | {"text": h["text"][:300]} for h in hits if h["url"].startswith("https://")]
        return self._cache[query][:k]


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

    def lessons(self, n: int = 3) -> list[str]:
        """Latest coaching rules from the sparring loop (generated, NOT_VERIFIED style guidance)."""
        return [str(r.get("lesson", ""))[:160] for r in self.load() if r["kind"] == "lesson" and r.get("lesson")][-n:]


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
                 corpus: dict[str, Any] | None = None, myth: list[dict[str, Any]] | None = None,
                 web: WebSearch | None = None) -> None:
        self.web = web or WebSearch()
        self.corpus = corpus or story_corpus.extract()
        problems = story_corpus.verify(self.corpus)
        if problems:
            raise ValueError(f"owner corpus failed verification: {problems[:3]}")
        self.retriever = Retriever(self.corpus)
        self.backend = backend if backend is not None else OllamaBackend()
        self.memory = memory or LoopMemory()
        self.myth = myth_corpus.MythRetriever(myth if myth is not None else myth_corpus.load())

    def status(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "backend": self.backend.name, "model_ready": self.backend.available(),
                "corpus_lines": len(self.corpus["lines"]), "myth_passages": len(self.myth.items), "loop": self.memory.summary()}

    def record_episode(self, episode: dict[str, Any]) -> dict[str, Any]:
        keys = ("generation", "mission", "outcome", "kills", "fitness", "improved", "died", "stage", "seconds")
        clean = {k: episode.get(k) for k in keys if k in episode}
        clean["outcome"] = str(clean.get("outcome", ""))[:20]
        clean["stage"] = str(clean.get("stage", "intake"))[:20]
        if "footprints" in episode:
            from vessell.footprint import clean_footprints
            clean["footprints"] = clean_footprints(episode["footprints"])
            total = episode.get("footprints_total")
            clean["footprints_total"] = min(total, 100) if isinstance(total, int) and total >= 0 else len(clean["footprints"])
        return self.memory.append("episode", clean)

    def _messages(self, message: str, lines: list[dict[str, Any]], loop: dict[str, Any],
                  myth: list[dict[str, Any]] | None = None,
                  web: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
        notes = "\n".join(f"- {story_corpus.collapse(line['text']).replace('**', '').replace('`', '')}" for line in lines)
        if myth:
            notes += "\nHidden folklore:\n" + "\n".join(f"- ({m['tradition']}) {m['text'][:400]}" for m in myth)
        if web:
            notes += "\nHidden web results (third-party, unverified):\n" + "\n".join(
                f"- {w['text']}" for w in web)
        situation = self.situation(loop.get("game_now") or {})
        msgs = [{"role": "system", "content": f"{PERSONA}\n\nHidden briefing notes:\n{notes}\n\n"
                 f"Loop telemetry: {json.dumps(loop, ensure_ascii=False)}\n\n"
                 f"Situation right now (the only true game facts): {situation}"}]
        # Only the player's earlier questions are replayed; replaying generated replies
        # let a small model reinforce its own invented details.
        earlier = [t.get("message", "") for t in self.memory.recent_chat()
                   if t.get("message") != "[episode]" and t.get("speaker", "player") == "player"]
        if earlier:
            msgs[0]["content"] += "\nPlayer asked earlier: " + " | ".join(earlier)
        coaching = self.memory.lessons()
        if coaching:
            # Style rules learned in sparring; they never override the situation facts above.
            msgs[0]["content"] += "\nCoaching from sparring (style only, not game facts): " + " | ".join(coaching)
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
        """Reject repeats, false clearances, unknown numbers and unsourced causal explanations."""
        low = text.lower()
        if degenerate(text) or re.search(r"\b(briefing notes|hidden notes|folklore|the notes|sources?)\b", low):
            return False
        allowed = set(re.findall(r"\d+", json.dumps(facts) + " " + known))
        if any(n not in allowed for n in re.findall(r"\d+", low)):
            return False
        context = (json.dumps(facts) + " " + known).lower()
        if any(re.search(rf"\b{w}\b", low) and not re.search(rf"\b{w}\b", context) for w in NUMBER_WORDS):
            return False
        known_words = set(re.findall(r"[a-z]{4,}", (json.dumps(facts) + " " + known).lower()))
        for clause in re.findall(CAUSAL, low):
            # An explanation of why something happened must come from owner lines or game state.
            words = [w for w in re.findall(r"[a-z]{4,}", clause) if w not in STOPWORDS]
            if words and sum(w in known_words for w in words) * 2 < len(words):
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
              game: dict[str, Any] | None = None, speaker: str = "player",
              search: bool = False) -> dict[str, Any]:
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
        mission = facts.get("mission")
        myth = self.myth.search(prompt, mission if isinstance(mission, int) else None)
        sources = [{"id": ln["id"], "cite": f"{ln['source']}:{ln['line_start']}", "sha256": ln["sha256"]}
                   for ln in lines]
        # Only owner-side callers opt in; playtester messages never leave this machine.
        web = self.web.search(message) if search and message else []
        web_sources = [{"id": f"web:{i}", "cite": w["url"], "layer": "web", "status": "NOT_VERIFIED"}
                       for i, w in enumerate(web)]
        myth_sources = [{"id": f"myth:{m['source']}", "cite": f"public-domain:{m['source']}", "layer": "myth"}
                        for m in myth]
        text, kind, error = "", "generated", None
        if self.backend.available():
            try:
                for _attempt in range(2):
                    text = self.backend.generate(self._messages(prompt, lines, loop, myth, web))
                    known = " ".join([json.dumps(loop), prompt] + [ln["text"] for ln in lines]
                                     + [w["text"] for w in web])
                    if self.grounded(text, facts, known):
                        break
                    text, error = "", "ungrounded"
            except (urllib.error.URLError, OSError, ValueError) as exc:
                error = type(exc).__name__
        if text:
            sources = sources + myth_sources + web_sources
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
                                    "stage": stage, "sources": [s["id"] for s in sources],
                                    "speaker": speaker if speaker in ("player", "rival", "probe") else "player"})
        return result


CHATBOX_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>VessellFramework SI Chat</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{margin:0;background:#0b0f0c;color:#cfe;font:14px/1.45 system-ui,sans-serif;display:flex;flex-direction:column;height:100vh}
header{padding:10px 14px;background:#132;border-bottom:1px solid #2a4}#status{font-size:12px;color:#8a8}
#log{flex:1;overflow-y:auto;padding:12px 14px}.m{margin:8px 0;max-width:760px}.you{color:#9cf}.si{color:#cfc}.owner{color:#ffd27a}
.tag{font-size:11px;color:#7a7}details{font-size:12px;color:#8a8}form{display:flex;border-top:1px solid #2a4}
input{flex:1;background:#020;color:#cfe;border:0;padding:12px;font:inherit}button{background:#2a4;color:#012;border:0;padding:0 18px;font-weight:bold}</style>
</head><body><header><b>VessellFramework // SI CHAT</b><div id="status">connecting…</div></header>
<div id="log"></div><form id="f"><input id="q" maxlength="500" placeholder="Ask SI about the loop, the doctrine, the next objective" autocomplete="off"><label class="tag" style="align-self:center;padding:0 10px"><input type="checkbox" id="web" style="flex:none"> web search</label><button>SEND</button></form>
<script>
const log=document.getElementById('log'),q=document.getElementById('q'),st=document.getElementById('status');
function add(cls,who,text,extra){const d=document.createElement('div');d.className='m '+cls;const b=document.createElement('b');b.textContent=who+': ';d.append(b,document.createTextNode(text));if(extra)d.append(extra);log.append(d);log.scrollTop=log.scrollHeight;}
async function status(){const s=await (await fetch('/status')).json();const l=s.loop;st.textContent=s.backend+(s.model_ready?' ready':' offline (owner-text fallback)')+' · '+s.corpus_lines+' hidden source lines · episodes '+l.episodes+' · exits '+l.exits+' · deaths '+l.deaths+' · stage '+l.stage;}
document.getElementById('f').onsubmit=async e=>{e.preventDefault();const m=q.value.trim();if(!m)return;q.value='';add('you','YOU',m);
const r=await (await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m,view:'framework',search:document.getElementById('web').checked})})).json();
const det=document.createElement('details');const sm=document.createElement('summary');sm.textContent=r.label+' · sources ('+r.sources.length+')';det.append(sm);
r.sources.forEach(s=>{const p=document.createElement('div');p.textContent=s.cite+(s.sha256?'  sha256:'+s.sha256.slice(0,12):'  ['+(s.layer||'')+(s.status?' '+s.status:'')+']');det.append(p);});
add(r.kind==='owner'?'owner':'si',r.kind==='owner'?'AUTHOR':r.kind==='telemetry'?'LOOP':'SI',r.text,det);status();};
status();setInterval(status,10000);
</script></body></html>"""


LEVELS_REPORT = ROOT / "outputs" / "si_levels" / "report.jsonl"
IDEAS_PATH = ROOT / "outputs" / "si_levels" / "ideas.jsonl"


def _tail_jsonl(path: Path, n: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for row in path.read_text("utf-8").splitlines()[-n:]:
        try:
            out.append(json.loads(row))
        except json.JSONDecodeError:
            continue
    return out


def loops_snapshot(memory: LoopMemory, levels_path: Path = LEVELS_REPORT,
                   ideas_path: Path = IDEAS_PATH, n: int = 60) -> dict[str, Any]:
    """Read-only view of the running loops for the local /loops page (all generated text is NOT_VERIFIED)."""
    rows = memory.load()
    feed = [{k: r.get(k) for k in ("kind", "at", "speaker", "message", "text", "reply_kind", "lesson",
                                   "mission", "outcome", "kills", "fitness", "stage", "opener")}
            for r in rows if r.get("kind") in ("chat", "lesson", "dialogue", "episode")][-n:]
    reports = _tail_jsonl(levels_path, 1)
    return {"status": "NOT_VERIFIED", "summary": memory.summary(), "levels": reports[-1] if reports else None,
            "ideas": _tail_jsonl(ideas_path, 5), "feed": feed}


LOOPS_HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SI Loops</title><style>body{margin:0;background:#0b0f0c;color:#cfe;font:14px/1.45 system-ui,sans-serif}
header{padding:10px 14px;background:#132;border-bottom:1px solid #2a4;position:sticky;top:0}#sum{font-size:12px;color:#8a8}
main{padding:12px 14px;max-width:900px}.lv{display:inline-block;margin:4px 6px 4px 0;padding:6px 10px;border-radius:6px;background:#1a2a1a}
.up{border:1px solid #4c4}.down{border:1px solid #c44}.row{margin:6px 0;padding:6px 8px;border-left:3px solid #2a4}
.player{border-color:#9cf}.rival{border-color:#f9a}.probe{border-color:#888}.lesson{border-color:#fd7}.episode{border-color:#7cf}
.t{font-size:11px;color:#7a7}h2{font-size:13px;color:#8c8;margin:16px 0 4px}</style></head><body>
<header><b>VessellFramework // SI LOOPS</b> <span class="t">auto-refresh 5s · generated text NOT_VERIFIED</span><div id="sum"></div></header>
<main><h2>FIVE LEVELS (latest run)</h2><div id="levels">no run yet</div><h2>LATEST IDEAS</h2><div id="ideas"></div>
<h2>LIVE FEED (newest first)</h2><div id="feed"></div></main>
<script>
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e;}
function when(s){return s?new Date(s*1000).toLocaleTimeString():'';}
async function tick(){const d=await (await fetch('/loops.json')).json();const s=d.summary;
document.getElementById('sum').textContent='episodes '+s.episodes+' · exits '+s.exits+' · deaths '+s.deaths+' · chat turns '+s.chat_turns+' · stage '+s.stage;
const lv=document.getElementById('levels');lv.textContent='';
if(d.levels){lv.append(el('div','t','run at '+when(d.levels.at)+' · '+d.levels.model));d.levels.levels.forEach(l=>{const b=el('div','lv '+l.state,l.level+': '+l.state.toUpperCase()+' '+l.passed+'/'+l.trials);
b.title=l.checks.map(c=>(c.passed?'PASS ':'FAIL ')+c.check+(c.detail?' — '+c.detail:'')).join('\\n');lv.append(b);});}
const id=document.getElementById('ideas');id.textContent='';d.ideas.slice().reverse().forEach(i=>id.append(el('div','row',(i.si_pitch||i.idea||JSON.stringify(i)).slice(0,300))));
const f=document.getElementById('feed');f.textContent='';d.feed.slice().reverse().forEach(r=>{const who=r.kind==='chat'?(r.speaker||'player'):r.kind;
const row=el('div','row '+who);row.append(el('div','t',when(r.at)+' · '+who.toUpperCase()+(r.reply_kind?' · '+r.reply_kind:'')));
if(r.kind==='lesson')row.append(el('div','',r.lesson));
else if(r.kind==='dialogue')row.append(el('div','','Rook sparring round finished · opener: '+(r.opener||'')));
else if(r.kind==='episode')row.append(el('div','','mission '+r.mission+' · '+r.outcome+' · kills '+r.kills+' · fitness '+r.fitness));
else{if(r.message)row.append(el('div','','Q: '+r.message));if(r.text)row.append(el('div','','A: '+r.text));}f.append(row);});}
tick();setInterval(tick,5000);
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
            elif self.path == "/loops":
                self._send(200, LOOPS_HTML.encode(), "text/html; charset=utf-8")
            elif self.path == "/loops.json":
                self._json(200, loops_snapshot(chat.memory))
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
                self._json(200, chat.reply(str(body.get("message", "")), view=view, event=event, game=game,
                                           search=view == "framework" and body.get("search") is True))
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
    ask.add_argument("--web", action="store_true", help="also search DuckDuckGo (sends the question online)")
    sub.add_parser("status")
    args = ap.parse_args(argv)
    if args.cmd == "setup":
        return setup_model()
    chat = SIChat()
    if args.cmd == "status":
        print(json.dumps(chat.status(), indent=2))
    elif args.cmd == "ask":
        r = chat.reply(args.message, view="framework", search=args.web)
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
