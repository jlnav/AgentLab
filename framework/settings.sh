# Sourced, not run: the lab's own settings, as environment variables.
#
#   lab.yaml                what this lab runs and where its things are (see the
#                           template beside it; docs/settings.md explains each)
#   notifiers/<name>.env    anything about Slack beyond the channel, default slack.env
#
# Both are untracked and both are optional. Anything already in the environment wins,
# so a campaign's run.sh has the last word on what the lab merely offers.
_settings_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
eval "$(python3 "$_settings_root/framework/lab_config.py" --export 2>/dev/null)"
_settings_notifier="$_settings_root/notifiers/${NOTIFIER:-slack}.env"
[ -f "$_settings_notifier" ] && . "$_settings_notifier"
unset _settings_root _settings_notifier
