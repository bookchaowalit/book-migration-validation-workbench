"""The unauthenticated workbench API binds loopback unless explicitly allowed."""

from __future__ import annotations

import pytest
import uvicorn

from migration_validation_api import cli


@pytest.fixture
def runs(monkeypatch):
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: calls.append(kwargs))
    return calls


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_hosts_start(runs, host):
    cli.main(["--host", host, "--port", "0"])
    assert runs == [{"host": host, "port": 0, "log_level": "info"}]


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.20"])
def test_non_loopback_host_is_refused_without_opt_in(runs, host, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--host", host])
    assert exc.value.code == 2
    assert "--allow-remote" in capsys.readouterr().err
    assert runs == []


def test_allow_remote_opts_in(runs):
    cli.main(["--host", "0.0.0.0", "--allow-remote"])
    assert runs[0]["host"] == "0.0.0.0"
