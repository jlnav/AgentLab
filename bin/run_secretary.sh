#!/bin/bash
# OPTIONAL. Answers board questions so the agents are not interrupted.
# Settings come from notifiers/slack.env; copy notifiers/slack.env.template to make it.
# Run from this dir: ./run_secretary.sh
set -euo pipefail
cd "$(dirname "$0")"
# source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate cas
umask 002
export PATH="$HOME/.local/bin:$PATH"
. ../framework/settings.sh
export WORKSPACE_ROOT="$(cd ../workspace && pwd)"   # all campaigns
export SLACK_WEBHOOK_FILE="${SLACK_WEBHOOK_FILE:-$HOME/.slack_webhook}"
export NOTIFY_SCRIPT="${NOTIFY_SCRIPT:-}"
export SLACK_PREFIX="${SLACK_PREFIX:-secretary}"   # slack_notify.sh renders this as *[secretary]*
export SLACK_CAMPAIGNS="${SLACK_CAMPAIGNS:-}"   # campaigns the secretary may start and stop; empty means none
export SECRETARY_POLL="${SECRETARY_POLL:-5}"       # also how often the heartbeat the bridge reads is rewritten
echo "[run] secretary -> campaign boards under $WORKSPACE_ROOT"
python -u ../framework/secretary.py
