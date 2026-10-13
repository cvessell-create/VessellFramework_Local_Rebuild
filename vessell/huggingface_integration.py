# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Hugging Face Hub and Inference API client integration for VessellFramework."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

try:
    import huggingface_hub
    from huggingface_hub import HfApi, InferenceClient, hf_hub_download

    HAS_HF_HUB = True
except ImportError:  # pragma: no cover
    HAS_HF_HUB = False


@dataclass(frozen=True)
class HuggingFaceConfig:
    """Configuration options for Hugging Face integration."""

    token: str | None = None
    endpoint: str | None = None
    timeout: float = 30.0

    @classmethod
    def from_env(cls, token: str | None = None) -> HuggingFaceConfig:
        """Resolve configuration from parameters and environment variables."""
        resolved_token = (
            token
            or os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGINGFACE_HUB_TOKEN")
        )
        endpoint = os.environ.get("HF_ENDPOINT")
        return cls(token=resolved_token, endpoint=endpoint)


class HuggingFaceIntegrationError(Exception):
    """Raised when a Hugging Face API or hub operation fails."""


class HuggingFaceClient:
    """Client for Hugging Face Hub metadata discovery and Inference API execution."""

    def __init__(self, config: HuggingFaceConfig | None = None, api: Any = None) -> None:
        self.config = config or HuggingFaceConfig.from_env()
        self._api: Any = api
        self._inference: Any = None

    @property
    def is_available(self) -> bool:
        """Check if huggingface_hub library is installed."""
        return HAS_HF_HUB

    @property
    def api(self) -> Any:
        """Lazily initialize and return HfApi instance."""
        if not HAS_HF_HUB:
            raise HuggingFaceIntegrationError(
                "huggingface_hub is not installed. Install with: pip install huggingface_hub"
            )
        if self._api is None:
            self._api = HfApi(token=self.config.token, endpoint=self.config.endpoint)
        return self._api

    @api.setter
    def api(self, value: Any) -> None:
        """Explicitly set or override the HfApi instance."""
        self._api = value

    def status(self) -> dict[str, Any]:
        """Check installation status and authentication credentials."""
        result: dict[str, Any] = {
            "installed": HAS_HF_HUB,
            "version": getattr(huggingface_hub, "__version__", None) if HAS_HF_HUB else None,
            "token_configured": bool(self.config.token),
            "authenticated": False,
            "user": None,
            "error": None,
        }

        if not HAS_HF_HUB:
            result["error"] = "huggingface_hub package is not installed."
            return result

        if not self.config.token:
            result["error"] = "No HF_TOKEN or HUGGINGFACE_HUB_TOKEN configured."
            return result

        try:
            user_info = self.api.whoami(token=self.config.token)
            result["authenticated"] = True
            result["user"] = {
                "name": user_info.get("name"),
                "fullname": user_info.get("fullname"),
                "email": user_info.get("email"),
                "type": user_info.get("type"),
                "orgs": [org.get("name") for org in user_info.get("orgs", []) if "name" in org],
            }
        except Exception as exc:  # noqa: BLE001
            result["error"] = str(exc)

        return result

    def list_spaces(
        self,
        *,
        search: str | None = None,
        author: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List AI application Spaces on Hugging Face."""
        if not HAS_HF_HUB:
            raise HuggingFaceIntegrationError("huggingface_hub is not installed.")

        try:
            spaces = self.api.list_spaces(search=search, author=author, limit=limit)
            out = []
            for sp in spaces:
                out.append(
                    {
                        "id": getattr(sp, "id", str(sp)),
                        "author": getattr(sp, "author", None),
                        "likes": getattr(sp, "likes", 0),
                        "private": getattr(sp, "private", False),
                        "sdk": getattr(sp, "sdk", None),
                        "last_modified": (
                            sp.last_modified.isoformat()
                            if getattr(sp, "last_modified", None)
                            else None
                        ),
                    }
                )
            return out
        except Exception as exc:
            raise HuggingFaceIntegrationError(f"Failed to list spaces: {exc}") from exc

    def list_models(
        self,
        *,
        search: str | None = None,
        author: str | None = None,
        filter_tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List models on Hugging Face matching query criteria."""
        if not HAS_HF_HUB:
            raise HuggingFaceIntegrationError("huggingface_hub is not installed.")

        try:
            models = self.api.list_models(
                search=search, author=author, filter=filter_tags, limit=limit
            )
            out = []
            for m in models:
                out.append(
                    {
                        "id": getattr(m, "id", str(m)),
                        "author": getattr(m, "author", None),
                        "downloads": getattr(m, "downloads", 0),
                        "likes": getattr(m, "likes", 0),
                        "pipeline_tag": getattr(m, "pipeline_tag", None),
                        "tags": list(getattr(m, "tags", []) or []),
                    }
                )
            return out
        except Exception as exc:
            raise HuggingFaceIntegrationError(f"Failed to list models: {exc}") from exc

    def generate_text(
        self,
        *,
        model: str,
        prompt: str,
        max_new_tokens: int = 100,
        temperature: float = 0.7,
    ) -> str:
        """Call Hugging Face Inference API for text generation."""
        if not HAS_HF_HUB:
            raise HuggingFaceIntegrationError("huggingface_hub is not installed.")

        try:
            client = InferenceClient(
                model=model,
                token=self.config.token,
                timeout=self.config.timeout,
            )
            response = client.text_generation(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
            )
            return str(response)
        except Exception as exc:
            raise HuggingFaceIntegrationError(
                f"Inference API call to model '{model}' failed: {exc}"
            ) from exc

    def download_file(
        self,
        *,
        repo_id: str,
        filename: str,
        repo_type: str = "model",
        subfolder: str | None = None,
        local_dir: str | Path | None = None,
    ) -> Path:
        """Download a specific file from Hugging Face Hub."""
        if not HAS_HF_HUB:
            raise HuggingFaceIntegrationError("huggingface_hub is not installed.")

        try:
            downloaded = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                subfolder=subfolder,
                repo_type=repo_type,
                token=self.config.token,
                local_dir=str(local_dir) if local_dir else None,
            )
            return Path(downloaded)
        except Exception as exc:
            raise HuggingFaceIntegrationError(
                f"Failed to download '{filename}' from repo '{repo_id}': {exc}"
            ) from exc

    @staticmethod
    def load_catalog(path: Path | str | None = None) -> dict[str, Any]:
        """Load the structured Hugging Face AI apps and models catalog."""
        target_path = (
            Path(path)
            if path
            else Path(__file__).resolve().parent.parent / "docs" / "huggingface-ai-catalog.json"
        )
        if not target_path.is_file():
            raise HuggingFaceIntegrationError(f"Catalog file not found at: {target_path}")
        try:
            data = json.loads(target_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise HuggingFaceIntegrationError("Catalog file does not contain a JSON object")
            return cast("dict[str, Any]", data)
        except HuggingFaceIntegrationError:
            raise
        except Exception as exc:
            raise HuggingFaceIntegrationError(f"Failed to parse catalog JSON: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for Hugging Face operations."""
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--token", help="Hugging Face personal access token")
    shared.add_argument("--json", action="store_true", help="Output raw JSON")

    parser = argparse.ArgumentParser(
        prog="vessell-hf",
        description="VessellFramework Hugging Face Hub and Inference Integration CLI",
        parents=[shared],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # status command
    subparsers.add_parser(
        "status", parents=[shared], help="Check installation and authentication status"
    )

    # spaces command
    spaces_parser = subparsers.add_parser(
        "spaces", parents=[shared], help="List or search AI application Spaces"
    )
    spaces_parser.add_argument("--search", help="Search query string")
    spaces_parser.add_argument("--author", help="Filter by space author / organization")
    spaces_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of spaces to return (default: 10)"
    )

    # models command
    models_parser = subparsers.add_parser(
        "models", parents=[shared], help="List or search models"
    )
    models_parser.add_argument("--search", help="Search query string")
    models_parser.add_argument("--author", help="Filter by model author / organization")
    models_parser.add_argument("--tag", action="append", dest="tags", help="Filter by tag")
    models_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of models to return (default: 10)"
    )

    # generate command
    gen_parser = subparsers.add_parser(
        "generate", parents=[shared], help="Run text generation via Inference API"
    )
    gen_parser.add_argument(
        "--model", required=True, help="Model repository ID (e.g. meta-llama/Llama-3-8B)"
    )
    gen_parser.add_argument("--prompt", required=True, help="Input prompt")
    gen_parser.add_argument(
        "--max-tokens", type=int, default=100, help="Max new tokens to generate"
    )
    gen_parser.add_argument(
        "--temperature", type=float, default=0.7, help="Sampling temperature"
    )

    # download command
    dl_parser = subparsers.add_parser(
        "download", parents=[shared], help="Download a specific file from Hugging Face Hub"
    )
    dl_parser.add_argument("--repo-id", required=True, help="Target repository ID")
    dl_parser.add_argument("--filename", required=True, help="File path within the repository")
    dl_parser.add_argument(
        "--repo-type",
        default="model",
        choices=["model", "dataset", "space"],
        help="Repository type",
    )
    dl_parser.add_argument("--local-dir", help="Target local destination directory")

    # catalog command
    cat_parser = subparsers.add_parser(
        "catalog", parents=[shared], help="Show integrated AI apps and models catalog"
    )
    cat_parser.add_argument("--type", choices=["space", "model"], help="Filter by type")
    cat_parser.add_argument("--category", help="Filter by category")
    cat_parser.add_argument("--target", help="Filter by target repository")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute Hugging Face CLI command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    config = HuggingFaceConfig.from_env(token=args.token)
    client = HuggingFaceClient(config=config)

    try:
        if args.command == "status":
            result = client.status()
            if args.json:
                sys.stdout.write(json.dumps(result, indent=2) + "\n")
            else:
                sys.stdout.write("=== Hugging Face Integration Status ===\n")
                sys.stdout.write(f"Installed: {result['installed']}\n")
                if result["version"]:
                    sys.stdout.write(f"Version: {result['version']}\n")
                sys.stdout.write(f"Token Configured: {result['token_configured']}\n")
                sys.stdout.write(f"Authenticated: {result['authenticated']}\n")
                if result["user"]:
                    sys.stdout.write(f"User: {result['user']['name']}\n")
                    if result["user"]["orgs"]:
                        sys.stdout.write(f"Orgs: {', '.join(result['user']['orgs'])}\n")
                if result["error"]:
                    sys.stdout.write(f"Notice: {result['error']}\n")

        elif args.command == "spaces":
            spaces = client.list_spaces(search=args.search, author=args.author, limit=args.limit)
            if args.json:
                sys.stdout.write(json.dumps(spaces, indent=2) + "\n")
            else:
                sys.stdout.write(f"Found {len(spaces)} Spaces:\n")
                for sp in spaces:
                    sys.stdout.write(f"- {sp['id']} (SDK: {sp['sdk']}, Likes: {sp['likes']})\n")

        elif args.command == "models":
            models = client.list_models(
                search=args.search, author=args.author, filter_tags=args.tags, limit=args.limit
            )
            if args.json:
                sys.stdout.write(json.dumps(models, indent=2) + "\n")
            else:
                sys.stdout.write(f"Found {len(models)} Models:\n")
                for m in models:
                    tag = f" [{m['pipeline_tag']}]" if m["pipeline_tag"] else ""
                    sys.stdout.write(f"- {m['id']}{tag} (Downloads: {m['downloads']}, Likes: {m['likes']})\n")

        elif args.command == "generate":
            generated = client.generate_text(
                model=args.model,
                prompt=args.prompt,
                max_new_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            if args.json:
                sys.stdout.write(json.dumps({"model": args.model, "output": generated}, indent=2) + "\n")
            else:
                sys.stdout.write(f"Model: {args.model}\n\n{generated}\n")

        elif args.command == "download":
            path = client.download_file(
                repo_id=args.repo_id,
                filename=args.filename,
                repo_type=args.repo_type,
                local_dir=args.local_dir,
            )
            if args.json:
                sys.stdout.write(json.dumps({"downloaded_path": str(path)}, indent=2) + "\n")
            else:
                sys.stdout.write(f"Successfully downloaded to: {path}\n")

        elif args.command == "catalog":
            cat = client.load_catalog()
            items = cat.get("items", [])
            if args.type:
                items = [i for i in items if i.get("type") == args.type]
            if args.category:
                items = [i for i in items if i.get("category") == args.category]
            if args.target:
                items = [i for i in items if args.target.lower() in str(i.get("target_repo", "")).lower()]

            if args.json:
                sys.stdout.write(json.dumps(items, indent=2) + "\n")
            else:
                sys.stdout.write(f"=== Hugging Face AI Catalog ({len(items)} items) ===\n")
                for i in items:
                    tag = f"[{i['type'].upper()} - {i['category']}]"
                    sys.stdout.write(f"- {i['id']} {tag} -> {i['use_case']}\n")

        return 0

    except HuggingFaceIntegrationError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 1
    except Exception as err:  # noqa: BLE001
        sys.stderr.write(f"Unexpected error: {err}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
