#!/usr/bin/env bash
# OPTIONAL. This lab's own repository, worked on from a Slack channel of its own.
# Settings come from notifiers/slack.env; the channel and webhook here are its own, so
# it does not share either with the secretary.
# Run from this dir: ./run_engineer.sh
set -euo pipefail
cd "$(dirname "$0")"
# source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate agentlab
umask 002
export PATH="$HOME/.local/bin:$PATH"
. ../framework/settings.sh
export LAB_DIR="$(cd .. && pwd)"

# Its own channel, webhook and queue -- sharing any of them with the secretary would
# put engineering questions in front of the wrong reader.
export SLACK_CHANNEL="${ENGINEER_SLACK_CHANNEL:-}"
export SLACK_WEBHOOK_FILE="${ENGINEER_WEBHOOK_FILE:-$HOME/.slack_webhook_dev}"
export SLACK_INBOX="$LAB_DIR/workspace/run/engineer_inbox.md"
export SLACK_STATE="$LAB_DIR/workspace/run/engineer_last_ts"
export SLACK_PREFIX="${SLACK_PREFIX:-engineer}"
export SLACK_READ_ALL="${SLACK_READ_ALL:-true}"
export ENGINEER_BRANCH="${ENGINEER_BRANCH:-}"
export ENGINEER_POLL="${ENGINEER_POLL:-5}"

[ -n "$SLACK_CHANNEL" ] || { echo "set ENGINEER_SLACK_CHANNEL to the channel it reads" >&2; exit 2; }

# The bridge for that channel, and the engineer that reads what it delivers. One
# process would be simpler, but the bridge is the same one the secretary uses.
echo "[run] engineer <- Slack $SLACK_CHANNEL, repository $LAB_DIR"
python -u ../framework/slack_to_board.py &
BRIDGE=$!
trap 'kill $BRIDGE 2>/dev/null' EXIT
python -u ../framework/engineer.py
