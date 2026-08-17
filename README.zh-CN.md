[English](README.md) | 中文

# Lark Wiki Migration

一个跨 AI 产品的飞书知识库迁移工具。输入源 wiki 链接和目标 wiki 链接，自动把源知识库的全部 docx 文档原样迁移到目标位置。

支持通过以下方式调用：
- **CLI**：`lark-wiki-migrate <source> <target>`
- **Claude Code skill**：自然语言触发
- **MCP Server**：任何支持 MCP 的 AI 产品（Codex、Workbuddy 等）

## 前置条件

1. 安装 [lark-cli](https://open.larksuite.com/document/tools/home) 并登录：
   ```bash
   lark-cli auth login
   ```
2. 当前登录账号必须同时拥有：
   - 源知识库的「读取文档内容」权限
   - 目标知识库的「创建文档」权限

## 安装

```bash
git clone https://github.com/LiChunyu77/lark-wiki-migration.git
cd lark-wiki-migration
./install.sh
```

`install.sh` 会：
- 把 `lark-wiki-migrate` 命令 symlink 到 `~/.local/bin`
- 如果检测到 `~/.claude/skills`，自动安装 Claude Code skill

安装完成后，确保 `~/.local/bin` 在你的 PATH 里：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## CLI 使用

```bash
# 迁移
lark-wiki-migrate "https://my.feishu.cn/wiki/SOURCE" "https://my.feishu.cn/wiki/TARGET"

# 先预览，不真正创建
lark-wiki-migrate "https://my.feishu.cn/wiki/SOURCE" "https://my.feishu.cn/wiki/TARGET" --dry-run

# 跳过确认
lark-wiki-migrate "https://my.feishu.cn/wiki/SOURCE" "https://my.feishu.cn/wiki/TARGET" --yes
```

## Claude Code 使用

安装后重启 Claude Code，然后说：

> 把 https://my.feishu.cn/wiki/SOURCE 迁到 https://my.feishu.cn/wiki/TARGET

Claude 会自动调用 `lark-wiki-migrate` 并返回结果。

## MCP Server 使用

任何支持 MCP 的 AI 客户端都可以接入。

1. 配置 MCP server：
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

2. AI 客户端会暴露一个 `migrate_feishu_wiki` 工具，接收：
   - `source`：源 wiki URL 或 token
   - `target`：目标 wiki URL 或 token
   - `dry_run`：可选，只扫描不创建

## 工作原理

- `lark-cli docs +fetch` 读取源文档 XML
- `lark-cli docs +create --doc-format xml` 在目标 wiki 下创建原生 docx
- 递归遍历源知识库树形结构，保持层级关系

## 输出

每次迁移会创建一个独立工作目录，默认在 `~/lark-wiki-migrations/`：

```
~/lark-wiki-migrations/
└── wiki-migration-<slug>-<timestamp>/
    ├── manifest.json
    ├── source_tree.json
    └── migration_state.json
```

- `source_tree.json`：源知识库结构
- `migration_state.json`：断点续传状态
- `manifest.json`：本次迁移元数据

## 环境变量

```bash
export LARK_WIKI_MIGRATION_DIR=~/my-migrations   # 自定义工作目录基路径
```

## 注意事项

- 迁移的是 docx 文档，嵌入的电子表格、多维表格、画板等对象不会被完整迁移
- 图片、附件通常会保留，但受限资源可能失败
- 工具只使用本机 `lark-cli` 的登录态，不会收集、上传或存储任何凭证
- 请确保你拥有源/目标知识库的合法权限
- 本工具适用于你已经拥有「读取」权限但缺少「复制/导出」入口的场景，不应用于绕过明确禁止你访问的内容
- 使用本工具需遵守飞书开放平台使用条款和所在组织的知识产权规定

## License

MIT
