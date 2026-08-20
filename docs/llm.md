# Which LLM the agent uses

The agent runs on the Claude Agent SDK, which talks the Anthropic Messages API and
takes its configuration from Claude Code's settings. By default that is
`~/.claude/settings.json`, so each person's own setup applies with nothing to
configure per campaign.

Any endpoint serving the Messages API can be used instead, by pointing
`ANTHROPIC_BASE_URL` at it. That is how a campaign runs against a facility gateway
rather than the public API, and — with a translation layer in front — how it runs on
a model that is not Claude.

## A gateway that already serves the Messages API

Set the base URL and the model in `~/.claude/settings.json`:

```json
{
  "env": {"ANTHROPIC_BASE_URL": "https://gateway.example/api"},
  "model": "claude-opus-4-5"
}
```

Nothing in `framework/` changes. Tools, permissions and context handling are the
SDK's, unchanged.

## A model that is not Claude, through LiteLLM

[LiteLLM](https://docs.litellm.ai) exposes a `/v1/messages` endpoint in Anthropic
format and routes it to any provider it supports. Running it in front of an
OpenAI-style backend lets a campaign run on that backend through the same SDK path.

Install it in its own environment. Its proxy extra pulls in a large dependency set,
including versions that a general working environment is unlikely to match:

```
python -m venv ~/venvs/litellm && ~/venvs/litellm/bin/pip install "litellm[proxy]"
```

Then pin FastAPI down, as a separate step:

```
~/venvs/litellm/bin/pip install "fastapi==0.118.0"
```

The two steps cannot be combined: asking for both at once makes the resolver satisfy
the FastAPI pin by choosing a years-old LiteLLM instead. Installed in this order,
LiteLLM stays current and FastAPI is downgraded afterwards.

The pin is needed because LiteLLM 1.97.0 imports `get_flat_dependant`, which later
FastAPI releases removed, and `litellm[proxy]` installs one of those releases. Without
the pin the proxy fails to start, reporting either that import or
`ModuleNotFoundError: No module named 'proxy_server'` depending on how it is launched.
Both come from the same cause. Check whether a newer LiteLLM has dropped the import
before carrying the pin forward.

Write a config naming the upstream model, its endpoint, and the key to reach it:

```yaml
model_list:
  - model_name: my-model
    litellm_params:
      model: openai/<upstream-model-name>
      api_base: https://backend.example/v1
      api_key: <key>

litellm_settings:
  use_chat_completions_url_for_anthropic_messages: true
```

`use_chat_completions_url_for_anthropic_messages` is required for an OpenAI-style
upstream. Without it LiteLLM translates `/v1/messages` to the OpenAI Responses API,
and a backend that implements only `/v1/chat/completions` answers 404.

Start the proxy:

```
~/venvs/litellm/bin/litellm --config config.yaml --port 4000
```

Check it before pointing the agent at it:

```
curl -s -X POST http://0.0.0.0:4000/v1/messages -H 'content-type: application/json' -H 'x-api-key: <key>' -H 'anthropic-version: 2023-06-01' -d '{"model":"my-model","max_tokens":64,"messages":[{"role":"user","content":"say hi"}]}'
```

Then point the settings at the proxy:

```json
{
  "env": {"ANTHROPIC_BASE_URL": "http://0.0.0.0:4000", "ANTHROPIC_API_KEY": "<key>"},
  "model": "my-model"
}
```

LiteLLM passes the caller's credential upstream, so `ANTHROPIC_API_KEY` has to be one
the backend accepts, not an arbitrary string. Where the backend authenticates by
username, that username is the value.

## A different model for one campaign

Settings are per user, not per campaign, so two campaigns on one machine share them.
To give one campaign its own, put a `settings.json` in a directory of its own and
point `CLAUDE_CONFIG_DIR` at that directory in the campaign's `run.sh`:

```
export CLAUDE_CONFIG_DIR="$PWD/claude"
```

The agent then reads that file instead of `~/.claude/settings.json`. A project-level
`.claude/settings.json` does not override the user's.

## What to expect from a non-Claude model

The SDK cannot tell what is behind the endpoint, so tools, permissions and compaction
work as they always do. Two things differ:

- Context reporting is partial. `totalTokens` is real; the window size falls back to a
  default when the model name is not one the CLI knows, so the percentage in the status
  line is measured against that default rather than the model's own window.
- Tool-calling quality is the model's own. A model that follows tool schemas poorly
  will submit poorly, and no translation layer changes that. Run one short campaign and
  read `jobs.jsonl` before committing a long one to a new model.

Anthropic documents that routing Claude Code to non-Claude models through a gateway is
outside what it supports. It works, and it is worth knowing that a Claude Code release
is not tested against it.
