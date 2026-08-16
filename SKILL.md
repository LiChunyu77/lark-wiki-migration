---
name: lark-wiki-migration
version: 1.0.0
description: "迁移飞书知识库：当用户需要把一个飞书 wiki 知识库的内容完整迁移到另一个飞书 wiki 时使用。支持输入源 wiki 链接和目标 wiki 链接，自动扫描、迁移并返回结果。"
metadata:
  requires:
    bins: ["lark-cli", "lark-wiki-migrate", "python3"]
---

# 飞书知识库迁移

> **前置条件：** 当前登录的 `lark-cli` 账号必须同时拥有：
> - 源知识库的「读取文档内容」权限
> - 目标知识库的「创建文档」权限
>
> 安装本仓库后，会同时获得一个 CLI 工具 `lark-wiki-migrate` 和一个 Claude Code skill。

## 功能

将源飞书 wiki 知识库的全部 docx 文档递归迁移到目标飞书 wiki 的指定父节点下。

迁移原理：
- 用 `lark-cli docs +fetch` 读取源文档 XML 内容
- 用 `lark-cli docs +create --doc-format xml` 在目标知识库原样创建文档
- 得到的是原生 docx，格式和层级都能保留

## 触发方式

当用户说类似以下的话时触发：
- "把 https://xxx.feishu.cn/wiki/ABC 迁到 https://yyy.feishu.cn/wiki/DEF"
- "迁移飞书知识库"
- "备份 wiki"
- "wiki migration"

## 使用方法

运行 CLI 工具：

```bash
lark-wiki-migrate "<source_wiki_url>" "<target_wiki_url>"
```

示例：

```bash
lark-wiki-migrate \
  "https://my.feishu.cn/wiki/SOURCE" \
  "https://my.feishu.cn/wiki/TARGET"
```

## 常用选项

```bash
lark-wiki-migrate <source> <target> --dry-run    # 只扫描，不创建
lark-wiki-migrate <source> <target> --yes        # 跳过确认
```

## 执行流程

1. **解析 URL**：从源/目标 wiki 链接中提取 `node_token`
2. **查询元数据**：用 `lark-cli wiki +node-get` 获取 `space_id` 和标题
3. **创建工作目录**：默认在 `~/lark-wiki-migrations/`
4. **扫描源结构**：递归列出所有子文档，保存为 `source_tree.json`
5. **执行迁移**：逐篇 `docs +fetch` → `docs +create`，保存 `migration_state.json`
6. **汇报结果**：输出迁移节点数、失败项、工作目录

## 输出文件

工作目录下会生成：
- `source_tree.json`：源知识库树形结构
- `migration_state.json`：源 node → 目标 node 映射，支持断点续传
- `manifest.json`：本次迁移的源/目标元数据

## 断点续传

如果中途失败，重新运行同一命令即可：
- 已迁移的节点会跳过
- 失败项保留在 `migration_state.json` 的 `failed` 列表中

## 注意事项

- 迁移的是 docx 文档，文档内嵌入的电子表格、多维表格、画板等对象不会被完整迁移
- 文档中的图片、附件通常会保留，但受限资源可能失败
- 每次迁移会创建独立工作目录，不会覆盖旧的迁移结果
- 如需重新全量迁移，删除对应工作目录后重新运行即可
- 本工具不会收集、上传或存储任何飞书登录凭证
- 请确保你拥有源/目标知识库的合法权限，并遵守飞书开放平台使用条款
