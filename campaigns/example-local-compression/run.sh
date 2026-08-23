#!/bin/bash
# Launch the agent for this campaign. Run from this directory, inside tmux:
#   tmux new -s agentlab && ./run.sh
#
# Stop:  ../../framework/kill_agent.sh --drain <run_id>
# List:  ../../framework/list_agents.sh --all
set -euo pipefail
cd "$(dirname "$0")"

# Environment providing the claude CLI and the Python packages in requirements.txt.
# source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate agentlab
export PATH="$HOME/.local/bin:$PATH"

# Settings and defaults: docs/settings.md
export CAMPAIGN="$(basename "$PWD")"
export USER_NAME="${USER_NAME:-$USER}"

export MAX_SUBMITS=12
export MAX_RUNTIME=1800

export NOTIFY_START=false
export NOTIFY_DAILY=false
export NOTIFY_FINISH=false

echo "[run] CAMPAIGN=$CAMPAIGN USER=$USER_NAME"
python -u ../../framework/agent.py
