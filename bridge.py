"""aiohttp HTTP + SSE bridge for ResearchAgent platform adapters.

Serves both the REST/SSE API and the built-in web frontend locally,
so ``python bridge.py`` gives you a complete research station at
http://127.0.0.1:18765 without any external deployment.
"""

import asyncio
import json
import logging
import mimetypes
import os
import pathlib
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

from aiohttp import web  # type: ignore[reportMissingImports]

try:  # Support direct script execution as documented by the project guide.
    from .agent_loop import ResearchHandler, research_loop  # pyright: ignore[reportMissingImports]
    from .config import get_router_config
    from .llm import LLMRouter
    from .memory import MemoryStore
    from .tools import do_challenge, do_crystallize, do_explore, do_reflect  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - direct script execution path.
    from agent_loop import ResearchHandler, research_loop  # pyright: ignore[reportMissingImports]
    from config import get_router_config
    from llm import LLMRouter
    from memory import MemoryStore
    from tools import do_challenge, do_crystallize, do_explore, do_reflect  # pyright: ignore[reportMissingImports]

# Path to the built-in web frontend shipped alongside bridge.py.
_FRONTEND_DIR = pathlib.Path(__file__).resolve().parent / "vercel"


def _new_llm_client():
    return LLMRouter(get_router_config())


@dataclass
class ResearchSession:
    """State owned by one client-visible research session."""

    sid: str
    question: str
    memory: Any = field(default_factory=lambda: MemoryStore("memory/"))
    handler: Any = None
    messages: list[str] = field(default_factory=list)
    sse_queue: asyncio.Queue[str] | None = None
    done: bool = False
    thread: threading.Thread | None = None
    loop: asyncio.AbstractEventLoop | None = None
    cancelled: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        self.handler = ResearchHandler(self.question, self.memory, _new_llm_client())

    def add_event(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Record an event and safely publish it into the aiohttp event loop."""
        message = json.dumps({"type": event_type, **(data or {})}, ensure_ascii=False)
        with self.lock:
            self.messages.append(message)
            queue, loop = self.sse_queue, self.loop
        if queue is not None and loop is not None and not loop.is_closed():
            asyncio.run_coroutine_threadsafe(queue.put(message), loop)


class ResearchBridge:
    """Owns all sessions and exposes the bridge's REST/SSE endpoints."""

    def __init__(self) -> None:
        self.sessions: dict[str, ResearchSession] = {}
        self.memory = MemoryStore("memory/")

    @staticmethod
    async def _json_body(request: web.Request) -> dict[str, Any] | None:
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return None
        return body if isinstance(body, dict) else None

    async def handle_session_new(self, request: web.Request) -> web.Response:
        body = await self._json_body(request)
        question = str((body or {}).get("question", "")).strip()
        if not question:
            return web.json_response({"error": "question is required"}, status=400)
        sid = f"rs_{uuid.uuid4().hex[:12]}"
        self.sessions[sid] = ResearchSession(sid=sid, question=question)
        host = request.headers.get("Host", "")
        return web.json_response({"sessionId": sid, "question": question, "bridgeUrl": f"http://{host}"})

    async def handle_session_question(self, request: web.Request) -> web.Response:
        session = self.sessions.get(request.match_info["sid"])
        if session is None:
            return web.json_response({"error": "session not found"}, status=404)
        if session.thread is not None and session.thread.is_alive():
            return web.json_response({"error": "research already running"}, status=409)

        body = await self._json_body(request)
        question = str((body or {}).get("question", "")).strip()
        if question:
            session.question = question
            session.handler = ResearchHandler(question, session.memory, _new_llm_client())
        session.done = False
        session.cancelled.clear()
        session.thread = threading.Thread(target=self._run_research, args=(session,), daemon=True)
        session.thread.start()
        return web.json_response({"status": "started", "sessionId": session.sid})

    def _run_research(self, session: ResearchSession) -> None:
        """Run blocking research in a worker thread and translate outcomes to SSE events."""
        logger = logging.getLogger("bridge")
        def on_status(msg: str) -> None:
            session.add_event("status", {"message": msg})
        try:
            session.add_event("stage_change", {"stage": 0, "description": self._stage_name(0)})
            if session.cancelled.is_set():
                return
            logger.info("Starting research: %s", session.question[:80])
            brief = asyncio.run(research_loop(_new_llm_client(), session.question, max_turns=50, on_status=on_status))
            logger.info("Research completed — brief: %d chars, findings: %d",
                        len(brief), len(getattr(session.handler, "findings", [])))
            if len(brief) < 50:
                logger.warning("Brief is suspiciously short: %r", brief)
            if session.cancelled.is_set():
                return
            session.add_event("stage_change", {"stage": 3.5, "description": self._stage_name(3.5)})
            session.add_event("challenge_result", {
                "results": getattr(session.handler, "adversarial_results", {}),
                "status": "completed",
            })
            session.add_event("stage_change", {"stage": 4, "description": self._stage_name(4)})
            session.add_event("finding", {"content": brief})
            session.add_event("complete", {
                "brief": brief,
                "findings": getattr(session.handler, "findings", [])[-5:],
                "confidence": getattr(session.handler, "confidence_scores", {}),
            })
            session.memory.archive_session(session.question, [{"final_brief": brief}])
        except Exception as exc:  # The event stream remains usable after a failed run.
            logger.error("Research failed: %s", exc, exc_info=True)
            session.add_event("error", {"message": str(exc)})
        finally:
            session.done = True

    async def handle_session_stream(self, request: web.Request) -> web.StreamResponse:
        session = self.sessions.get(request.match_info["sid"])
        if session is None:
            return web.json_response({"error": "session not found"}, status=404)

        response = web.StreamResponse(headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        })
        await response.prepare(request)
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str] = asyncio.Queue()
        with session.lock:
            session.loop, session.sse_queue = loop, queue
            history = list(session.messages)
            done = session.done

        try:
            for message in history:
                await response.write(f"data: {message}\n\n".encode("utf-8"))
            while not done:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    await response.write(f"data: {message}\n\n".encode("utf-8"))
                except asyncio.TimeoutError:
                    await response.write(b": heartbeat\n\n")
                with session.lock:
                    done = session.done and queue.empty()
            await response.write(b"data: {\"type\":\"done\"}\n\n")
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            with session.lock:
                if session.sse_queue is queue:
                    session.sse_queue = None
                    session.loop = None
        return response

    async def handle_session_history(self, request: web.Request) -> web.Response:
        session = self.sessions.get(request.match_info["sid"])
        if session is None:
            return web.json_response({"error": "session not found"}, status=404)
        with session.lock:
            return web.json_response({"done": session.done, "messages": session.messages})

    async def handle_session_cancel(self, request: web.Request) -> web.Response:
        session = self.sessions.get(request.match_info["sid"])
        if session is None:
            return web.json_response({"error": "session not found"}, status=404)
        session.cancelled.set()
        setattr(session.handler, "should_exit", True)
        session.done = True
        session.add_event("error", {"message": "research cancelled"})
        return web.json_response({"status": "cancelled", "sessionId": session.sid})

    async def handle_list_sessions(self, request: web.Request) -> web.Response:
        return web.json_response({"sessions": [
            {"sessionId": item.sid, "question": item.question, "done": item.done}
            for item in self.sessions.values()
        ]})

    @staticmethod
    def _stage_name(stage: int | float) -> str:
        names = {-1: "初始化", 0: "动态视角发现", 1: "多视角扫描", 2: "矛盾映射",
                 3: "综合合成", 3.5: "对抗验证闸门", 4: "同行评审"}
        return names.get(stage, f"Stage {stage}")


def _build_frontend_routes(bridge: ResearchBridge) -> list[web.RouteDef]:
    """Return routes for the built-in web frontend and its /api aliases."""
    routes: list[web.RouteDef] = []

    # --- Static frontend files (served only when the directory exists) ---
    if _FRONTEND_DIR.is_dir():
        for fpath in _FRONTEND_DIR.rglob("*"):
            if not fpath.is_file() or fpath.name.startswith("."):
                continue
            rel = "/" + str(fpath.relative_to(_FRONTEND_DIR)).replace("\\", "/")
            content = fpath.read_bytes()
            content_type, _ = mimetypes.guess_type(str(fpath))
            routes.append(
                web.route("GET", rel, lambda req, c=content, ct=content_type: web.Response(
                    body=c, content_type=ct or "application/octet-stream",
                ))
            )
        # Root → index.html
        index = _FRONTEND_DIR / "index.html"
        if index.is_file():
            index_bytes = index.read_bytes()
            routes.append(
                web.route("GET", "/", lambda req, b=index_bytes: web.Response(
                    body=b, content_type="text/html; charset=utf-8",
                ))
            )

    # --- /api aliases so the same frontend works with or without Vercel ---
    routes.append(web.route("POST", "/api/session/new", bridge.handle_session_new))
    routes.append(web.route("POST", "/api/session/{sid}/question", bridge.handle_session_question))
    routes.append(web.route("GET", "/api/research/stream", bridge.handle_session_stream))
    routes.append(web.route("GET", "/api/session/{sid}/history", bridge.handle_session_history))
    routes.append(web.route("POST", "/api/session/{sid}/cancel", bridge.handle_session_cancel))
    routes.append(web.route("GET", "/api/sessions", bridge.handle_list_sessions))

    return routes


def create_app() -> web.Application:
    api_key = os.environ.get("BRIDGE_API_KEY")
    logger = logging.getLogger("bridge")

    @web.middleware
    async def log_requests(request: web.Request, handler: Any) -> web.StreamResponse:
        start = time.monotonic()
        response = await handler(request)
        elapsed = (time.monotonic() - start) * 1000
        logger.info("%s %s → %s (%.0fms)", request.method, request.path, response.status, elapsed)
        return response

    @web.middleware
    async def require_api_key(request: web.Request, handler: Any) -> web.StreamResponse:
        if api_key and request.headers.get("Authorization") != f"Bearer {api_key}":
            return web.json_response({"error": "unauthorized"}, status=401)
        return await handler(request)

    app = web.Application(middlewares=[log_requests, require_api_key])
    bridge = ResearchBridge()
    app["bridge"] = bridge

    # Primary API endpoints.
    app.router.add_post("/session/new", bridge.handle_session_new)
    app.router.add_post("/session/{sid}/question", bridge.handle_session_question)
    app.router.add_get("/session/{sid}/stream", bridge.handle_session_stream)
    app.router.add_get("/session/{sid}/history", bridge.handle_session_history)
    app.router.add_post("/session/{sid}/cancel", bridge.handle_session_cancel)
    app.router.add_get("/sessions", bridge.handle_list_sessions)

    # Built-in web frontend + /api aliases.
    app.add_routes(_build_frontend_routes(bridge))

    return app


def main(handle_signals: bool = True) -> None:
    host = os.environ.get("BRIDGE_HOST", "127.0.0.1")
    port = int(os.environ.get("BRIDGE_PORT", "18765"))
    logger = logging.getLogger("bridge")
    logger.info("Starting ResearchAgent bridge on http://%s:%d", host, port)
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY is not set — LLM calls will fail")
    web.run_app(create_app(), host=host, port=port, handle_signals=handle_signals, print=lambda msg: logger.info(msg.rstrip()))


if __name__ == "__main__":
    main()
