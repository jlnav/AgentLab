# Slack

A campaign posts its status, milestones and alerts to a Slack channel, and messages sent
back reach a running campaign so it can be steered mid-run. Optional, and it can be added
at any time.

## The pieces

**The Slack app** is a registration in a workspace: a name and a set of scopes. Nothing
runs on Slack's side for you. It exists so credentials can be issued against it. Most
workspaces need a Slack admin to approve one, requested through the app setup process.

**The incoming webhook** is a URL Slack issues, `https://hooks.slack.com/services/…`,
bound to one workspace and one channel. POST JSON to it and the message appears there.
There is no authentication header — the URL is the credential.

**The bot token**, `xoxb-…`, is presented as `Authorization: Bearer` on calls to Slack's
Web API. Reading a channel needs the `channels:history` scope.

Keep both outside the repository, in `~/.slack_webhook` and `~/.slack_bot_token`.

## Two paths, two credentials

Outbound and inbound use different endpoints and different credentials. Neither passes
through the other, and neither passes through the app — the app is an identity, not a hop.

**Outbound.** `framework/slack_notify.sh` POSTs to the webhook URL. The URL alone
authorises it, so any machine holding the file can post.

**Inbound.** `framework/slack_to_board.py` polls
`https://slack.com/api/conversations.history` with the bot token, every 30 seconds, and
appends any message mentioning the bot to `workspace/<campaign>/ANNOUNCEMENTS.md`. A
message naming a campaign goes to that one; otherwise to all of them.

Slack has no way to reach a compute node directly, which is why inbound is a poll rather
than Slack pushing to you.

## The announcements board

`ANNOUNCEMENTS.md` is the mechanism; Slack is one way to write to it. A running campaign
reads its board between rounds and acts on what is there. Appending to the file by any
other means works identically.

## The secretary

`framework/secretary.py` watches the boards and answers from `results.jsonl`,
`LOGBOOK.md` and `JOURNAL.md`, posting back through the webhook.

When campaigns are running, it is the first responder, so a question is answered once
rather than by every agent that sees the board. It checks for a live agent and relays
only what needs that agent's own reasoning.

## Where things run

| | runs where | needs |
|---|---|---|
| campaign agent | any machine, one per campaign | `~/.slack_webhook` |
| bridge, `run_slack_bridge.sh` | one per lab | `~/.slack_bot_token`, `SLACK_CHANNEL` |
| secretary, `run_secretary.sh` | one per lab | `~/.slack_webhook` |

Which is why joining a lab is a one-line setup: you need the channel and the webhook URL,
and nothing else. Creating the app, issuing the token and running the two processes
happens once, by whoever hosts the lab.

Neither credential is tied to the machine that created it. Moving a lab means copying the
two files and starting the bridge and secretary elsewhere.
