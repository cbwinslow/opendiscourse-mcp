#!/usr/bin/env python3
# =============================================================================
# Script Name   : cbwtools.py
# Author        : cbwinslow (generated with GPT-5.1 Thinking)
# Created       : 2025-11-19
# Summary       : Personal GitHub-backed encrypted vault + shortcuts manager.
#                 Provides a CLI wrapper around the GitHub API, symmetric
#                 encryption for secrets and bundles, and optional Bitwarden
#                 integration for searching and retrieving secrets.
#
# Inputs        : CLI arguments and subcommands (see --help for details).
# Outputs       : Encrypted files pushed to a GitHub repo, local config files,
#                 log file, and decrypted values printed to stdout when
#                 requested.
#
# Dependencies  : Python 3.9+, packages:
#                   - typer
#                   - pyyaml
#                   - cryptography
#                   - PyGithub
#                 Optional:
#                   - bitwarden-cli (`bw`) for Bitwarden integration
#
# Usage         :
#   python cbwtools.py init
#   python cbwtools.py add-secret "openai/api_key"
#   python cbwtools.py get-secret "openai/api_key"
#   python cbwtools.py list-secrets
#   python cbwtools.py save-folder-bundle ./myfolder myfolder-backup
#   python cbwtools.py fetch-folder-bundle myfolder-backup ./restore-here
#
# Modification Log:
#   2025-11-19 - Initial version (MVP) with:
#                  * Config management (YAML)
#                  * Symmetric encryption (Fernet/AES)
#                  * GitHub-backed secret storage
#                  * Folder bundle upload/download
#                  * Bitwarden search/lookup wrappers
# =============================================================================

import json
import logging
import os
import sys
import tarfile
from dataclasses import dataclass
from datetime import datetime
from getpass import getpass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import typer
import yaml
from cryptography.fernet import Fernet, InvalidToken
from github import Github, GithubException
from github.ContentFile import ContentFile

# -----------------------------------------------------------------------------
# Constants & Global Configuration
# -----------------------------------------------------------------------------

APP_NAME = "cbwtools"
CONFIG_DIR = Path(os.environ.get("CBWTOOLS_CONFIG_DIR", Path.home() / ".config" / APP_NAME))
CONFIG_PATH = CONFIG_DIR / "config.yml"
KEY_PATH = CONFIG_DIR / "symkey.key"
LOG_PATH = Path(os.environ.get("CBWTOOLS_LOG_PATH", f"/tmp/CBW-{APP_NAME}.log"))

DEFAULT_INDEX_PATH = "index.yml"  # Path inside GitHub repo
DEFAULT_GITHUB_REPO = "cbwinslow/cbwtools-vault"  # You can change this in config later
DEFAULT_BRANCH = "main"

app = typer.Typer(help="cbwtools: GitHub-backed encrypted vault & shortcuts manager")

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------

def setup_logging() -> None:
    """Configure logging for the tool.

    Logs are written to a temporary file and also to stderr for visibility.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )
    logging.debug("Logging initialized at %s", LOG_PATH)


# -----------------------------------------------------------------------------
# Data Classes & Config Management
# -----------------------------------------------------------------------------

@dataclass
class GitHubConfig:
    token_env: str = "GITHUB_TOKEN"
    repo_full_name: str = DEFAULT_GITHUB_REPO
    default_branch: str = DEFAULT_BRANCH


@dataclass
class EncryptionConfig:
    method: str = "fernet"
    key_path: str = str(KEY_PATH)


@dataclass
class BitwardenConfig:
    enabled: bool = True
    bw_path: str = "bw"  # Path to Bitwarden CLI
    session_env: str = "BW_SESSION"


@dataclass
class AppConfig:
    github: GitHubConfig
    encryption: EncryptionConfig
    bitwarden: BitwardenConfig
    index_path: str = DEFAULT_INDEX_PATH

    def to_dict(self) -> Dict[str, Any]:
        # Convert dataclass instance to dictionary for YAML serialization.
        return {
            "github": {
                "token_env": self.github.token_env,
                "repo_full_name": self.github.repo_full_name,
                "default_branch": self.github.default_branch,
            },
            "encryption": {
                "method": self.encryption.method,
                "key_path": self.encryption.key_path,
            },
            "bitwarden": {
                "enabled": self.bitwarden.enabled,
                "bw_path": self.bitwarden.bw_path,
                "session_env": self.bitwarden.session_env,
            },
            "index_path": self.index_path,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AppConfig":
        # Create AppConfig from dictionary (e.g., loaded from YAML file).
        github = data.get("github", {})
        encryption = data.get("encryption", {})
        bitwarden = data.get("bitwarden", {})
        return AppConfig(
            github=GitHubConfig(
                token_env=github.get("token_env", "GITHUB_TOKEN"),
                repo_full_name=github.get("repo_full_name", DEFAULT_GITHUB_REPO),
                default_branch=github.get("default_branch", DEFAULT_BRANCH),
            ),
            encryption=EncryptionConfig(
                method=encryption.get("method", "fernet"),
                key_path=encryption.get("key_path", str(KEY_PATH)),
            ),
            bitwarden=BitwardenConfig(
                enabled=bitwarden.get("enabled", True),
                bw_path=bitwarden.get("bw_path", "bw"),
                session_env=bitwarden.get("session_env", "BW_SESSION"),
            ),
            index_path=data.get("index_path", DEFAULT_INDEX_PATH),
        )


def load_config() -> AppConfig:
    """Load the application configuration from YAML.

    If the file does not exist, a minimal default configuration is returned.
    """
    if not CONFIG_PATH.exists():
        logging.warning("Config file not found at %s, using defaults.", CONFIG_PATH)
        return AppConfig(
            github=GitHubConfig(),
            encryption=EncryptionConfig(),
            bitwarden=BitwardenConfig(),
            index_path=DEFAULT_INDEX_PATH,
        )

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        config = AppConfig.from_dict(data)
        logging.info("Loaded config from %s", CONFIG_PATH)
        return config
    except Exception as exc:
        logging.error("Failed to load config: %s", exc)
        raise typer.Exit(code=1)


def save_config(config: AppConfig) -> None:
    """Persist the configuration to disk in YAML format."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            yaml.safe_dump(config.to_dict(), f, sort_keys=False)
        logging.info("Saved config to %s", CONFIG_PATH)
    except Exception as exc:
        logging.error("Failed to save config: %s", exc)
        raise typer.Exit(code=1)


# -----------------------------------------------------------------------------
# Symmetric Encryption Helpers (Fernet / AES)
# -----------------------------------------------------------------------------

def load_or_create_key(enc_cfg: EncryptionConfig) -> bytes:
    """Load the symmetric key from disk or create it if it does not exist.

    The key is stored in a file with restricted permissions. This key should be
    backed up securely (e.g., in Bitwarden) because it is required to decrypt
    all stored secrets and bundles.
    """
    key_path = Path(enc_cfg.key_path)
    if key_path.exists():
        logging.debug("Loading encryption key from %s", key_path)
        return key_path.read_bytes()

    logging.info("Encryption key not found, generating a new key at %s", key_path)
    key = Fernet.generate_key()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    # Write key with restricted permissions to avoid leaking it.
    with open(key_path, "wb") as f:
        f.write(key)
    try:
        os.chmod(key_path, 0o600)
    except PermissionError:
        # On some systems (e.g., Windows), chmod might not be supported fully.
        logging.warning("Could not set restrictive permissions on key file.")
    return key


def get_fernet(enc_cfg: EncryptionConfig) -> Fernet:
    """Create a Fernet instance using the configured symmetric key."""
    if enc_cfg.method != "fernet":
        logging.error("Unsupported encryption method: %s", enc_cfg.method)
        raise typer.Exit(code=1)
    key = load_or_create_key(enc_cfg)
    return Fernet(key)


def encrypt_bytes(fernet: Fernet, data: bytes) -> bytes:
    """Encrypt raw bytes using Fernet."""
    return fernet.encrypt(data)


def decrypt_bytes(fernet: Fernet, token: bytes) -> bytes:
    """Decrypt raw bytes using Fernet.

    Raises typer.Exit if the token cannot be decrypted with the current key.
    """
    try:
        return fernet.decrypt(token)
    except InvalidToken:
        logging.error("Failed to decrypt data: invalid token or key.")
        raise typer.Exit(code=1)


# -----------------------------------------------------------------------------
# GitHub Helpers
# -----------------------------------------------------------------------------

def get_github_client(gh_cfg: GitHubConfig) -> Github:
    """Instantiate a GitHub client using a token from the environment."""
    token = os.environ.get(gh_cfg.token_env)
    if not token:
        logging.error("GitHub token not found in environment variable %s", gh_cfg.token_env)
        typer.echo(f"ERROR: GitHub token not found in env var {gh_cfg.token_env}", err=True)
        raise typer.Exit(code=1)
    return Github(token)


def get_repo_and_index(
    config: AppConfig,
) -> Tuple[Any, Dict[str, Any], Optional[ContentFile]]:
    """Fetch the GitHub repository and the index YAML file contents.

    Returns:
        (repo, index_data, index_content_file)

    where index_data is a deserialized dictionary (empty if missing) and
    index_content_file is the ContentFile object or None if not found.
    """
    gh = get_github_client(config.github)
    try:
        repo = gh.get_repo(config.github.repo_full_name)
    except GithubException as exc:
        logging.error("Could not open repo %s: %s", config.github.repo_full_name, exc)
        typer.echo(f"ERROR: Could not open repo {config.github.repo_full_name}", err=True)
        raise typer.Exit(code=1)

    index_data: Dict[str, Any] = {"secrets": {}, "bundles": {}, "shortcuts": {}, "repos": {}, "folders": {}, "scripts": {}}
    index_cf: Optional[ContentFile] = None
    try:
        index_cf = repo.get_contents(config.index_path, ref=config.github.default_branch)
        index_data = yaml.safe_load(index_cf.decoded_content.decode("utf-8")) or index_data
        logging.info("Loaded index from %s", config.index_path)
    except GithubException as exc:
        if exc.status == 404:
            logging.warning("Index file %s not found, starting fresh.", config.index_path)
        else:
            logging.error("Error loading index file: %s", exc)
            raise typer.Exit(code=1)

    # Ensure top-level keys exist
    for key in ("secrets", "bundles", "shortcuts", "repos", "folders", "scripts"):
        index_data.setdefault(key, {})

    return repo, index_data, index_cf


def save_index(
    repo: Any,
    config: AppConfig,
    index_data: Dict[str, Any],
    index_cf: Optional[ContentFile],
    message: str,
) -> None:
    """Persist the index YAML back to the GitHub repository."""
    encoded = yaml.safe_dump(index_data, sort_keys=False).encode("utf-8")
    content_str = encoded.decode("utf-8")

    try:
        if index_cf is None:
            # Create new index file
            repo.create_file(
                path=config.index_path,
                message=message,
                content=content_str,
                branch=config.github.default_branch,
            )
            logging.info("Created index file %s", config.index_path)
        else:
            # Update existing index file
            repo.update_file(
                path=config.index_path,
                message=message,
                content=content_str,
                sha=index_cf.sha,
                branch=config.github.default_branch,
            )
            logging.info("Updated index file %s", config.index_path)
    except GithubException as exc:
        logging.error("Failed to save index file: %s", exc)
        raise typer.Exit(code=1)


def upload_blob(
    repo: Any,
    path: str,
    data: bytes,
    branch: str,
    commit_message: str,
) -> None:
    """Upload or update a file in the repository at the given path."""
    content_str = data.decode("utf-8") if isinstance(data, bytes) else str(data)
    try:
        existing = repo.get_contents(path, ref=branch)
        repo.update_file(
            path=path,
            message=commit_message,
            content=content_str,
            sha=existing.sha,
            branch=branch,
        )
        logging.info("Updated file %s in repo", path)
    except GithubException as exc:
        if exc.status == 404:
            repo.create_file(
                path=path,
                message=commit_message,
                content=content_str,
                branch=branch,
            )
            logging.info("Created file %s in repo", path)
        else:
            logging.error("Failed to upload blob to %s: %s", path, exc)
            raise typer.Exit(code=1)


def download_blob(repo: Any, path: str, branch: str) -> bytes:
    """Download file content as bytes from the repository."""
    try:
        cf = repo.get_contents(path, ref=branch)
        logging.info("Downloaded file %s from repo", path)
        return cf.decoded_content
    except GithubException as exc:
        logging.error("Failed to download blob from %s: %s", path, exc)
        raise typer.Exit(code=1)


# -----------------------------------------------------------------------------
# Bitwarden Helpers
# -----------------------------------------------------------------------------

def bw_run(bw_cfg: BitwardenConfig, args: list) -> str:
    """Run a Bitwarden CLI command and return stdout as text.

    This expects BW_SESSION to be set in the environment for non-interactive
    usage. You can unlock Bitwarden manually and export BW_SESSION before
    running cbwtools, or you can extend this function to perform `bw unlock`
    interactively.
    """
    if not bw_cfg.enabled:
        typer.echo("Bitwarden integration is disabled in config.", err=True)
        raise typer.Exit(code=1)

    import subprocess

    cmd = [bw_cfg.bw_path] + args
    env = os.environ.copy()
    if not env.get(bw_cfg.session_env):
        typer.echo(
            f"ERROR: Bitwarden session env var {bw_cfg.session_env} not set. "
            f"Run `bw unlock` and export the session first.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        result = subprocess.run(
            cmd,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as exc:
        logging.error("Bitwarden command failed: %s", exc.stderr)
        typer.echo(f"ERROR: Bitwarden command failed: {exc.stderr}", err=True)
        raise typer.Exit(code=1)


def bw_search_items(bw_cfg: BitwardenConfig, query: str) -> Any:
    """Search Bitwarden items that match the given query string."""
    out = bw_run(bw_cfg, ["list", "items", f'--search={query}', "--raw"])
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        logging.error("Failed to parse Bitwarden output.")
        raise typer.Exit(code=1)


def bw_get_item(bw_cfg: BitwardenConfig, item_id: str) -> Any:
    """Retrieve a specific Bitwarden item by ID."""
    out = bw_run(bw_cfg, ["get", "item", item_id, "--raw"])
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        logging.error("Failed to parse Bitwarden item JSON.")
        raise typer.Exit(code=1)


# -----------------------------------------------------------------------------
# Utility: Folder Bundling
# -----------------------------------------------------------------------------

def create_tarball(source_dir: Path) -> bytes:
    """Create a gzipped tarball from the specified folder and return bytes."""
    if not source_dir.is_dir():
        typer.echo(f"ERROR: Source directory {source_dir} does not exist or is not a directory.", err=True)
        raise typer.Exit(code=1)

    import io

    buf = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=buf) as tar:
        tar.add(str(source_dir), arcname=source_dir.name)
    buf.seek(0)
    return buf.read()


def extract_tarball(data: bytes, target_dir: Path) -> None:
    """Extract a gzipped tarball bytes object into the target directory."""
    import io

    target_dir.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(data)
    with tarfile.open(mode="r:gz", fileobj=buf) as tar:
        tar.extractall(path=target_dir)


# -----------------------------------------------------------------------------
# CLI Commands
# -----------------------------------------------------------------------------


def make_safe_name(name: str) -> str:
    """Convert a logical name into a filesystem-safe identifier."""
    return name.replace("/", "_").replace(" ", "_")


# -----------------------------------------------------------------------------
# Secret & Bundle Commands
# -----------------------------------------------------------------------------

@app.command()
def init(
    repo_full_name: str = typer.Option(
        DEFAULT_GITHUB_REPO,
        "--repo",
        "-r",
        help="GitHub repo to store encrypted data (e.g., user/repo).",
    ),
    github_token_env: str = typer.Option(
        "GITHUB_TOKEN",
        "--token-env",
        help="Environment variable containing the GitHub token.",
    ),
    bitwarden_enabled: bool = typer.Option(
        True,
        "--bw/--no-bw",
        help="Enable or disable Bitwarden integration.",
    ),
):
    """Initialize cbwtools configuration and encryption key.

    This command creates a config file and generates a symmetric key if
    necessary. It does not push anything to GitHub yet.
    """
    setup_logging()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config = AppConfig(
        github=GitHubConfig(
            token_env=github_token_env,
            repo_full_name=repo_full_name,
            default_branch=DEFAULT_BRANCH,
        ),
        encryption=EncryptionConfig(
            method="fernet",
            key_path=str(KEY_PATH),
        ),
        bitwarden=BitwardenConfig(
            enabled=bitwarden_enabled,
            bw_path="bw",
            session_env="BW_SESSION",
        ),
        index_path=DEFAULT_INDEX_PATH,
    )

    # Ensure key exists
    _ = load_or_create_key(config.encryption)

    save_config(config)
    typer.echo(f"Initialized {APP_NAME} with config at {CONFIG_PATH}")
    typer.echo(f"Encryption key stored at {config.encryption.key_path}")
    typer.echo("Remember to BACK UP this key file securely (e.g., Bitwarden).")


@app.command("add-secret")
def add_secret(
    name: str = typer.Argument(..., help="Logical name for the secret, e.g. 'openai/api_key'."),
    from_stdin: bool = typer.Option(
        False,
        "--stdin",
        help="Read the secret value from stdin instead of interactive prompt.",
    ),
):
    """Encrypt and store a secret in the GitHub-backed vault."""
    setup_logging()
    config = load_config()
    fernet = get_fernet(config.encryption)
    repo, index_data, index_cf = get_repo_and_index(config)

    if name in index_data["secrets"]:
        overwrite = typer.confirm(f"Secret '{name}' already exists. Overwrite?", default=False)
        if not overwrite:
            typer.echo("Aborting.")
            raise typer.Exit(code=0)

    if from_stdin:
        secret_value = sys.stdin.read().strip()
    else:
        secret_value = getpass(f"Enter value for secret '{name}': ").strip()

    if not secret_value:
        typer.echo("ERROR: Secret value cannot be empty.", err=True)
        raise typer.Exit(code=1)

    encrypted = encrypt_bytes(fernet, secret_value.encode("utf-8"))
    now = datetime.utcnow().isoformat() + "Z"
    # Store under a deterministic path for this secret
    safe_name = name.replace("/", "_")
    secret_path = f"secrets/{safe_name}.enc"

    upload_blob(
        repo=repo,
        path=secret_path,
        data=encrypted,
        branch=config.github.default_branch,
        commit_message=f"cbwtools: store secret {name}",
    )

    index_data["secrets"][name] = {
        "path": secret_path,
        "created_at": now,
        "updated_at": now,
    }

    save_index(
        repo=repo,
        config=config,
        index_data=index_data,
        index_cf=index_cf,
        message=f"cbwtools: update index for secret {name}",
    )

    typer.echo(f"Stored secret '{name}' at {secret_path} in repo {config.github.repo_full_name}.")


@app.command("get-secret")
def get_secret(
    name: str = typer.Argument(..., help="Logical name for the secret to retrieve."),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Print only the secret value (no labels) for easy scripting.",
    ),
):
    """Retrieve and decrypt a secret from the GitHub-backed vault."""
    setup_logging()
    config = load_config()
    fernet = get_fernet(config.encryption)
    repo, index_data, _ = get_repo_and_index(config)

    meta = index_data["secrets"].get(name)
    if not meta:
        typer.echo(f"ERROR: Secret '{name}' not found in index.", err=True)
        raise typer.Exit(code=1)

    secret_path = meta["path"]
    encrypted = download_blob(
        repo=repo,
        path=secret_path,
        branch=config.github.default_branch,
    )
    value = decrypt_bytes(fernet, encrypted).decode("utf-8")
    if raw:
        typer.echo(value)
    else:
        typer.echo(f"{name} = {value}")


@app.command("list-secrets")
def list_secrets():
    """List all secret names stored in the index."""
    setup_logging()
    config = load_config()
    _, index_data, _ = get_repo_and_index(config)

    secrets = index_data.get("secrets", {})
    if not secrets:
        typer.echo("No secrets stored yet.")
        return

    typer.echo("Stored secrets:")
    for name, meta in secrets.items():
        created = meta.get("created_at", "?")
        updated = meta.get("updated_at", "?")
        typer.echo(f"  - {name} (created: {created}, updated: {updated})")


@app.command("save-folder-bundle")
def save_folder_bundle(
    source_dir: Path = typer.Argument(..., exists=True, file_okay=False, help="Folder to tar, encrypt, and upload."),
    bundle_name: str = typer.Argument(..., help="Logical name for the bundle (e.g. 'dotfiles')."),
):
    """Create an encrypted tarball of a folder and push it to GitHub."""
    setup_logging()
    config = load_config()
    fernet = get_fernet(config.encryption)
    repo, index_data, index_cf = get_repo_and_index(config)

    tar_bytes = create_tarball(source_dir)
    encrypted = encrypt_bytes(fernet, tar_bytes)

    safe_name = bundle_name.replace("/", "_")
    bundle_path = f"bundles/{safe_name}.tgz.enc"
    now = datetime.utcnow().isoformat() + "Z"

    upload_blob(
        repo=repo,
        path=bundle_path,
        data=encrypted,
        branch=config.github.default_branch,
        commit_message=f"cbwtools: save bundle {bundle_name}",
    )

    index_data["bundles"][bundle_name] = {
        "path": bundle_path,
        "source_dir_name": source_dir.name,
        "created_at": now,
        "updated_at": now,
    }

    save_index(
        repo=repo,
        config=config,
        index_data=index_data,
        index_cf=index_cf,
        message=f"cbwtools: update index for bundle {bundle_name}",
    )

    typer.echo(f"Saved bundle '{bundle_name}' from folder {source_dir} to {bundle_path}.")


@app.command("fetch-folder-bundle")
def fetch_folder_bundle(
    bundle_name: str = typer.Argument(..., help="Logical name of bundle to fetch."),
    target_dir: Path = typer.Argument(..., help="Destination folder to extract into."),
):
    """Download, decrypt, and extract a previously saved folder bundle."""
    setup_logging()
    config = load_config()
    fernet = get_fernet(config.encryption)
    repo, index_data, _ = get_repo_and_index(config)

    meta = index_data["bundles"].get(bundle_name)
    if not meta:
        typer.echo(f"ERROR: Bundle '{bundle_name}' not found in index.", err=True)
        raise typer.Exit(code=1)

    bundle_path = meta["path"]
    encrypted = download_blob(
        repo=repo,
        path=bundle_path,
        branch=config.github.default_branch,
    )
    tar_bytes = decrypt_bytes(fernet, encrypted)
    extract_tarball(tar_bytes, target_dir)
    typer.echo(f"Extracted bundle '{bundle_name}' into {target_dir}")


@app.command("bw-search")
def bw_search(
    query: str = typer.Argument(..., help="Search string for Bitwarden items."),
    limit: int = typer.Option(10, "--limit", "-n", help="Limit number of items shown."),
):
    """Search Bitwarden items via the CLI and display basic info."""
    setup_logging()
    config = load_config()
    if not config.bitwarden.enabled:
        typer.echo("Bitwarden integration is disabled.", err=True)
        raise typer.Exit(code=1)

    items = bw_search_items(config.bitwarden, query)
    if not items:
        typer.echo("No Bitwarden items found.")
        return

    typer.echo(f"Found {len(items)} items (showing up to {limit}):")
    for item in items[:limit]:
        typer.echo(f"- {item.get('id')} :: {item.get('name')} :: {item.get('login', {}).get('username')}")


@app.command("bw-get")
def bw_get(
    item_id: str = typer.Argument(..., help="Bitwarden item ID to fetch."),
):
    """Fetch a Bitwarden item and print its JSON representation."""
    setup_logging()
    config = load_config()
    if not config.bitwarden.enabled:
        typer.echo("Bitwarden integration is disabled.", err=True)
        raise typer.Exit(code=1)

    item = bw_get_item(config.bitwarden, item_id)
    typer.echo(json.dumps(item, indent=2))


@app.command("show-config")
@app.command("add-shortcut")
def add_shortcut(
    name: str = typer.Argument(..., help="Logical name for the shortcut, e.g. 'deploy/app'."),
    command: str = typer.Option(
        None,
        "--command",
        "-c",
        help="Shell command to run when this shortcut is invoked.",
    ),
):
    """Create or update a shell-command shortcut stored in the index."""
    setup_logging()
    config = load_config()
    repo, index_data, index_cf = get_repo_and_index(config)

    if command is None:
        command = typer.prompt(f"Enter shell command for shortcut '{name}'")

    now = datetime.utcnow().isoformat() + "Z"
    index_data.setdefault("shortcuts", {})
    index_data["shortcuts"][name] = {
        "type": "command",
        "command": command,
        "created_at": index_data["shortcuts"].get(name, {}).get("created_at", now),
        "updated_at": now,
    }

    save_index(
        repo=repo,
        config=config,
        index_data=index_data,
        index_cf=index_cf,
        message=f"cbwtools: update shortcut {name}",
    )

    typer.echo(f"Shortcut '{name}' saved: {command}")


@app.command("list-shortcuts")
def list_shortcuts():
    """List all shortcuts stored in the index."""
    setup_logging()
    config = load_config()
    _, index_data, _ = get_repo_and_index(config)

    shortcuts = index_data.get("shortcuts", {})
    if not shortcuts:
        typer.echo("No shortcuts defined yet.")
        return

    typer.echo("Shortcuts:")
    for name, meta in shortcuts.items():
        typer.echo(f"  - {name}: {meta.get('command')} (type={meta.get('type', 'command')})")


@app.command("run-shortcut")
def run_shortcut(
    name: str = typer.Argument(..., help="Name of the shortcut to run."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the command without executing it."),
    no_confirm: bool = typer.Option(False, "--yes", "-y", help="Run without confirmation."),
):
    """Execute a shortcut's shell command locally."""
    setup_logging()
    config = load_config()
    _, index_data, _ = get_repo_and_index(config)

    meta = index_data.get("shortcuts", {}).get(name)
    if not meta:
        typer.echo(f"ERROR: Shortcut '{name}' not found.", err=True)
        raise typer.Exit(code=1)

    cmd = meta.get("command")
    if not cmd:
        typer.echo(f"ERROR: Shortcut '{name}' has no command defined.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Shortcut '{name}' -> {cmd}")
    if dry_run:
        typer.echo("[dry run] Command not executed.")
        return

    if not no_confirm and not typer.confirm("Execute this command?", default=False):
        typer.echo("Aborted.")
        raise typer.Exit(code=0)

    import subprocess

    try:
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            typer.echo(f"Command exited with code {result.returncode}", err=True)
            raise typer.Exit(code=result.returncode)
    except OSError as exc:
        typer.echo(f"ERROR: Failed to run command: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("add-repo-alias")
def add_repo_alias(
    name: str = typer.Argument(..., help="Alias name for the repository."),
    url: str = typer.Argument(..., help="Git repository URL (SSH or HTTPS)."),
    default_path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Default local path to clone/pull this repo.",
    ),
):
    """Register a Git repository alias in the index."""
    setup_logging()
    config = load_config()
    repo, index_data, index_cf = get_repo_and_index(config)

    now = datetime.utcnow().isoformat() + "Z"
    index_data.setdefault("repos", {})
    index_data["repos"][name] = {
        "url": url,
        "default_path": str(default_path) if default_path else "",
        "created_at": index_data["repos"].get(name, {}).get("created_at", now),
        "updated_at": now,
    }

    save_index(
        repo=repo,
        config=config,
        index_data=index_data,
        index_cf=index_cf,
        message=f"cbwtools: update repo alias {name}",
    )

    typer.echo(f"Repo alias '{name}' -> {url} (default_path={default_path or '<cwd>/<name>'})")


@app.command("list-repo-aliases")
def list_repo_aliases():
    """List all repository aliases."""
    setup_logging()
    config = load_config()
    _, index_data, _ = get_repo_and_index(config)

    repos = index_data.get("repos", {})
    if not repos:
        typer.echo("No repo aliases defined yet.")
        return

    typer.echo("Repository aliases:")
    for name, meta in repos.items():
        typer.echo(f"  - {name}: {meta.get('url')} (default_path={meta.get('default_path') or '<cwd>/<name>'})")


@app.command("clone-repo-alias")
def clone_repo_alias(
    name: str = typer.Argument(..., help="Name of the repo alias to clone."),
    dest: Optional[Path] = typer.Argument(
        None,
        help="Destination directory (defaults to alias default_path or ./<name>).",
    ),
):
    """Clone a repository using a stored alias."""
    setup_logging()
    config = load_config()
    _, index_data, _ = get_repo_and_index(config)

    meta = index_data.get("repos", {}).get(name)
    if not meta:
        typer.echo(f"ERROR: Repo alias '{name}' not found.", err=True)
        raise typer.Exit(code=1)

    url = meta.get("url")
    default_path_str = meta.get("default_path") or ""
    if dest is None:
        dest = Path(default_path_str) if default_path_str else Path.cwd() / name

    if dest.exists() and any(dest.iterdir()):
        if not typer.confirm(f"Destination {dest} exists and is not empty. Continue?", default=False):
            typer.echo("Aborted.")
            raise typer.Exit(code=0)

    dest.parent.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Cloning {url} -> {dest}")

    import subprocess

    try:
        result = subprocess.run(["git", "clone", url, str(dest)])
        if result.returncode != 0:
            typer.echo(f"git clone exited with code {result.returncode}", err=True)
            raise typer.Exit(code=result.returncode)
    except OSError as exc:
        typer.echo(f"ERROR: Failed to run git clone: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("add-folder-alias")
def add_folder_alias(
    name: str = typer.Argument(..., help="Alias name for the folder."),
    path: Path = typer.Argument(..., help="Local folder path to alias."),
    notes: str = typer.Option("", "--notes", help="Optional notes/description."),
):
    """Register a local folder alias (for quick recall)."""
    setup_logging()
    config = load_config()
    repo, index_data, index_cf = get_repo_and_index(config)

    if not path.exists() or not path.is_dir():
        typer.echo(f"ERROR: {path} does not exist or is not a directory.", err=True)
        raise typer.Exit(code=1)

    now = datetime.utcnow().isoformat() + "Z"
    index_data.setdefault("folders", {})
    index_data["folders"][name] = {
        "path": str(path.resolve()),
        "notes": notes,
        "created_at": index_data["folders"].get(name, {}).get("created_at", now),
        "updated_at": now,
    }

    save_index(
        repo=repo,
        config=config,
        index_data=index_data,
        index_cf=index_cf,
        message=f"cbwtools: update folder alias {name}",
    )

    typer.echo(f"Folder alias '{name}' -> {path}")


@app.command("list-folder-aliases")
def list_folder_aliases():
    """List all folder aliases."""
    setup_logging()
    config = load_config()
    _, index_data, _ = get_repo_and_index(config)

    folders = index_data.get("folders", {})
    if not folders:
        typer.echo("No folder aliases defined yet.")
        return

    typer.echo("Folder aliases:")
    for name, meta in folders.items():
        typer.echo(f"  - {name}: {meta.get('path')} ({meta.get('notes', '')})")


@app.command("add-script")
def add_script(
    name: str = typer.Argument(..., help="Logical name for the script (e.g. 'install/dev-env')."),
    file: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="Path to script file to upload (otherwise read from stdin).",
    ),
    language: str = typer.Option(
        "bash",
        "--lang",
        "-l",
        help="Script language: 'bash' or 'python' (affects how it's executed).",
    ),
):
    """Encrypt and store an installation/script snippet in the vault."""
    setup_logging()
    config = load_config()
    fernet = get_fernet(config.encryption)
    repo, index_data, index_cf = get_repo_and_index(config)

    if file is not None:
        if not file.exists() or not file.is_file():
            typer.echo(f"ERROR: Script file {file} does not exist.", err=True)
            raise typer.Exit(code=1)
        data = file.read_bytes()
    else:
        typer.echo("Reading script content from stdin. Press Ctrl-D when done.")
        data = sys.stdin.read().encode("utf-8")

    if not data:
        typer.echo("ERROR: Script content cannot be empty.", err=True)
        raise typer.Exit(code=1)

    encrypted = encrypt_bytes(fernet, data)
    now = datetime.utcnow().isoformat() + "Z"

    ext = ".sh" if language.lower() == "bash" else ".py" if language.lower() == "python" else ".txt"
    safe_name = make_safe_name(name)
    script_path = f"scripts/{safe_name}{ext}.enc"

    upload_blob(
        repo=repo,
        path=script_path,
        data=encrypted,
        branch=config.github.default_branch,
        commit_message=f"cbwtools: store script {name}",
    )

    index_data.setdefault("scripts", {})
    index_data["scripts"][name] = {
        "path": script_path,
        "language": language.lower(),
        "created_at": index_data["scripts"].get(name, {}).get("created_at", now),
        "updated_at": now,
    }

    save_index(
        repo=repo,
        config=config,
        index_data=index_data,
        index_cf=index_cf,
        message=f"cbwtools: update index for script {name}",
    )

    typer.echo(f"Script '{name}' stored at {script_path} (lang={language}).")


@app.command("list-scripts")
def list_scripts():
    """List all stored scripts."""
    setup_logging()
    config = load_config()
    _, index_data, _ = get_repo_and_index(config)

    scripts = index_data.get("scripts", {})
    if not scripts:
        typer.echo("No scripts stored yet.")
        return

    typer.echo("Stored scripts:")
    for name, meta in scripts.items():
        typer.echo(
            f"  - {name}: {meta.get('path')} (lang={meta.get('language')}, "
            f"created={meta.get('created_at')})"
        )


@app.command("run-script")
def run_script(
    name: str = typer.Argument(..., help="Name of the stored script to execute."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would run without executing."),
    no_confirm: bool = typer.Option(False, "--yes", "-y", help="Run without confirmation."),
):
    """Fetch, decrypt, and execute a stored script snippet."""
    setup_logging()
    config = load_config()
    fernet = get_fernet(config.encryption)
    repo, index_data, _ = get_repo_and_index(config)

    meta = index_data.get("scripts", {}).get(name)
    if not meta:
        typer.echo(f"ERROR: Script '{name}' not found.", err=True)
        raise typer.Exit(code=1)

    script_path = meta.get("path")
    language = meta.get("language", "bash").lower()

    encrypted = download_blob(
        repo=repo,
        path=script_path,
        branch=config.github.default_branch,
    )
    data = decrypt_bytes(fernet, encrypted)

    import tempfile
    import os
    import subprocess

    suffix = ".sh" if language == "bash" else ".py" if language == "python" else ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    os.chmod(tmp_path, 0o700)

    if language == "bash":
        cmd = ["bash", str(tmp_path)]
    elif language == "python":
        cmd = [sys.executable, str(tmp_path)]
    else:
        cmd = [str(tmp_path)]

    typer.echo(f"Prepared script '{name}' at {tmp_path} (lang={language}).")
    typer.echo(f"Command: {' '.join(cmd)}")

    if dry_run:
        typer.echo("[dry run] Script not executed.")
        return

    if not no_confirm and not typer.confirm("Execute this script?", default=False):
        typer.echo("Aborted.")
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise typer.Exit(code=0)

    try:
        result = subprocess.run(cmd)
        if result.returncode != 0:
            typer.echo(f"Script exited with code {result.returncode}", err=True)
            raise typer.Exit(code=result.returncode)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


@app.command("show-config")
def show_config():
    """Print the current configuration values (excluding secret key contents)."""
    setup_logging()
    config = load_config()
    data = config.to_dict()
    # Do NOT print key file contents; path is fine.
    typer.echo(yaml.safe_dump(data, sort_keys=False))


# -----------------------------------------------------------------------------
# Main Entrypoint
# -----------------------------------------------------------------------------

def main() -> None:
    """Main entrypoint for cbwtools CLI."""
    try:
        app()
    except KeyboardInterrupt:
        typer.echo("Interrupted by user.", err=True)
        sys.exit(130)


if __name__ == "__main__":
    main()
