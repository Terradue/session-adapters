from pathlib import Path

import pytest
from pydantic import ValidationError

from session_adapters.conainers_auth import ContainersAuth


def test_default_auth_entries_are_independent() -> None:
    config = ContainersAuth()
    other = ContainersAuth()

    assert not config.auths
    config.add_auth("registry.io", "user", "password")

    assert not other.auths


def test_get_instance_loads_credentials_helpers_and_extra_fields(tmp_path: Path) -> None:
    authfile = tmp_path / "auth.json"
    authfile.write_text(
        '{"auths":{"registry.io":{"auth":"dXNlcjpwYXNz"}},'
        '"credHelpers":{"other.io":"pass"},"custom":"preserved"}',
        encoding="utf-8",
    )

    config = ContainersAuth.get_instance(authfile)

    assert config.auths is not None
    assert config.auths["registry.io"].auth == "dXNlcjpwYXNz"
    assert config.cred_helpers == {"other.io": "pass"}
    assert config.model_dump()["custom"] == "preserved"


@pytest.mark.parametrize("content", ["not JSON", '{"auths": []}', '{"credHelpers": 42}'])
def test_get_instance_rejects_invalid_configuration(tmp_path: Path, content: str) -> None:
    authfile = tmp_path / "auth.json"
    authfile.write_text(content, encoding="utf-8")

    with pytest.raises(ValidationError):
        ContainersAuth.get_instance(authfile)


def test_get_instance_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ContainersAuth.get_instance(tmp_path / "missing.json")
