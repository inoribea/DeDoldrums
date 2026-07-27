"""Telegram long-polling adapter backed by the ResearchAgent SSE bridge."""

import asyncio
import json
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx  # type: ignore[reportMissingImports]


BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://127.0.0.1:14168").rstrip("/")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API_URL = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""


def _bridge_headers() -> dict[str, str]:
    api_key = os.environ.get("BRIDGE_API_KEY")
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


async def _telegram(client: httpx.AsyncClient, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(f"{API_URL}/{method}", json=payload)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "Telegram API request failed"))
    return data["result"]


async def _stream(client: httpx.AsyncClient, sid: str) -> AsyncIterator[dict[str, Any]]:
    async with client.stream("GET", f"{BRIDGE_URL}/session/{sid}/stream", headers=_bridge_headers(), timeout=None) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                yield json.loads(line[6:])


def _brief(event: dict[str, Any]) -> str:
    if event.get("brief"):
        return str(event["brief"])
    findings = event.get("findings", [])
    return "\n\n".join(str(item.get("content") or item.get("data") or item) for item in findings) or "研究已完成。"


async def handle_question(client: httpx.AsyncClient, chat_id: int, question: str) -> None:
    created = await client.post(f"{BRIDGE_URL}/session/new", headers=_bridge_headers(), json={"question": question})
    created.raise_for_status()
    sid = created.json()["sessionId"]
    started = await client.post(f"{BRIDGE_URL}/session/{sid}/question", headers=_bridge_headers(), json={"question": question})
    started.raise_for_status()

    status = await _telegram(client, "sendMessage", {"chat_id": chat_id, "text": "🔍 正在发现研究视角..."})
    status_id = status["message_id"]
    try:
        async for event in _stream(client, sid):
            event_type = event.get("type")
            if event_type == "stage_change":
                text = f"📊 Stage {event.get('stage')}: {event.get('description', '研究中')}"
                await _telegram(client, "editMessageText", {"chat_id": chat_id, "message_id": status_id, "text": text})
            elif event_type == "complete":
                text = _brief(event)[:4000]
                await _telegram(client, "editMessageText", {"chat_id": chat_id, "message_id": status_id, "text": text})
            elif event_type == "error":
                await _telegram(client, "editMessageText", {"chat_id": chat_id, "message_id": status_id, "text": f"研究失败：{event.get('message', '未知错误')}"})
            elif event_type == "done":
                return
    except (httpx.HTTPError, json.JSONDecodeError, RuntimeError) as exc:
        await _telegram(client, "editMessageText", {"chat_id": chat_id, "message_id": status_id, "text": f"研究连接失败：{exc}"})


async def poll() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    offset: int | None = None
    async with httpx.AsyncClient(timeout=35) as client:
        while True:
            payload: dict[str, Any] = {"timeout": 30, "allowed_updates": ["message"]}
            if offset is not None:
                payload["offset"] = offset
            updates = await _telegram(client, "getUpdates", payload)
            if not isinstance(updates, list):
                raise RuntimeError("Telegram getUpdates returned an invalid response")
            for update in updates:
                if not isinstance(update, dict):
                    continue
                update_id = update.get("update_id")
                if not isinstance(update_id, int):
                    continue
                offset = update_id + 1
                message = update.get("message") or {}
                text = str(message.get("text") or "").strip()
                chat_id = (message.get("chat") or {}).get("id")
                if not chat_id or not text:
                    continue
                if text == "/start":
                    await _telegram(client, "sendMessage", {"chat_id": chat_id, "text": "你好！直接发送研究问题，我会返回多视角研究简报。"})
                elif not text.startswith("/"):
                    asyncio.create_task(handle_question(client, chat_id, text))


if __name__ == "__main__":
    asyncio.run(poll())
