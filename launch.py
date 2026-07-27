"""Start the bridge and any configured platform adapters."""

import asyncio
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

try:
    from .bridge import main as bridge_main  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - direct script execution path.
    from bridge import main as bridge_main  # pyright: ignore[reportMissingImports]


ROOT = Path(__file__).resolve().parent


def _start_bridge() -> None:
    bridge_main(handle_signals=False)


async def _wait(processes: list[subprocess.Popen[bytes]]) -> None:
    if processes:
        await asyncio.gather(*(asyncio.to_thread(process.wait) for process in processes))


async def main() -> None:
    bridge_thread = threading.Thread(target=_start_bridge, name="research-bridge", daemon=True)
    bridge_thread.start()

    processes: list[subprocess.Popen[bytes]] = []
    adapters = {
        "TELEGRAM_BOT_TOKEN": ROOT / "adapters" / "telegram_bot.py",
        "DISCORD_BOT_TOKEN": ROOT / "adapters" / "discord_bot.py",
    }
    for env_name, script in adapters.items():
        if os.environ.get(env_name):
            processes.append(subprocess.Popen([sys.executable, str(script)], cwd=ROOT))

    try:
        await _wait(processes)
        if not processes:
            while bridge_thread.is_alive():
                await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
        await asyncio.gather(*(asyncio.to_thread(process.wait) for process in processes), return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
