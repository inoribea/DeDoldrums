"""Discord adapter that relays messages through the ResearchAgent SSE bridge."""

import asyncio
import importlib
import json
import os
from typing import Any

import httpx  # type: ignore[reportMissingImports]


BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://127.0.0.1:14168").rstrip("/")
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")


def _bridge_headers() -> dict[str, str]:
    api_key = os.environ.get("BRIDGE_API_KEY")
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


async def _stream(client: httpx.AsyncClient, sid: str):
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


async def run() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    try:
        discord = importlib.import_module("discord")
    except ImportError as exc:
        raise RuntimeError("Install discord.py to run the Discord adapter") from exc

    intents = discord.Intents.default()
    intents.message_content = True
    bot = discord.Client(intents=intents)

    @bot.event
    async def on_ready() -> None:
        print(f"Discord adapter connected as {bot.user}")

    @bot.event
    async def on_message(message: Any) -> None:
        if message.author.bot or not message.content.strip():
            return
        question = message.content.strip()
        if question == "/start":
            await message.channel.send("Send a research question and I will return a multi-perspective brief.")
            return
        status = await message.channel.send(embed=discord.Embed(title="ResearchAgent", description="🔍 Discovering research lenses..."))
        try:
            async with httpx.AsyncClient() as client:
                created = await client.post(f"{BRIDGE_URL}/session/new", headers=_bridge_headers(), json={"question": question})
                created.raise_for_status()
                sid = created.json()["sessionId"]
                started = await client.post(f"{BRIDGE_URL}/session/{sid}/question", headers=_bridge_headers(), json={"question": question})
                started.raise_for_status()
                async for event in _stream(client, sid):
                    if event.get("type") == "stage_change":
                        embed = discord.Embed(title="ResearchAgent", description=f"Stage {event.get('stage')}: {event.get('description', 'Researching')}")
                        await status.edit(embed=embed)
                    elif event.get("type") == "complete":
                        brief = _brief(event)
                        embed = discord.Embed(title="Research brief", description=brief[:4096])
                        for index, finding in enumerate(event.get("findings", [])[:5], start=1):
                            embed.add_field(name=f"Finding {index}", value=str(finding)[:1024], inline=False)
                        await status.edit(embed=embed)
                    elif event.get("type") == "error":
                        await status.edit(embed=discord.Embed(title="Research failed", description=str(event.get("message", "Unknown error"))))
                    elif event.get("type") == "done":
                        return
        except (httpx.HTTPError, json.JSONDecodeError, RuntimeError) as exc:
            await status.edit(embed=discord.Embed(title="Research connection failed", description=str(exc)))

    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(run())
