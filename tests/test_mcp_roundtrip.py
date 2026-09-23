from __future__ import annotations

import asyncio
import json
import socket
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_mcp_stdio_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    async def run():
        server = StdioServerParameters(command=sys.executable, args=["-m", "laya_agent.mcp_server"], env={"XDG_STATE_HOME": str(tmp_path)})
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert len(tools.tools) == 7
                result = await session.call_tool("laya_risk_check", {"action": "rm -rf /tmp/example"})
                assert '"requires_human":true' in str(result).replace(" ", "")

    try:
        asyncio.run(run())
    finally:
        path = tmp_path / "laya-agent/agent.sock"
        if path.exists():
            with socket.socket(socket.AF_UNIX) as sock:
                sock.connect(str(path))
                sock.sendall(b'{"op":"shutdown"}\n')
                json.loads(sock.recv(1024))
