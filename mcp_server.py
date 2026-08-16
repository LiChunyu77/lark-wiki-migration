#!/usr/bin/env python3
"""MCP server exposing lark-wiki-migration as a tool.

Run with:
    python3 mcp_server.py

Then configure your MCP client (Claude Code, Codex, Workbuddy, etc.) with:
    {
      "mcpServers": {
        "lark-wiki-migration": {
          "command": "python3",
          "args": ["/absolute/path/to/mcp_server.py"]
        }
      }
    }
"""
import asyncio
import json
import os
import sys

import mcp.types as types
import mcp.server.stdio
from mcp.server.lowlevel.server import Server, InitializationOptions

from lark_wiki_migrate import run_migration


async def main():
    async def on_list_tools(ctx, params):
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name="migrate_feishu_wiki",
                    title="Migrate Feishu Wiki",
                    description=(
                        "Migrate all docx documents from a source Feishu wiki "
                        "to a target Feishu wiki. The user must already be logged in "
                        "via lark-cli and have read access to the source and write "
                        "access to the target. Set dry_run=true to scan without creating documents."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": "Source Feishu wiki URL or node token",
                            },
                            "target": {
                                "type": "string",
                                "description": "Target Feishu wiki URL or parent node token",
                            },
                            "output_dir": {
                                "type": "string",
                                "description": "Optional working directory for logs and state",
                            },
                            "dry_run": {
                                "type": "boolean",
                                "description": "If true, only scan and report counts without creating documents",
                                "default": False,
                            },
                        },
                        "required": ["source", "target"],
                    },
                    annotations=types.ToolAnnotations(
                        destructive=True,
                        idempotent=False,
                        openWorld=False,
                    ),
                )
            ]
        )

    async def on_call_tool(ctx, params):
        args = params.arguments or {}
        source = args.get("source", "").strip()
        target = args.get("target", "").strip()
        output_dir = args.get("output_dir") or None
        dry_run = bool(args.get("dry_run", False))

        if not source or not target:
            return types.CallToolResult(
                is_error=True,
                content=[
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": "Both 'source' and 'target' are required."},
                            ensure_ascii=False,
                        ),
                    )
                ],
            )

        try:
            result = run_migration(
                source=source,
                target=target,
                output_dir=output_dir,
                dry_run=dry_run,
                yes=True,
            )
            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ],
            )
        except Exception as e:
            return types.CallToolResult(
                is_error=True,
                content=[
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": str(e)},
                            ensure_ascii=False,
                        ),
                    )
                ],
            )

    server = Server(
        name="lark-wiki-migration",
        version="1.0.0",
        title="Lark Wiki Migration",
        description="Migrate Feishu/Lark wiki documents between spaces.",
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="lark-wiki-migration",
                server_version="1.0.0",
                capabilities=types.ServerCapabilities(
                    tools=types.ToolsCapability(list_changed=False)
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
