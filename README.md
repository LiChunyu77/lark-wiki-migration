English | [中文](README.zh-CN.md)

# Lark Wiki Migration

A cross-AI-product migration tool for Feishu (Lark) wiki spaces. Give it a source wiki link and a target wiki link, and it migrates all docx documents from the source space to the target, preserving the tree structure.

Available through:
- **CLI**: `lark-wiki-migrate <source> <target>`
- **Claude Code skill**: triggered by natural language
- **MCP Server**: any MCP-compatible AI product (Codex, Workbuddy, etc.)

## Prerequisites

1. [Lark CLI](https://github.com/larksuite/cli) installed and configured:
   ```bash
   lark-cli config init
   ```
2. User authentication completed:
   ```bash
   lark-cli auth login --domain all
   ```
3. The logged-in account must have both:
   - **Read** permission on the source wiki space
   - **Create document** permission on the target wiki space

## Installation

```bash
git clone https://github.com/LiChunyu77/lark-wiki-migration.git
cd lark-wiki-migration
./install.sh
```

`install.sh` will:
- Symlink the `lark-wiki-migrate` command into `~/.local/bin`
- Automatically install the Claude Code skill if `~/.claude/skills` is detected

After installation, make sure `~/.local/bin` is in your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## CLI Usage

```bash
# Migrate
lark-wiki-migrate "https://my.feishu.cn/wiki/SOURCE" "https://my.feishu.cn/wiki/TARGET"

# Preview only, create nothing
lark-wiki-migrate "https://my.feishu.cn/wiki/SOURCE" "https://my.feishu.cn/wiki/TARGET" --dry-run

# Skip confirmation
lark-wiki-migrate "https://my.feishu.cn/wiki/SOURCE" "https://my.feishu.cn/wiki/TARGET" --yes
```

## Claude Code Usage

Restart Claude Code after installation, then say:

> Migrate https://my.feishu.cn/wiki/SOURCE to https://my.feishu.cn/wiki/TARGET

Claude will automatically invoke `lark-wiki-migrate` and return the result.

## MCP Server Usage

Works with any MCP-compatible AI client.

1. Configure the MCP server:
   ```json
   {
     "mcpServers": {
       "lark-wiki-migration": {
         "command": "python3",
         "args": ["/absolute/path/to/mcp_server.py"]
       }
     }
   }
   ```

2. The client will expose a `migrate_feishu_wiki` tool that accepts:
   - `source`: source wiki URL or token
   - `target`: target wiki URL or token
   - `dry_run`: optional, scan only without creating anything

## How It Works

- `lark-cli docs +fetch` reads the source document XML
- `lark-cli docs +create --doc-format xml` creates native docx documents under the target wiki
- Recursively walks the source wiki tree, preserving the hierarchy

## Output

Each migration creates a dedicated working directory under `~/lark-wiki-migrations/` by default:

```
~/lark-wiki-migrations/
└── wiki-migration-<slug>-<timestamp>/
    ├── manifest.json
    ├── source_tree.json
    └── migration_state.json
```

- `source_tree.json`: source wiki structure
- `migration_state.json`: resumable migration state
- `manifest.json`: metadata for this migration run

## Environment Variables

```bash
export LARK_WIKI_MIGRATION_DIR=~/my-migrations   # Custom working directory base path
```

## Notes

- Only docx documents are migrated; embedded spreadsheets, bitables, whiteboards, and similar objects are not fully migrated
- Images and attachments are usually preserved, but access-restricted resources may fail
- The tool only uses the local `lark-cli` login session; it does not collect, upload, or store any credentials
- The tool operates through official APIs and can only access content your account already has permission to access — it does not bypass any permission restrictions
- Compared with manually copying/exporting documents one by one, this tool supports batch migration, preserves the wiki hierarchy, and can resume interrupted migrations
- Make sure you have legitimate access to both the source and target wiki spaces
- Use of this tool must comply with the Feishu Open Platform terms of service and your organization's IP policies

## License

MIT
