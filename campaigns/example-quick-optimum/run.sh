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

# Jobs take about a second, so a run that proves the machinery works is minutes.
# Enough for a sweep and then some refinement: one round would not show what a campaign
# does. Jobs here are a second each, so the budget bounds turns, not money.
export CAS_MAX_SUBMITS=16
export CAS_MAX_RUNTIME=900

# No critic on a first run: it finishes in a few minutes and shows the machinery.
# Run it again with one when you want to see a cycle reviewed -- it takes longer,
# because the reviewing model reads the rows and thinks before it answers:
#
#     CRITIC_MODEL=auto CRITIC_BASE_URL=<your gateway> ./run.sh
#
# docs/llm.md covers what serves the second model.
export CRITIC_MODEL="${CRITIC_MODEL:-}"

export NOTIFY_START="${NOTIFY_START:-true}"
export NOTIFY_DAILY="${NOTIFY_DAILY:-false}"
export NOTIFY_FINISH="${NOTIFY_FINISH:-true}"

echo "[run] CAMPAIGN=$CAMPAIGN USER=$USER_NAME"
python -u ../../framework/agent.py
