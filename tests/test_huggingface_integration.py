# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Unit tests for Hugging Face Hub and Inference client integration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vessell.huggingface_integration import (
    HuggingFaceClient,
    HuggingFaceConfig,
    HuggingFaceIntegrationError,
    main,
)


def test_huggingface_config_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGINGFACE_HUB_TOKEN", raising=False)
    monkeypatch.delenv("HF_ENDPOINT", raising=False)

    cfg = HuggingFaceConfig.from_env()
    assert cfg.token is None
    assert cfg.endpoint is None

    monkeypatch.setenv("HF_TOKEN", "hf_test_env_token")
    cfg2 = HuggingFaceConfig.from_env()
    assert cfg2.token == "hf_test_env_token"

    cfg3 = HuggingFaceConfig.from_env(token="hf_override_token")
    assert cfg3.token == "hf_override_token"


def test_huggingface_client_status_no_token() -> None:
    client = HuggingFaceClient(config=HuggingFaceConfig(token=None))
    status = client.status()
    assert status["installed"] is True
    assert status["token_configured"] is False
    assert status["authenticated"] is False
    assert "No HF_TOKEN" in str(status["error"])


def test_huggingface_client_status_authenticated() -> None:
    mock_api = MagicMock()
    mock_api.whoami.return_value = {
        "name": "analyst-user",
        "fullname": "Analyst User",
        "email": "user@example.org",
        "type": "user",
        "orgs": [{"name": "research-team"}],
    }
    client = HuggingFaceClient(config=HuggingFaceConfig(token="hf_mock_token"), api=mock_api)

    status = client.status()
    assert status["authenticated"] is True
    assert status["user"] is not None
    assert status["user"]["name"] == "analyst-user"
    assert status["user"]["orgs"] == ["research-team"]
    assert status["error"] is None


def test_huggingface_client_status_error() -> None:
    mock_api = MagicMock()
    mock_api.whoami.side_effect = RuntimeError("401 Client Error: Invalid Token")
    client = HuggingFaceClient(config=HuggingFaceConfig(token="hf_invalid_token"), api=mock_api)

    status = client.status()
    assert status["authenticated"] is False
    assert status["error"] is not None
    assert "Invalid Token" in status["error"]


def test_huggingface_list_spaces() -> None:
    mock_api = MagicMock()

    class MockSpace:
        id = "org/cool-space"
        author = "org"
        likes = 42
        private = False
        sdk = "gradio"
        last_modified = datetime(2026, 10, 1, tzinfo=UTC)

    mock_api.list_spaces.return_value = [MockSpace()]
    client = HuggingFaceClient(config=HuggingFaceConfig(token="hf_token"), api=mock_api)

    spaces = client.list_spaces(search="cool", limit=5)
    assert len(spaces) == 1
    assert spaces[0]["id"] == "org/cool-space"
    assert spaces[0]["likes"] == 42
    assert spaces[0]["sdk"] == "gradio"


def test_huggingface_list_models() -> None:
    mock_api = MagicMock()

    class MockModel:
        id = "sentence-transformers/all-MiniLM-L6-v2"
        author = "sentence-transformers"
        downloads = 1000000
        likes = 3500
        pipeline_tag = "feature-extraction"
        tags = ("embeddings", "nlp")

    mock_api.list_models.return_value = [MockModel()]
    client = HuggingFaceClient(config=HuggingFaceConfig(token="hf_token"), api=mock_api)

    models = client.list_models(search="MiniLM", limit=5)
    assert len(models) == 1
    assert models[0]["id"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert models[0]["pipeline_tag"] == "feature-extraction"


def test_huggingface_generate_text() -> None:
    client = HuggingFaceClient(config=HuggingFaceConfig(token="hf_token"))
    with patch("vessell.huggingface_integration.InferenceClient") as mock_inf:
        mock_instance = MagicMock()
        mock_instance.text_generation.return_value = "Generated response from model"
        mock_inf.return_value = mock_instance

        output = client.generate_text(
            model="test-org/test-model", prompt="Evaluate scenario", max_new_tokens=50
        )
        assert output == "Generated response from model"
        mock_instance.text_generation.assert_called_once_with(
            "Evaluate scenario", max_new_tokens=50, temperature=0.7
        )


def test_huggingface_download_file(tmp_path: Path) -> None:
    client = HuggingFaceClient(config=HuggingFaceConfig(token="hf_token"))
    fake_download = tmp_path / "model.safetensors"
    fake_download.write_text("weights")

    with patch("vessell.huggingface_integration.hf_hub_download", return_value=str(fake_download)):
        res = client.download_file(repo_id="test/repo", filename="model.safetensors")
        assert res == fake_download


def test_huggingface_cli_status(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["status", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["installed"] is True
    assert "token_configured" in data


def test_huggingface_cli_spaces(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(HuggingFaceClient, "list_spaces", return_value=[{"id": "demo/app", "sdk": "docker", "likes": 5}]):
        code = main(["spaces", "--search", "demo", "--json"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 1
        assert data[0]["id"] == "demo/app"


def test_huggingface_cli_models(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(
        HuggingFaceClient,
        "list_models",
        return_value=[{"id": "meta/llama", "pipeline_tag": "text-generation", "downloads": 100, "likes": 50}],
    ):
        code = main(["models", "--search", "llama"])
        assert code == 0
        captured = capsys.readouterr()
        assert "meta/llama" in captured.out


def test_huggingface_cli_generate(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(HuggingFaceClient, "generate_text", return_value="Synthetic response"):
        code = main(["generate", "--model", "test/model", "--prompt", "Hello"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Synthetic response" in captured.out


def test_huggingface_cli_error(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(
        HuggingFaceClient, "generate_text", side_effect=HuggingFaceIntegrationError("Model offline")
    ):
        code = main(["generate", "--model", "test/model", "--prompt", "Hello"])
        assert code == 1
        captured = capsys.readouterr()
        assert "Model offline" in captured.err
