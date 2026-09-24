from __future__ import annotations

import asyncio
import json
import socket
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_mcp_stdio_roundtrip(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="laya-") as directory:
        state_home = Path(directory)
        monkeypatch.setenv("XDG_STATE_HOME", directory)
        asyncio.run(_roundtrip(state_home))


async def _roundtrip(state_home):
    server = StdioServerParameters(command=sys.executable, args=["-m", "laya_agent.mcp_server"], env={"XDG_STATE_HOME": str(state_home)})
    events = state_home / "laya-agent/events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    (events.parent / "agent.sock").write_text("stale")
    (events.parent / "stats.json").write_text('{"decisions_by_policy":"corrupt"}')
    try:
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                assert "laya_test_decision for ambiguous test scope" in initialized.instructions
                tools = await session.list_tools()
                assert len(tools.tools) == 7
                assert all(t.annotations and t.annotations.readOnlyHint for t in tools.tools)
                events.write_bytes(b"x" * 1_000_001)
                result = await session.call_tool("laya_risk_check", {"action": "rm -rf /tmp/example"})
                assert '"requires_human":true' in str(result).replace(" ", "")
                with socket.socket(socket.AF_UNIX) as sock:
                    sock.connect(str(state_home / "laya-agent/agent.sock"))
                    sock.sendall(b'{"op":"stats"}\n')
                    assert json.loads(sock.recv(1024))["mcp_decisions"] == 1
                assert events.with_suffix(".jsonl.1").stat().st_size == 1_000_001

                def hook_decision(_):
                    with socket.socket(socket.AF_UNIX) as sock:
                        sock.connect(str(state_home / "laya-agent/agent.sock"))
                        sock.sendall(b'{"op":"decide","policy":"risk_check","state":{"action":"rm -rf /tmp/example"},"source":"hook"}\n')
                        return json.loads(sock.recv(1024))["requires_human"]

                with ThreadPoolExecutor(max_workers=8) as pool:
                    assert all(pool.map(hook_decision, range(16)))
                with socket.socket(socket.AF_UNIX) as sock:
                    sock.connect(str(state_home / "laya-agent/agent.sock"))
                    sock.sendall(b'{"op":"stats"}\n')
                    stats = json.loads(sock.recv(1024))
                    assert stats["hook_decisions"] == 16
                    assert stats["decisions_by_policy"]["risk_check"] == 17
    finally:
        path = state_home / "laya-agent/agent.sock"
        if path.exists():
            with socket.socket(socket.AF_UNIX) as sock:
                sock.connect(str(path))
                sock.sendall(b'{"op":"shutdown"}\n')
                json.loads(sock.recv(1024))
