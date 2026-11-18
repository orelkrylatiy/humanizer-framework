import os

from humanizer_framework import env as env_module
from humanizer_framework.providers import ZaiAnthropicProvider


def test_load_env_reads_file_quotes_and_comments(monkeypatch, tmp_path):
    key_file = tmp_path / ".env"
    key_file.write_text(
        'A_KEY=from-file\nB_KEY="quoted value"\n# comment\n\nBROKEN LINE NO EQUALS\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HUMANIZER_ENV_FILE", str(key_file))
    monkeypatch.delenv("A_KEY", raising=False)
    monkeypatch.delenv("B_KEY", raising=False)
    monkeypatch.setattr(env_module, "_LOADED", False)
    env_module.load_env()
    assert os.environ["A_KEY"] == "from-file"
    assert os.environ["B_KEY"] == "quoted value"


def test_load_env_real_environment_wins(monkeypatch, tmp_path):
    key_file = tmp_path / ".env"
    key_file.write_text("A_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("HUMANIZER_ENV_FILE", str(key_file))
    monkeypatch.setenv("A_KEY", "already-set")
    monkeypatch.setattr(env_module, "_LOADED", False)
    env_module.load_env()
    assert os.environ["A_KEY"] == "already-set"


def test_load_env_missing_file_is_fine(monkeypatch, tmp_path):
    monkeypatch.setenv("HUMANIZER_ENV_FILE", str(tmp_path / "absent.env"))
    monkeypatch.setattr(env_module, "_LOADED", False)
    env_module.load_env()  # must not raise


def test_zai_provider_resolves_key_from_env_file(monkeypatch, tmp_path):
    key_file = tmp_path / ".env"
    key_file.write_text("ZAI_API_KEY=file-secret\n", encoding="utf-8")
    monkeypatch.setenv("HUMANIZER_ENV_FILE", str(key_file))
    for var in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "ZAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(env_module, "_LOADED", False)
    provider = ZaiAnthropicProvider()
    assert provider._resolve_key() == "file-secret"


def test_load_env_reads_a_file_created_after_an_initial_miss(monkeypatch, tmp_path):
    key_file = tmp_path / ".env"
    monkeypatch.setenv("HUMANIZER_ENV_FILE", str(key_file))
    monkeypatch.delenv("LATE_KEY", raising=False)
    env_module.load_env()
    key_file.write_text("LATE_KEY=available\n", encoding="utf-8")
    env_module.load_env()
    assert os.environ["LATE_KEY"] == "available"


def test_load_env_reads_new_path_without_clearing_module_state(monkeypatch, tmp_path):
    first = tmp_path / "first.env"
    second = tmp_path / "second.env"
    first.write_text("ENV_FIRST=one\n", encoding="utf-8")
    second.write_text("ENV_SECOND=two\n", encoding="utf-8")
    monkeypatch.delenv("ENV_FIRST", raising=False)
    monkeypatch.delenv("ENV_SECOND", raising=False)
    monkeypatch.setenv("HUMANIZER_ENV_FILE", str(first))
    env_module.load_env()
    monkeypatch.setenv("HUMANIZER_ENV_FILE", str(second))
    env_module.load_env()
    assert os.environ["ENV_FIRST"] == "one"
    assert os.environ["ENV_SECOND"] == "two"
