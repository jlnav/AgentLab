# Sourced, not run: the settings this installation and its lab keep outside the code.
#
#   lab.env                 what this installation can reach -- gateways, credentials
#   notifiers/<name>.env    how the lab talks to Slack, default notifiers/slack.env
#
# Both are untracked, both are optional, and anything already in the environment wins
# over either: every line in them is written `${VAR:-default}`.
#
# A campaign's run.sh sources this before its own settings, so the campaign has the
# last word on anything the lab merely offers.
_settings_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for _settings_file in "$_settings_root/lab.env" \
                      "$_settings_root/notifiers/${NOTIFIER:-slack}.env"; do
    [ -f "$_settings_file" ] && . "$_settings_file"
done
unset _settings_root _settings_file
