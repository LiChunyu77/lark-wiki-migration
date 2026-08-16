#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
SKILL_DIR="${HOME}/.claude/skills/lark-wiki-migration"

echo "Installing lark-wiki-migration..."

# Ensure ~/.local/bin exists
mkdir -p "$BIN_DIR"

# Symlink CLI tool
ln -sf "$REPO_DIR/lark_wiki_migrate.py" "$BIN_DIR/lark-wiki-migrate"
chmod +x "$BIN_DIR/lark-wiki-migrate"

# Ensure PATH contains ~/.local/bin
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "⚠️  ~/.local/bin is not in your PATH."
    echo "   Add this to your shell profile:"
    echo "     export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Install Claude Code skill if .claude/skills exists
if [ -d "$HOME/.claude" ]; then
    mkdir -p "$SKILL_DIR"
    cp "$REPO_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
    echo "Claude Code skill installed to $SKILL_DIR"
fi

echo ""
echo "✅ Installation complete."
echo "   CLI: lark-wiki-migrate <source> <target>"
echo "   Skill: restart Claude Code to use it."
