# Sourced by the launchers, not run. Loads the lab's messaging settings from
# notifiers/<NOTIFIER>.env, default notifiers/slack.env. Absent file: defaults apply.
_notifier_file="$(dirname "${BASH_SOURCE[0]}")/../notifiers/${NOTIFIER:-slack}.env"
if [ -f "$_notifier_file" ]; then . "$_notifier_file"; fi
unset _notifier_file
