
# VS Code Docker Workspace

## Requirements

1. Enable AI to auto-complete actions safely.
2. Allow multiple VS Code instances to run in isolation.
3. Provide a reusable base Docker image with:
    - Ubuntu
    - Rich dev toolkit: Rust, Python, .NET, GCC+LLVM
    - Networking tools: tcpdump, snort, wireshark, iptables, etc.
    - VS Code, git, shell utilities
    - X and remote X tools
4. Develop a Python-based dev tool that:
    - Accepts a local repo as an argument
    - Clones a new Docker image with the repo (COW) and a local workspace (RW)
    - Runs the image with both repo and workspace, with remote X display
    - Inside Docker: creates a new feature branch in a worktree, names it `YYMMDD-<feature>`, runs VS Code, and ensures the worktree is available for merging
    - Leaves a comprehensive commit message for the feature branch
    - Allows resuming and finishing sessions
    - Prompts for squash-merging to master, with a single commit referencing the branch for full history
    - Supports extension of workflows (start, resume, squash-merge, etc.) via plugins/extensions
5. Ensure user settings, extensions, and workspace state can persist across sessions.
6. Include comprehensive documentation and LLM usage instructions.
7. Provide automated build/test/clippy workflows and a plan for automated testing of the dev tool.

---

## Current Status & Updated Plan (2025-09-06)

### Current Implementation State
- ✅ **Base Docker Image**: Complete - Dockerfile with Ubuntu, dev tools, networking utilities, code-server, and X11 support
- ✅ **Basic CLI Structure**: `devtool/cli.py` with minimal argument parsing
- ✅ **Testing Infrastructure**: pytest setup with basic CLI tests
- ✅ **Docker Compose**: Basic setup for testing X11 with xclock
- ✅ **Session Discovery Feature**: `devtool list` and `devtool status` commands implemented
- ✅ **Virtual Environment**: Setup with `SETUP_ENV.sh`, wrapper script `devtool.sh`
- 🚧 **Dev Tool Core**: Basic CLI only - needs full workflow implementation
- ❌ **VS Code Integration**: Not started
- ❌ **X11 Forwarding**: Not implemented for VS Code
- ❌ **Session Management**: Not implemented
- ❌ **Git Worktree Workflow**: Not implemented

### Updated Development Approach
**Phase 1: CLI-Only Workflow (Current Focus)**
- Implement core workflow using command-line tools only
- Validate Git worktree management and Docker orchestration
- Build robust session lifecycle (start → develop → finish)
- Defer VS Code and X11 integration until CLI workflow is proven

**Phase 2: VS Code Integration**
- Add code-server for headless VS Code
- Implement X11 forwarding for GUI
- Ensure orthogonal to CLI workflow

**Phase 3: Advanced Features**
- Plugin system for workflow extensions
- Session persistence and state management
- User settings/extensions persistence

### Implementation Strategy
- **Feature Branches**: Each complementary feature gets its own `YYMMDD-feature` branch
- **Incremental Development**: Build and test each component separately
- **CLI-First Validation**: Prove core workflow works before adding GUI layers

### Complementary Features (Non-Critical Enhancements)
These quality-of-life improvements will be implemented as separate feature branches:

1. **Session Discovery & Listing** ✅ **COMPLETED**
   - `devtool list` - Show active sessions
   - `devtool status` - System overview
   - Auto-detect orphaned containers/worktrees

2. **State Management & Cleanup**
   - `devtool cleanup` - Remove stale resources
   - `devtool doctor` - Health checks
   - Auto-cleanup policies

3. **Workspace Organization**
   - `devtool init` - Setup workspace structure
   - Configurable workspace locations
   - `devtool workspaces` - Manage directories

4. **Configuration Management**
   - User config in `~/.devtool/config.json`
   - `devtool config` - View/edit settings

5. **Validation & Diagnostics**
   - `devtool check <repo>` - Pre-flight validation
   - Permission and dependency checks

6. **Better Error Handling & Logging**
   - Structured logging to `~/.devtool/logs/`
   - Debug mode support

7. **Helper Utilities**
   - `devtool shell <session>` - Container access
   - `devtool logs <session>` - Container logs
   - `devtool export <session>` - Debug exports

---

## Usage

### Setup
```bash
# Clone the repository and enter the worktree
cd 250906-devtool-cli-worktree

# Setup virtual environment (optional - CLI works without it)
./SETUP_ENV.sh

# Or use the wrapper script (handles venv automatically)
./devtool.sh --help
```

### Current CLI Commands
```bash
# Show version
python3 devtool/cli.py --version
# or with wrapper
./devtool.sh --version

# List active sessions and resources
python3 devtool/cli.py list

# Show system status
python3 devtool/cli.py status

# Show help
python3 devtool/cli.py --help
```

### Testing
```bash
# Run tests
python3 -m pytest tests/ -v

# Run with virtualenv
source .venv/bin/activate && python3 -m pytest tests/ -v
```

### Architecture

- **Base Docker Image**: Ubuntu-based, pre-installed with major language toolchains, networking tools, VS Code, and X/remote X support. Designed for easy extension.
- **Dev Tool (Python)**: CLI utility to manage containerized VS Code sessions, feature branch workflows, and session persistence. Plugin system for workflow extensions.
- **Session Isolation**: Each feature branch runs in its own Docker container, leveraging Docker’s isolation. Optional: resource limits and security flags for extra sandboxing.
- **Persistence**: User settings, extensions, and workspace state are mounted to persist across sessions.
- **Documentation**: Usage, troubleshooting, LLM instructions, and FAQ.

### Execution Plan


1. **Base Image**
    - Build a Dockerfile with all required tools and language runtimes.
    - **General Principle:** Break up `apt-get` and other installation steps into logical layers to maximize Docker build caching and minimize rebuild times when updating dependencies.
    - Add support for X/remote X and VS Code.
    - Document image extension process.

2. **Dev Tool (Python)**
    - CLI to start, resume, and finish sessions.
    - Accepts repo as argument, sets up COW repo and RW workspace.
    - Manages Docker container lifecycle and feature branch workflow.
    - Plugin system for workflow extensions (e.g., squash-merge, resume, etc.).
    - Ensure persistence of user settings and extensions.

3. **Workflow**
    - On session start: create feature branch, launch VS Code in container, remote X display.
    - On finish: comprehensive commit message, squash-merge prompt, reference to full branch history.
    - Support for resuming/finishing sessions.

4. **Automation & Testing**
    - Integrate build/test/clippy workflows.
    - Plan and implement automated tests for the dev tool.

5. **Documentation**
    - Write clear setup, usage, and troubleshooting docs.
    - Include LLM usage instructions and FAQ.

---

The end result will be a robust, reproducible, and extensible workspace for safe, isolated, and efficient development with AI and VS Code.
