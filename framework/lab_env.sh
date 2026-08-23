# Sourced by a campaign's run.sh, not run. Loads this installation's own settings from
# lab.env at the top of the repository -- what is available here, as opposed to what a
# campaign wants. Absent file: the framework's defaults apply.
_lab_file="$(dirname "${BASH_SOURCE[0]}")/../lab.env"
if [ -f "$_lab_file" ]; then . "$_lab_file"; fi
unset _lab_file
