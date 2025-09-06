#!/usr/bin/env python3
"""
DevTool CLI

A command-line tool for development utilities.
"""
import argparse
import subprocess
import json
import os
from typing import Any, List, Dict, Optional
from pathlib import Path

def run_command(cmd: List[str], capture_output: bool = True, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        return subprocess.run(cmd, capture_output=capture_output, text=True, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        return e

def get_docker_containers() -> List[Dict[str, str]]:
    """Get list of running Docker containers."""
    result = run_command(["docker", "ps", "--format", "json"])
    if result.returncode != 0:
        return []
    
    containers = []
    for line in result.stdout.strip().split('\n'):
        if line.strip():
            try:
                container = json.loads(line)
                containers.append({
                    'id': container.get('ID', ''),
                    'name': container.get('Names', ''),
                    'image': container.get('Image', ''),
                    'status': container.get('Status', ''),
                    'ports': container.get('Ports', '')
                })
            except json.JSONDecodeError:
                continue
    return containers

def get_git_worktrees(repo_path: str) -> List[Dict[str, str]]:
    """Get list of Git worktrees for a repository."""
    if not os.path.exists(repo_path):
        return []
    
    result = run_command(["git", "worktree", "list"], cwd=repo_path)
    if result.returncode != 0:
        return []
    
    worktrees = []
    for line in result.stdout.strip().split('\n'):
        if line.strip():
            parts = line.split()
            if len(parts) >= 2:
                worktrees.append({
                    'path': parts[0],
                    'branch': parts[1] if len(parts) > 1 else 'HEAD',
                    'commit': parts[2] if len(parts) > 2 else ''
                })
    return worktrees

def find_repos_in_workspace(workspace_dir: str = "~/dev") -> List[str]:
    """Find Git repositories in the workspace directory."""
    workspace_path = os.path.expanduser(workspace_dir)
    repos = []
    
    if not os.path.exists(workspace_path):
        return repos
    
    for root, dirs, files in os.walk(workspace_path):
        if '.git' in dirs:
            repos.append(root)
            dirs[:] = []  # Don't recurse into subdirs of found repos
    
    return repos

def cmd_list(args: argparse.Namespace) -> None:
    """List active sessions and resources."""
    print("🔍 DevTool Session Discovery")
    print("=" * 50)
    
    # Docker containers
    containers = get_docker_containers()
    print(f"\n🐳 Docker Containers ({len(containers)} found):")
    if containers:
        for container in containers:
            print(f"  • {container['name']} ({container['image']}) - {container['status']}")
    else:
        print("  No running containers found")
    
    # Git repositories and worktrees
    repos = find_repos_in_workspace()
    print(f"\n📁 Git Repositories ({len(repos)} found):")
    for repo in repos:
        print(f"  • {os.path.basename(repo)}")
        worktrees = get_git_worktrees(repo)
        if len(worktrees) > 1:  # More than just main worktree
            for wt in worktrees[1:]:  # Skip main worktree
                print(f"    └─ worktree: {os.path.basename(wt['path'])} ({wt['branch']})")

def cmd_status(args: argparse.Namespace) -> None:
    """Show system status overview."""
    print("📊 DevTool System Status")
    print("=" * 50)
    
    # Docker status
    docker_result = run_command(["docker", "info"])
    docker_ok = docker_result.returncode == 0
    print(f"🐳 Docker: {'✅ Running' if docker_ok else '❌ Not available'}")
    
    # Git status
    git_result = run_command(["git", "--version"])
    git_ok = git_result.returncode == 0
    print(f"📦 Git: {'✅ Available' if git_ok else '❌ Not available'}")
    
    # Workspace
    workspace = os.path.expanduser("~/dev")
    workspace_exists = os.path.exists(workspace)
    print(f"📁 Workspace: {'✅ ' + workspace if workspace_exists else '❌ ~/dev not found'}")
    
    # Summary
    all_good = docker_ok and git_ok and workspace_exists
    print(f"\n🎯 Overall Status: {'✅ Ready' if all_good else '⚠️  Issues detected'}")

def main() -> None:
    """Entry point for the DevTool CLI."""
    parser = argparse.ArgumentParser(
        description="DevTool: A developer utility CLI."
    )
    parser.add_argument(
        "-v", "--version",
        action="store_true",
        help="Show the version and exit."
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List active sessions and resources')
    
    # Status command  
    status_parser = subparsers.add_parser('status', help='Show system status overview')
    
    # Legacy message option (for backward compatibility)
    parser.add_argument(
        "-m", "--message",
        type=str,
        default=None,
        help="Print a custom message (legacy)."
    )
    
    args = parser.parse_args()

    if args.version:
        print("DevTool version 0.1.0")
    elif args.command == 'list':
        cmd_list(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.message:
        print(f"Message: {args.message}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
