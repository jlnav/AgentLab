#!/usr/bin/env python3
"""
The critic: a second model that checks a cycle's write-up against the recorded results.

It is a plain request-and-reply, not an agent. The evidence it judges is chosen by the
framework and travels with the verdict, so a review can be read later and checked --
which is the point of having one. It cannot submit work, write files, or continue the
research.

Which model it is depends on what the lab can reach. When the agent talks to a gateway
serving several models (see docs/llm.md), `CRITIC_MODEL=auto` picks one from a different
family than the agent's own, because two instances of one model share their blind spots.
With no gateway there is only Claude, and a Claude critic still helps: no memory of the
reasoning, a different prompt, and only the rows to go on.

Resolved once at startup, never mid-run: a critic that vanishes between rounds is worse
than one you knew you did not have.

Env:
    CRITIC_MODEL         model name, `auto`, or unset for no critic
    CRITIC_REQUIRED      1/true to refuse to start when no critic can be resolved
    CRITIC_PROMPT_FILE   overrides framework/critic_prompt.md
    CRITIC_MAX_TOKENS    reply cap (default 8000; a reasoning model spends most of it
                         thinking, so a tight cap returns an empty reply)
"""

import json
import os
import re
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_SETTING = (os.environ.get("CRITIC_MODEL") or "").strip()
REQUIRED = (os.environ.get("CRITIC_REQUIRED", "").strip().lower()
            in ("1", "true", "yes", "on"))
MAX_TOKENS = int(os.environ.get("CRITIC_MAX_TOKENS", "8000"))
# The agent's own gateway. The critic goes to the same place with a different model.
BASE_URL = (os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

BLOCK_RE = re.compile(
    r"CLAIM:\s*(?P<claim>.+?)\n\s*VERDICT:\s*(?P<verdict>\w+).*?"
    r"SEVERITY:\s*(?P<severity>\w+)", re.S | re.I)


class CriticUnavailable(Exception):
    """No critic could be resolved and the campaign asked for one."""


def _prompt_text():
    path = os.environ.get("CRITIC_PROMPT_FILE") or os.path.join(SCRIPT_DIR, "critic_prompt.md")
    with open(path) as f:
        return f.read()


def _served_models():
    """Model names the gateway offers, with what each resolves to upstream. Empty when
    there is no gateway -- talking to Anthropic directly means Claude only."""
    try:
        req = urllib.request.Request(BASE_URL + "/model/info",
                                     headers={"x-api-key": API_KEY})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r).get("data", [])
    except Exception:
        return {}
    out = {}
    for m in data:
        name = m.get("model_name")
        if name:
            out[name] = (m.get("litellm_params", {}).get("model", "") or "").split("/")[-1]
    return out


def resolve(agent_model=""):
    """Pick the critic model, once, at startup. Returns (name, label) or (None, reason)."""
    if not MODEL_SETTING:
        return None, "no critic (CRITIC_MODEL unset)"
    served = _served_models()
    if MODEL_SETTING != "auto":
        if served and MODEL_SETTING not in served:
            raise CriticUnavailable(
                f"CRITIC_MODEL={MODEL_SETTING} is not served by {BASE_URL} "
                f"(it has: {', '.join(sorted(served)) or 'nothing'})")
        return MODEL_SETTING, served.get(MODEL_SETTING) or MODEL_SETTING
    if not served:
        if REQUIRED:
            raise CriticUnavailable(
                f"CRITIC_MODEL=auto but {BASE_URL} lists no models, so there is nothing "
                "to choose from")
        return None, "no critic (no gateway to choose a model from)"
    # A different family than the agent's own, where there is one.
    agent_family = (agent_model or "").split("-")[0].lower()
    for name, upstream in sorted(served.items()):
        if agent_family and agent_family in (upstream or name).lower():
            continue
        return name, upstream or name
    name, upstream = sorted(served.items())[0]
    return name, upstream or name


def review(model, write_up, evidence):
    """Send one cycle to the critic. Returns its raw reply; never raises."""
    prompt = (_prompt_text()
              + "\n\n# The write-up\n\n" + write_up
              + "\n\n# The recorded results\n\n" + (evidence or "(no rows recorded)"))
    body = json.dumps({"model": model, "max_tokens": MAX_TOKENS,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(
        BASE_URL + "/v1/messages", data=body,
        headers={"content-type": "application/json", "x-api-key": API_KEY,
                 "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            reply = json.load(r)
        text = "".join(b.get("text", "") for b in reply.get("content", [])).strip()
        # A reasoning model can spend the whole budget thinking and return nothing.
        # Silence and truncation look identical from here, so say which it was.
        if not text and reply.get("stop_reason") == "max_tokens":
            print(f"[critic] no review: the reply hit CRITIC_MAX_TOKENS "
                  f"({MAX_TOKENS}) before writing anything", flush=True)
        return text
    except Exception as e:
        print(f"[critic] review failed (ignored): {e}", flush=True)
        return ""


def blocking(reply):
    """The blocking findings in a reply, as (claim, verdict) pairs. A reply that does
    not parse yields none: a critic that ignored the format does not get to halt a run
    on the strength of prose nobody can act on."""
    out = []
    for m in BLOCK_RE.finditer(reply or ""):
        if m.group("severity").strip().lower() == "blocking":
            out.append((m.group("claim").strip(), m.group("verdict").strip().lower()))
    return out
