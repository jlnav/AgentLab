#!/usr/bin/env python3
"""Interactive, deterministic setup for AgentLab."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path

LAB_DIR = Path(__file__).resolve().parent.parent
REQUIREMENTS = LAB_DIR / "requirements.txt"
MIN_PYTHON = (3, 10)
NAME_RE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]*$")


def bootstrap_rich(allow_install: bool) -> None:
    if importlib.util.find_spec("rich"):
        return
    if not allow_install:
        print("Rich is not installed. Run: python3 -m pip install rich", file=sys.stderr)
        raise SystemExit(1)
    if not sys.stdin.isatty():
        print("Rich is not installed. Run: python3 -m pip install rich", file=sys.stderr)
        raise SystemExit(1)
    answer = input("The setup interface needs Rich. Install it now? [Y/n] ").strip().lower()
    if answer not in {"", "y", "yes"}:
        raise SystemExit("Setup stopped. Install Rich and run this command again.")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "rich"])
    if result.returncode:
        raise SystemExit(result.returncode)
    os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set up AgentLab without relying on an LLM to reproduce the instructions.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--example", action="store_true", help="set up and optionally run the local example")
    mode.add_argument("--campaign", action="store_true", help="scaffold a campaign of your own")
    mode.add_argument("--check", action="store_true", help="check the local installation and change nothing")
    parser.add_argument("--dry-run", action="store_true", help="preview file changes without writing them")
    parser.add_argument("--no-color", action="store_true", help="disable colored output")
    parser.add_argument("--no-install", action="store_true", help="do not offer to install missing packages")
    return parser.parse_args()


ARGS = parse_args()
if sys.version_info < MIN_PYTHON:
    raise SystemExit(f"AgentLab requires Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer; found {sys.version.split()[0]}.")
bootstrap_rich(not ARGS.no_install and not ARGS.check and not ARGS.dry_run)

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.syntax import Syntax
from rich.table import Table

console = Console(no_color=ARGS.no_color)


def heading(step: int, title: str) -> None:
    console.rule(f"[bold cyan]Step {step}: {title}")


def command_panel(command: str, title: str = "Command") -> None:
    console.print(Panel(Syntax(command, "bash", word_wrap=True), title=title, border_style="blue"))


def run(command: list[str], *, cwd: Path = LAB_DIR, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    console.print(f"[dim]$ {' '.join(command)}[/dim]")
    return subprocess.run(command, cwd=cwd, env=env, text=True)


def package_status() -> list[tuple[str, str]]:
    packages = [
        ("rich", "Rich setup interface"),
        ("claude_agent_sdk", "Claude Agent SDK"),
        ("globus_compute_sdk", "Globus Compute SDK"),
        ("markdown", "run viewer Markdown rendering"),
    ]
    return [(description, "installed" if importlib.util.find_spec(module) else "missing") for module, description in packages]


def environment_check(offer_install: bool) -> bool:
    heading(1, "Check the installation")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Requirement")
    table.add_column("Status")
    python_ok = sys.version_info >= MIN_PYTHON
    table.add_row("Python 3.10+", f"[green]{sys.version.split()[0]}[/green]" if python_ok else "[red]too old[/red]")
    claude = shutil.which("claude")
    table.add_row("claude CLI", f"[green]{claude}[/green]" if claude else "[red]not found[/red]")
    claude_authenticated = False
    if claude:
        try:
            auth = subprocess.run(
                [claude, "auth", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if auth.returncode == 0:
                claude_authenticated = bool(json.loads(auth.stdout).get("loggedIn"))
        except (json.JSONDecodeError, subprocess.TimeoutExpired):
            pass
    auth_status = "authenticated" if claude_authenticated else "not authenticated"
    auth_color = "green" if claude_authenticated else "red"
    table.add_row("Claude authentication", f"[{auth_color}]{auth_status}[/{auth_color}]")
    missing = []
    for description, status in package_status():
        color = "green" if status == "installed" else "yellow"
        table.add_row(description, f"[{color}]{status}[/{color}]")
        if status == "missing":
            missing.append(description)
    console.print(table)

    if claude:
        result = run([claude, "--version"])
        if result.returncode or not claude_authenticated:
            console.print("[yellow]Authenticate the claude CLI before running a campaign.[/yellow]")
    else:
        console.print("Install and authenticate the Claude CLI, then rerun this check.", style="yellow")

    if missing and offer_install and Confirm.ask("Install the repository requirements now?", default=True):
        result = run([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)])
        if result.returncode:
            console.print("[red]Dependency installation failed.[/red]")
            return False
        missing = [description for description, status in package_status() if status == "missing"]

    ready = python_ok and bool(claude) and claude_authenticated and not missing
    if ready:
        console.print("[green]The local installation is ready.[/green]")
    else:
        console.print("[yellow]Setup can continue, but campaigns will not run until the missing requirements are resolved.[/yellow]")
    return ready


def preflight(campaign: str) -> bool:
    campaign_dir = LAB_DIR / "campaigns" / campaign
    env = dict(os.environ)
    env["PREFLIGHT"] = "true"
    heading(3, "Run preflight")
    console.print("Preflight validates the task contract and workspace without submitting campaign jobs.")
    result = run(["./run.sh"], cwd=campaign_dir, env=env)
    if result.returncode:
        console.print("[red]Preflight failed. Resolve the output above before starting the campaign.[/red]")
        return False
    console.print("[green]Preflight passed.[/green]")
    return True


def show_example_results() -> None:
    workspace = LAB_DIR / "workspace" / "example-quick-optimum"
    heading(4, "Read the results")
    console.print(f"Campaign output is in [bold]{workspace}[/bold].")
    for name in ("results.jsonl", "LOGBOOK.md"):
        path = workspace / name
        if path.exists():
            console.print(f"[green]found[/green] {path}")
        else:
            console.print(f"[dim]not created yet[/dim] {path}")
    command_panel("bin/list_agents.sh --all\nclaude -r <session-id>", "Inspect runs and resume a session")


def example_flow(ready: bool) -> None:
    heading(2, "Run the local example")
    console.print(Markdown(
        "`example-quick-optimum` runs on this machine. It needs no HPC allocation or "
        "Globus endpoint, but the agent still uses your configured LLM service."
    ))
    command_panel("cd campaigns/example-quick-optimum && WATCH=true AGENT_MODEL=haiku ./run.sh")
    if not ready:
        console.print("[yellow]Resolve the installation check before running preflight or the example.[/yellow]")
        return
    if Confirm.ask("Run the no-job-submission preflight now?", default=True) and not preflight("example-quick-optimum"):
        return
    if Confirm.ask("Start the example now? This makes LLM calls and writes its workspace.", default=False):
        env = dict(os.environ)
        env.update({"WATCH": "true", "AGENT_MODEL": "haiku"})
        result = run(["./run.sh"], cwd=LAB_DIR / "campaigns" / "example-quick-optimum", env=env)
        if result.returncode:
            console.print(f"[red]The example exited with status {result.returncode}.[/red]")
    show_example_results()


def ask_campaign_name() -> str:
    while True:
        name = Prompt.ask("Short campaign name").strip()
        if not NAME_RE.fullmatch(name):
            console.print("Use letters, numbers, dots, underscores, or hyphens; do not start with a dot.", style="yellow")
            continue
        path = LAB_DIR / "campaigns" / name
        if path.exists():
            console.print(f"[yellow]{path} already exists. This wizard will not overwrite it.[/yellow]")
            continue
        return name


def ask_nonempty(label: str) -> str:
    while True:
        value = Prompt.ask(label).strip()
        if value:
            return value
        console.print("A value is required.", style="yellow")


def choose_system() -> str:
    systems = sorted(path.stem for path in (LAB_DIR / "systems").glob("*.json") if path.stem != "local")
    if not systems:
        raise SystemExit("No remote systems are defined under systems/.")
    console.print("Available systems: " + ", ".join(systems))
    return Prompt.ask("Compute system", choices=systems)


def task_template(kind: str) -> str:
    if kind == "local":
        return '''"""TODO: implement one local job for this campaign.

Ask an agent to replace the explicit placeholders below. This module intentionally raises
until that work is complete.
"""

LOCAL_DESC = """
TODO: Describe what one job does, every parameter the agent may vary, and every value
returned. State which result is the objective and whether it is minimized or maximized.
"""

# TODO: Replace this example parameter with the complete explorable interface.
LOCAL_SCHEMA = {"parameter": str}


def local_fn(args):
    """Run one job on this machine and return a JSON-serializable dictionary."""
    raise NotImplementedError("Replace the generated local_fn placeholder before running jobs")
'''
    return '''"""TODO: implement one remote job for this campaign.

Ask an agent to replace the explicit placeholders below. remote_fn is shipped to the
worker by source, so imports belong inside it and dependencies arrive through args/target.
"""

import json

JOB_DESC = """
TODO: Describe what one remote job does, every parameter the agent may vary, and every
value returned. State which result is the objective and whether it is minimized or maximized.
"""

# TODO: Replace this example parameter with the complete explorable interface.
JOB_SCHEMA = {"parameter": str}


def job_key(args):
    """Return a stable identity so an identical configuration is not submitted twice."""
    return json.dumps(args, sort_keys=True, separators=(",", ":"))


def remote_fn(args, target):
    """Run one job on the compute system and return a JSON-serializable dictionary."""
    raise NotImplementedError("Replace the generated remote_fn placeholder before submitting jobs")
'''


def run_script(max_submits: int, max_runtime: int) -> str:
    return f'''#!/bin/bash
# Launch from this directory, inside tmux. Settings: ../../docs/settings.md
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
. ../../framework/settings.sh
export CAMPAIGN="$(basename "$PWD")"
export USER_NAME="${{USER_NAME:-$USER}}"

export MAX_SUBMITS="${{MAX_SUBMITS:-{max_submits}}}"
export MAX_RUNTIME="${{MAX_RUNTIME:-{max_runtime}}}"

export NOTIFY_START="${{NOTIFY_START:-false}}"
export NOTIFY_DAILY="${{NOTIFY_DAILY:-false}}"
export NOTIFY_FINISH="${{NOTIFY_FINISH:-false}}"

echo "[run] CAMPAIGN=$CAMPAIGN USER=$USER_NAME"
"${{PYTHON:-python3}}" -u ../../framework/agent.py "$@"
'''


def render_files(files: dict[Path, str], copies: dict[Path, Path]) -> None:
    console.print("\n[bold]Files to create[/bold]")
    for path, content in files.items():
        console.print(Panel(Syntax(content, "python" if path.suffix == ".py" else "json" if path.suffix == ".json" else "text", word_wrap=True), title=str(path.relative_to(LAB_DIR))))
    for destination, source in copies.items():
        console.print(f"[cyan]copy[/cyan] {source} -> {destination.relative_to(LAB_DIR)}")


def apply_files(files: dict[Path, str], copies: dict[Path, Path], executable: set[Path]) -> None:
    if ARGS.dry_run:
        console.print("[yellow]Dry run: no files were written.[/yellow]")
        return
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if path in executable:
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    for destination, source in copies.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    console.print(f"[green]Created {len(files)} files and copied {len(copies)} existing files.[/green]")


def choose_existing_files(campaign_dir: Path, reserved: set[Path]) -> dict[Path, Path]:
    if not Confirm.ask("Copy existing scripts, notes, or reference files into the campaign?", default=False):
        return {}
    console.print("Enter paths separated like shell arguments. Directories are not copied by this release.")
    while True:
        raw = Prompt.ask("Existing file paths").strip()
        try:
            sources = [Path(value).expanduser().resolve() for value in shlex.split(raw)]
        except ValueError as exc:
            console.print(f"Could not parse those paths: {exc}", style="yellow")
            continue
        if not sources or any(not source.is_file() for source in sources):
            console.print("Every path must name an existing regular file.", style="yellow")
            continue
        destinations = [campaign_dir / source.name for source in sources]
        if len(set(destinations)) != len(destinations) or any(path in reserved for path in destinations):
            console.print("Two files have the same name, or a file conflicts with a generated campaign file.", style="yellow")
            continue
        return dict(zip(destinations, sources))


def user_access_file(system: str) -> tuple[Path, str]:
    default_user = os.environ.get("USER", "user")
    while True:
        user = Prompt.ask("Local user configuration name", default=default_user).strip()
        if NAME_RE.fullmatch(user):
            break
        console.print("Use letters, numbers, dots, underscores, or hyphens; do not start with a dot.", style="yellow")
    while True:
        endpoint = ask_nonempty("Globus Compute endpoint UUID")
        try:
            uuid.UUID(endpoint)
            break
        except ValueError:
            console.print("Enter the endpoint UUID shown by globus-compute-endpoint list.", style="yellow")
    account = ask_nonempty("Project or allocation to charge")
    while True:
        work_dir = ask_nonempty("Writable directory on the compute system")
        if work_dir.startswith("/"):
            break
        console.print("Enter an absolute path on the compute system.", style="yellow")
    path = LAB_DIR / "users" / user / f"{system}.json"
    data = {"endpoint": endpoint, "account": account, "work_dir": work_dir}
    return path, json.dumps(data, indent=2) + "\n"


def agent_help_prompt(name: str, kind: str) -> str:
    contract = "LOCAL_DESC, LOCAL_SCHEMA, and local_fn(args)" if kind == "local" else "JOB_DESC, JOB_SCHEMA, job_key(args), and remote_fn(args, target)"
    return f'''Open campaigns/{name}/ and finish this AgentLab campaign scaffold.

Read AGENTS.md, campaigns/{name}/prompt.md, campaigns/{name}/user_prompt.md, and every file already placed in that campaign directory. Implement task.py's explicit TODOs using {contract}. Preserve the user's scripts and commands as given. Expose all useful experimental parameters in the schema, validate inputs, return JSON-serializable results with enough evidence to support the campaign's conclusions, and do not submit a job. Then run:

    cd campaigns/{name} && PREFLIGHT=true ./run.sh

Report every assumption and anything only the user can answer. Do not run ./run.sh without PREFLIGHT=true.
'''


def campaign_flow(ready: bool) -> None:
    heading(2, "Describe the campaign")
    name = ask_campaign_name()
    kind = Prompt.ask("Where does one job run?", choices=["local", "remote"], default="local")
    goal = ask_nonempty("Campaign goal, including what counts as an answer")
    first_run = ask_nonempty("Aim and stopping condition for the first run")
    method = Prompt.ask("Working method", choices=["quick", "standard", "research"], default="standard")
    max_submits = IntPrompt.ask("Maximum jobs submitted in one launch", default=12 if kind == "local" else 20)
    max_runtime = IntPrompt.ask("Maximum launch runtime in seconds", default=1800 if kind == "local" else 14400)
    if max_submits < 1 or max_runtime < 1:
        raise SystemExit("Job and runtime limits must be positive.")

    system = "local" if kind == "local" else choose_system()
    campaign_dir = LAB_DIR / "campaigns" / name
    files = {
        campaign_dir / "prompt.md": f"# {name}\n\n{goal}\n",
        campaign_dir / "user_prompt.md": f"# This run\n\n{first_run}\n",
        campaign_dir / "task.py": task_template(kind),
        campaign_dir / "campaign.json": json.dumps({"system": system}, indent=2) + "\n",
        campaign_dir / "method.md": (LAB_DIR / "methods" / f"{method}.md").read_text(),
        campaign_dir / "run.sh": run_script(max_submits, max_runtime),
    }
    copies = choose_existing_files(campaign_dir, set(files))

    if kind == "remote":
        heading(3, "Record remote access")
        console.print("Use an existing endpoint. Creating and configuring an endpoint remains a guided manual step in this release.")
        access_path, access_content = user_access_file(system)
        if access_path.exists():
            raise SystemExit(f"Refusing to overwrite existing access configuration: {access_path}")
        files[access_path] = access_content

    heading(4 if kind == "remote" else 3, "Preview changes")
    render_files(files, copies)
    if not ARGS.dry_run and not Confirm.ask("Create these files?", default=True):
        console.print("No files were written.")
        return
    apply_files(files, copies, {campaign_dir / "run.sh"})
    if ARGS.dry_run:
        return

    heading(5 if kind == "remote" else 4, "Finish task.py")
    prompt = agent_help_prompt(name, kind)
    console.print(Panel(prompt, title="Paste this into your agent harness", border_style="magenta"))
    if kind == "remote":
        command_panel(
            "ssh <system-host>\n"
            "python3 -V\n"
            "globus-compute-endpoint list",
            "Remote endpoint handoff",
        )
        console.print(f"Endpoint templates are under [bold]{LAB_DIR / 'systems' / 'endpoints'}[/bold].")
    command_panel(f"cd campaigns/{name} && PREFLIGHT=true ./run.sh", "Validate after task.py is implemented")
    command_panel(f"tmux new -s agentlab\ncd campaigns/{name} && ./run.sh", "Run only after preflight and explicit compute approval")
    if ready:
        console.print("Preflight is not run now because task.py still contains intentional placeholders.", style="yellow")


def main() -> int:
    console.print(Panel.fit("[bold]AgentLab Setup[/bold]\nDeterministic setup with explicit previews and handoffs.", border_style="cyan"))
    ready = environment_check(offer_install=not ARGS.check and not ARGS.dry_run and not ARGS.no_install)
    if ARGS.check:
        return 0 if ready else 1
    if ARGS.example:
        example_flow(ready)
        return 0
    if ARGS.campaign:
        campaign_flow(ready)
        return 0
    choice = Prompt.ask(
        "What do you want to set up?",
        choices=["example", "campaign"],
        default="example",
    )
    if choice == "example":
        example_flow(ready)
    else:
        campaign_flow(ready)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Setup cancelled; the current step was not completed.[/yellow]")
        raise SystemExit(130)
