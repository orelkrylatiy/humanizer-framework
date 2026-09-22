from pathlib import Path

import pytest

from humanizer_framework.config import load_config


def test_config_rejects_non_table_provider_options(tmp_path: Path):
    path = tmp_path / "humanizer.toml"
    path.write_text(
        '[provider]\nkind = "litellm"\nmodel = "x"\noptions = "bad"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_config(path)


def test_config_loads_provider_table(tmp_path: Path):
    path = tmp_path / "humanizer.toml"
    path.write_text(
        'strict = true\n[provider]\nkind = "litellm"\nmodel = "x"\n'
        '[provider.options]\ntimeout = 20\n',
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.strict is True
    assert config.provider.model == "x"
    assert config.provider.options["timeout"] == 20
