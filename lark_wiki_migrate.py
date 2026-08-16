#!/usr/bin/env python3
"""Core migration logic and CLI for lark-wiki-migration."""
import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

__version__ = "1.0.0"

DEFAULT_BASE_DIR = Path.home() / "lark-wiki-migrations"
ENV_OUTPUT_DIR = "LARK_WIKI_MIGRATION_DIR"


def run_cmd(cmd, check=True, cwd=None):
    """Run a shell command and return parsed JSON if possible."""
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"CMD FAILED: {' '.join(cmd)}", file=sys.stderr)
        print(f"stderr: {result.stderr}", file=sys.stderr)
        if check:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}")
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout}


def check_lark_cli():
    """Verify lark-cli is installed and authenticated."""
    result = subprocess.run(["lark-cli", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "lark-cli not found. Please install it first: https://open.larksuite.com/document/tools/home"
        )

    auth = subprocess.run(["lark-cli", "auth", "status"], capture_output=True, text=True)
    if auth.returncode != 0:
        raise RuntimeError(
            "lark-cli is not authenticated. Run: lark-cli auth login"
        )
    return True


def extract_wiki_token(url_or_token):
    """Extract wiki node token from a URL or return the token as-is."""
    if not isinstance(url_or_token, str):
        raise ValueError("Wiki URL or token must be a string")
    url_or_token = url_or_token.strip()
    if not url_or_token:
        raise ValueError("Wiki URL or token cannot be empty")
    if "/wiki/" in url_or_token:
        match = re.search(r"/wiki/([A-Za-z0-9]+)", url_or_token)
        if match:
            return match.group(1)
    if re.match(r"^[A-Za-z0-9_-]+$", url_or_token):
        return url_or_token
    raise ValueError(f"Cannot extract wiki token from: {url_or_token}")


def get_node_metadata(url_or_token):
    """Use lark-cli to fetch wiki node metadata."""
    cmd = [
        "lark-cli", "wiki", "+node-get",
        "--node-token", url_or_token,
        "--as", "user",
        "--json",
    ]
    data = run_cmd(cmd, check=False)
    if not data or not data.get("ok"):
        raise RuntimeError(f"Failed to fetch node metadata for {url_or_token}: {data}")
    return data["data"]


def discover_tree(space_id, root_token, title, output_dir, dry_run=False):
    """Recursively list source wiki nodes and save source_tree.json."""
    print(f"\n[discover] Scanning source wiki: {title}")

    def list_children(parent_node_token):
        cmd = [
            "lark-cli", "wiki", "+node-list",
            "--space-id", space_id,
            "--parent-node-token", parent_node_token,
            "--page-all",
            "--as", "user",
            "--json",
        ]
        data = run_cmd(cmd, check=False)
        if not data or not data.get("ok"):
            return []
        return data.get("data", {}).get("nodes", [])

    def build_tree(node_token, node_title, obj_type, obj_token=None):
        node = {
            "node_token": node_token,
            "title": node_title,
            "obj_type": obj_type,
            "obj_token": obj_token,
            "children": [],
        }
        for child in list_children(node_token):
            node["children"].append(build_tree(
                child["node_token"],
                child["title"],
                child["obj_type"],
                child.get("obj_token"),
            ))
        return node

    tree = build_tree(root_token, title, "docx", obj_token=None)

    if dry_run:
        return tree

    tree_path = output_dir / "source_tree.json"
    tree_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tree_path, 0o600)

    def count_docs(node):
        return (1 if node.get("obj_type") == "docx" else 0) + sum(count_docs(c) for c in node.get("children", []))

    count = count_docs(tree)
    print(f"[discover] Found {count} docx nodes. Tree saved to {tree_path}")
    return tree


def migrate_tree(tree, target_space, target_parent_token, output_dir, dry_run=False, yes=False):
    """Migrate source tree into target wiki."""
    print(f"\n[migrate] Starting migration to target space {target_space}")

    state_path = output_dir / "migration_state.json"
    state = {"source_to_target": {}, "failed": []}

    def save_state():
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(state_path, 0o600)

    def count_docs(node):
        return (1 if node.get("obj_type") == "docx" else 0) + sum(count_docs(c) for c in node.get("children", []))

    total = count_docs(tree)
    if dry_run:
        print(f"[dry-run] Would migrate {total} docx nodes.")
        return {"total": total, "migrated": 0, "failed": 0}

    if not yes:
        answer = input(f"Will migrate {total} documents. Continue? [y/N]: ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    def fetch_doc_content(doc_token):
        cmd = [
            "lark-cli", "docs", "+fetch",
            "--doc", doc_token,
            "--api-version", "v2",
            "--as", "user",
            "--json",
        ]
        data = run_cmd(cmd, check=False)
        if data and data.get("ok"):
            return data["data"]["document"]["content"]
        print(f"[migrate] Failed to fetch {doc_token}: {data}", file=sys.stderr)
        return None

    def create_target_doc(parent_token, title, content_xml):
        safe_title = "".join(c for c in title if c.isalnum() or c in "_-")[:30]
        tmp_file = output_dir / f"content_{safe_title}.xml"
        tmp_file.write_text(content_xml, encoding="utf-8")
        os.chmod(tmp_file, 0o600)
        rel_path = f"./{tmp_file.name}"

        cmd = [
            "lark-cli", "docs", "+create",
            "--api-version", "v2",
            "--wiki-space", target_space,
            "--parent-token", parent_token,
            "--title", title,
            "--content", f"@{rel_path}",
            "--doc-format", "xml",
            "--as", "user",
            "--json",
        ]
        try:
            data = run_cmd(cmd, check=False, cwd=output_dir)
        finally:
            try:
                tmp_file.unlink()
            except FileNotFoundError:
                pass

        if data and data.get("ok"):
            doc = data["data"]["document"]
            return doc["document_id"], doc.get("url")
        print(f"[migrate] Failed to create doc '{title}': {data}", file=sys.stderr)
        return None, None

    def get_node_token_from_doc_url(url):
        if not url:
            return None
        cmd = [
            "lark-cli", "wiki", "+node-get",
            "--node-token", url,
            "--as", "user",
            "--json",
        ]
        data = run_cmd(cmd, check=False)
        if data and data.get("ok"):
            return data["data"]["node_token"]
        return None

    def migrate_node(node, target_parent_token, is_root=False):
        source_token = node["node_token"]
        title = node["title"]
        if is_root:
            title = title + "-备份"

        if source_token in state["source_to_target"]:
            print(f"[migrate] SKIP {title} (already migrated)")
            return state["source_to_target"][source_token]

        print(f"[migrate] MIGRATE {title}")
        content = fetch_doc_content(node.get("obj_token") or source_token)
        if content is None:
            content = f"<title>{title}</title><p>（内容获取失败）</p>"

        doc_id, url = create_target_doc(target_parent_token, title, content)
        if doc_id is None:
            state["failed"].append({"source_token": source_token, "title": title, "reason": "create_failed"})
            save_state()
            return None

        target_token = get_node_token_from_doc_url(url)
        if target_token is None:
            state["failed"].append({"source_token": source_token, "title": title, "reason": "node_resolve_failed", "doc_id": doc_id})
            save_state()
            return None

        state["source_to_target"][source_token] = target_token
        save_state()
        print(f"[migrate]   -> {url}")
        time.sleep(0.5)
        return target_token

    root_target_token = migrate_node(tree, target_parent_token, is_root=True)
    if root_target_token is None:
        raise RuntimeError("Failed to create root node in target wiki")

    def recurse(node, parent_target_token):
        for child in node.get("children", []):
            child_target_token = migrate_node(child, parent_target_token)
            if child_target_token:
                recurse(child, child_target_token)

    recurse(tree, root_target_token)

    print(f"\n[migrate] Migration complete. State saved to {state_path}")
    print(f"[migrate] Total migrated: {len(state['source_to_target'])}, Failed: {len(state['failed'])}")
    return {"total": total, "migrated": len(state["source_to_target"]), "failed": len(state["failed"])}


def run_migration(source, target, output_dir=None, dry_run=False, yes=False):
    """High-level entry point used by CLI, MCP server, and skill wrappers."""
    check_lark_cli()

    source_token = extract_wiki_token(source)
    target_token = extract_wiki_token(target)

    print("[setup] Resolving source wiki metadata...")
    source_meta = get_node_metadata(source)
    source_space = source_meta["space_id"]
    source_title = source_meta["title"]
    print(f"[setup] Source: {source_title} (space {source_space})")

    print("[setup] Resolving target wiki metadata...")
    target_meta = get_node_metadata(target)
    target_space = target_meta["space_id"]
    target_title = target_meta["title"]
    print(f"[setup] Target parent: {target_title} (space {target_space})")

    if output_dir:
        output_dir = Path(output_dir)
    else:
        slug = re.sub(r"[^A-Za-z0-9_\-]", "_", source_title)[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = Path(os.environ.get(ENV_OUTPUT_DIR, DEFAULT_BASE_DIR))
        output_dir = base / f"wiki-migration-{slug}-{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    # Restrict working directory to owner only
    os.chmod(output_dir, 0o700)
    print(f"[setup] Working directory: {output_dir}")

    manifest = {
        "source": {"url_or_token": source, "space_id": source_space, "node_token": source_token, "title": source_title},
        "target": {"url_or_token": target, "space_id": target_space, "node_token": target_token, "title": target_title},
        "output_dir": str(output_dir),
    }
    if not dry_run:
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(manifest_path, 0o600)

    tree = discover_tree(source_space, source_token, source_title, output_dir, dry_run=dry_run)
    result = migrate_tree(tree, target_space, target_token, output_dir, dry_run=dry_run, yes=yes)

    return {
        "source": source_title,
        "target_space": target_space,
        "target_parent": target_title,
        "output_dir": str(output_dir),
        "total": result["total"],
        "migrated": result["migrated"],
        "failed": result["failed"],
    }


def main():
    parser = argparse.ArgumentParser(description="Migrate a Feishu wiki to another Feishu wiki.")
    parser.add_argument("source", help="Source wiki URL or node token")
    parser.add_argument("target", help="Target wiki URL or parent node token")
    parser.add_argument("--output-dir", help="Working directory for this migration")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, do not create documents")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    result = run_migration(
        source=args.source,
        target=args.target,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        yes=args.yes,
    )

    print("\n=== Migration Summary ===")
    print(f"Source:        {result['source']}")
    print(f"Target space:  {result['target_space']}")
    print(f"Target parent: {result['target_parent']}")
    print(f"Docx nodes:    {result['total']}")
    print(f"Migrated:      {result['migrated']}")
    print(f"Failed:        {result['failed']}")
    print(f"Work dir:      {result['output_dir']}")

    if result["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
