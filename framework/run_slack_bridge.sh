#!/bin/bash
# OPTIONAL. Forwards Slack messages that @-mention the bot onto the announcements
# board. Needs a bot token with channels:history -- see AGENTS.md.
# Settings come from notifiers/slack.env; copy notifiers/slack.env.template to make it.
# Run from this dir: ./run_slack_bridge.sh
set -euo pipefail
cd "$(dirname "$0")"
# source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate cas
umask 002
. ./notifier_env.sh
export WORKSPACE_ROOT="$(cd ../workspace && pwd)"   # all campaigns
export SLACK_CHANNEL="${SLACK_CHANNEL:-}"                             # channel ID to read
export SLACK_BOT_TOKEN_FILE="${SLACK_BOT_TOKEN_FILE:-$HOME/.slack_bot_token}"
export SLACK_BOT_NAME="${SLACK_BOT_NAME:-@cas_agent}"                 # plain-text mention fallback
# 5s, not 30: this poll dominates end-to-end latency, and conversations.history is
# Slack Tier 3 (50+ req/min), so 12/min leaves plenty of headroom.
export SLACK_FETCH_POLL="${SLACK_FETCH_POLL:-5}"
echo "[run] slack bridge -> campaign boards under $WORKSPACE_ROOT"
python -u slack_to_board.py
