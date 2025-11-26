#!/usr/bin/env python3
"""cbwtools-ai.py
===============================================================================
Project       : cbwtools AI helper
Author        : cbwinslow (co-piloted by GPT-5.1 Thinking)
Created       : 2025-11-20

Summary:
    Small CLI utility that plugs into the cbwtools ecosystem to provide
    terminal-based AI chat for different providers (e.g. OpenRouter, Gemini).

    - Reads API keys securely via `cbwtools get-secret <provider>/api_key`.
    - Supports a simple REPL chat loop in your terminal.
    - Designed to be launched inside tmux (e.g. from the cbwtools Go TUI).

Inputs:
    Command-line arguments via Typer:
        - `chat` subcommand with options:
            * provider: "openrouter" or "gemini" (extensible)
            * model: model identifier for the provider
            * system_prompt: optional system instruction

Outputs:
    - Streams conversation to stdout.
    - Logs errors and debug messages to stderr when verbose.

Dependencies:
    - Python 3.9+
    - Typer (CLI framework): `pip install typer[all]`
    - Requests (HTTP client): `pip install requests`

Environment:
    - CBWTOOLS_BIN (optional): path to cbwtools executable (default: "cbwtools")
    - OPENROUTER_API_KEY / GEMINI_API_KEY (optional fallbacks if cbwtools
      secret lookup is not configured yet).

Security notes:
    - API keys are never logged.
    - API keys are fetched at runtime from cbwtools or env vars.
    - No conversation history is persisted to disk by default.

Modification log:
    - 2025-11-20: Initial version.
===============================================================================
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
import typer

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(add_completion=False, help="AI helper for cbwtools.")


# ---------------------------------------------------------------------------
# Utility + configuration helpers
# ---------------------------------------------------------------------------

@dataclass
class ProviderConfig:
    name: str
    env_var: str
    secret_name: str  # name in cbwtools secrets (e.g. "openrouter/api_key")
    base_url: str
    default_model: str


PROVIDERS: Dict[str, ProviderConfig] = {
    "openrouter": ProviderConfig(
        name="openrouter",
        env_var="OPENROUTER_API_KEY",
        secret_name="openrouter/api_key",
        base_url="https://openrouter.ai/api/v1",
        # Adjust to your preferred free model; verify with OpenRouter docs.
        default_model="openai/gpt-4o-mini",
    ),
    "gemini": ProviderConfig(
        name="gemini",
        env_var="GEMINI_API_KEY",
        secret_name="gemini/api_key",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        # Adjust to your preferred Gemini model.
        default_model="models/gemini-1.5-flash",
    ),
}


def cbwtools_bin() -> str:
    """Return the cbwtools executable path, honoring CBWTOOLS_BIN if set.

    This allows you to point to `python cbwtools.py` or an installed
    `cbwtools` entry-point.
    """

    return os.environ.get("CBWTOOLS_BIN", "cbwtools")


def run_cbwtools(args: List[str], timeout: int = 10) -> str:
    """Run cbwtools with the given arguments and return stdout.

    This is used primarily to fetch secrets from the cbwtools vault.
    """

    cmd = [cbwtools_bin()] + args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"cbwtools executable not found. Set CBWTOOLS_BIN or put 'cbwtools' on PATH. "
            f"Original error: {exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"cbwtools timed out while running {cmd!r}") from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(
            f"cbwtools returned non-zero exit code {proc.returncode}. Stderr: {stderr}"
        )

    return (proc.stdout or "").strip()


def get_api_key(provider: ProviderConfig, verbose: bool = False) -> str:
    """Retrieve the API key for a provider.

    Order of precedence:
      1. Environment variable (e.g. OPENROUTER_API_KEY).
      2. `cbwtools get-secret <secret_name> --raw`.

    Raises RuntimeError if no key is found.
    """

    # 1. Environment variable
    key = os.environ.get(provider.env_var)
    if key:
        if verbose:
            typer.echo(f"Using API key from env var {provider.env_var}.")
        return key.strip()

    # 2. cbwtools secret
    try:
        if verbose:
            typer.echo(f"Fetching API key from cbwtools secret '{provider.secret_name}'.")
        key = run_cbwtools(["get-secret", provider.secret_name, "--raw"])
        if key:
            return key.strip()
    except RuntimeError as exc:
        if verbose:
            typer.echo(f"Warning: failed to fetch key from cbwtools: {exc}", err=True)

    raise RuntimeError(
        f"No API key found for provider '{provider.name}'. Set {provider.env_var} "
        f"or store it in cbwtools as '{provider.secret_name}'."
    )


# ---------------------------------------------------------------------------
# Chat history model
# ---------------------------------------------------------------------------

@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant"
    content: str


def build_openrouter_payload(model: str, history: List[ChatMessage]) -> Dict:
    """Build OpenRouter-compatible payload from internal history.

    This uses an OpenAI-compatible /chat/completions format.
    """

    messages = [
        {"role": m.role, "content": m.content}
        for m in history
    ]
    return {
        "model": model,
        "messages": messages,
    }


def build_gemini_payload(history: List[ChatMessage]) -> Dict:
    """Build Gemini-compatible payload from internal history.

    Gemini's REST API expects `contents` with a list of parts.
    We coalesce the conversation into alternating user/assistant turns,
    ignoring explicit system messages (which we prepend to the first user
    turn if present).
    """

    contents: List[Dict] = []
    for msg in history:
        if msg.role == "system":
            # We'll handle system prompts by prepending to next user message in
            # a more advanced version; for now include as its own content.
            role = "user"
        elif msg.role == "assistant":
            role = "model"
        else:
            role = "user"

        contents.append(
            {
                "role": role,
                "parts": [{"text": msg.content}],
            }
        )

    return {"contents": contents}


# ---------------------------------------------------------------------------
# Provider-specific HTTP calls
# ---------------------------------------------------------------------------

def call_openrouter(
    api_key: str,
    model: str,
    history: List[ChatMessage],
    timeout: int = 60,
) -> str:
    """Send chat request to OpenRouter and return the assistant's reply text.

    Note: This assumes an OpenAI-compatible endpoint at
    https://openrouter.ai/api/v1/chat/completions. Adjust the URL or payload
    if your account requires different settings or headers.
    """

    url = f"{PROVIDERS['openrouter'].base_url}/chat/completions"
    payload = build_openrouter_payload(model, history)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # OpenRouter may require an HTTP Referer / X-Title header; configure
        # those via env vars in a future revision if needed.
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(
            f"OpenRouter API error {resp.status_code}: {resp.text[:300]}"
        )

    data = resp.json()
    # OpenAI-style: choices[0].message.content
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected OpenRouter response structure: {data}") from exc


def call_gemini(
    api_key: str,
    model: str,
    history: List[ChatMessage],
    timeout: int = 60,
) -> str:
    """Send chat request to Gemini and return the assistant's reply text.

    Uses the v1beta REST API. You may need to adjust the URL path depending on
    your enabled features and region.
    """

    base = PROVIDERS["gemini"].base_url.rstrip("/")
    url = f"{base}/{model}:generateContent?key={api_key}"
    payload = build_gemini_payload(history)

    resp = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Gemini API error {resp.status_code}: {resp.text[:300]}"
        )

    data = resp.json()
    # Typical: candidates[0].content.parts[0].text
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            raise KeyError("no candidates in response")
        parts = candidates[0]["content"]["parts"]
        if not parts:
            raise KeyError("no parts in response")
        return parts[0].get("text", "")
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Gemini response structure: {data}") from exc


# ---------------------------------------------------------------------------
# Chat loop
# ---------------------------------------------------------------------------

@app.command("chat")
def chat(
    provider: str = typer.Option(
        "openrouter",
        "--provider",
        "-p",
        help="AI provider to use (openrouter, gemini).",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Model identifier for the chosen provider.",
    ),
    system_prompt: str = typer.Option(
        "You are a helpful coding and infrastructure assistant running in a terminal.",
        "--system-prompt",
        help="System instruction that sets the assistant's behavior.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging to stderr.",
    ),
) -> None:
    """Start an interactive chat session in the terminal.

    This command is designed to run nicely inside tmux, but will also work in
    a plain terminal.
    """

    provider_key = provider.lower()
    if provider_key not in PROVIDERS:
        raise typer.BadParameter(
            f"Unknown provider '{provider}'. Supported: {', '.join(PROVIDERS.keys())}"
        )

    cfg = PROVIDERS[provider_key]
    if model is None:
        model = cfg.default_model

    try:
        api_key = get_api_key(cfg, verbose=verbose)
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    if verbose:
        typer.echo(f"Using provider={cfg.name}, model={model}")

    history: List[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]

    typer.echo("\ncbwtools-ai chat session started.")
    typer.echo("Type your message and press Enter. Use /quit to exit, /clear to reset history.\n")

    while True:
        try:
            user_input = input("you> ")
        except (EOFError, KeyboardInterrupt):
            typer.echo("\nExiting chat.")
            break

        user_input = user_input.strip()
        if not user_input:
            continue
        if user_input in {"/quit", "/exit"}:
            typer.echo("Goodbye.")
            break
        if user_input == "/clear":
            history = [ChatMessage(role="system", content=system_prompt)]
            typer.echo("History cleared.")
            continue

        # Append user message
        history.append(ChatMessage(role="user", content=user_input))

        try:
            if cfg.name == "openrouter":
                reply = call_openrouter(api_key=api_key, model=model, history=history)
            elif cfg.name == "gemini":
                reply = call_gemini(api_key=api_key, model=model, history=history)
            else:
                raise RuntimeError(f"Provider '{cfg.name}' not implemented.")
        except Exception as exc:  # noqa: BLE001 - we want a broad catch for CLI use
            typer.echo(f"Error during API call: {exc}", err=True)
            if verbose:
                import traceback

                traceback.print_exc()
            # Don't append an assistant message if the call failed.
            continue

        # Append assistant reply to history and print it.
        history.append(ChatMessage(role="assistant", content=reply))
        for line in reply.splitlines():
            print(f"ai > {line}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point for cbwtools-ai."""

    try:
        app()
    except KeyboardInterrupt:
        # Graceful exit on Ctrl-C
        typer.echo("\nInterrupted.")
        raise SystemExit(130)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
