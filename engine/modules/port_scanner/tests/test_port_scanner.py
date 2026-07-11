from unittest.mock import patch

from engine.core.policy_client import PolicyClient
from engine.modules.port_scanner.module import PortScannerModule
from engine.policy.policy_engine import PolicyEngine


def _make_module(profile_name, authorized_scopes=None):
    engine = PolicyEngine(profile_name=profile_name, authorized_scopes=authorized_scopes)
    client = PolicyClient(engine, module_name="port_scanner")
    return PortScannerModule(client)


def test_denied_without_target():
    module = _make_module("home_lab")
    result = module.run(target="")
    assert result["status"] == "error"


def test_denied_under_safe_profile():
    module = _make_module("safe")
    result = module.run(target="192.168.1.10")
    assert result["status"] == "denied"


def test_denied_outside_authorized_scope():
    module = _make_module("home_lab")
    result = module.run(target="8.8.8.8")
    assert result["status"] == "denied"


def test_allowed_and_reports_missing_nmap(monkeypatch):
    module = _make_module("home_lab")
    monkeypatch.setattr("shutil.which", lambda _: None)
    result = module.run(target="192.168.1.10")
    assert result["status"] == "error"
    assert "nmap" in result["reason"]


def test_allowed_and_runs_nmap(monkeypatch):
    module = _make_module("home_lab")
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/nmap")

    class FakeProc:
        returncode = 0
        stdout = "PORT   STATE SERVICE\n22/tcp open  ssh\n"
        stderr = ""

    with patch("subprocess.run", return_value=FakeProc()) as mock_run:
        result = module.run(target="192.168.1.10", ports="22")

    assert result["status"] == "ok"
    assert "22/tcp" in result["raw_output"]
    called_cmd = mock_run.call_args.args[0]
    assert called_cmd == ["nmap", "-Pn", "-p", "22", "192.168.1.10"]


def test_authorized_client_requires_explicit_scope_confirmation():
    denied_module = _make_module("authorized_client")
    denied = denied_module.run(target="203.0.113.10")
    assert denied["status"] == "denied"

    allowed_module = _make_module("authorized_client", authorized_scopes=["203.0.113.0/24"])
    with patch("shutil.which", return_value="/usr/bin/nmap"):

        class FakeProc:
            returncode = 0
            stdout = ""
            stderr = ""

        with patch("subprocess.run", return_value=FakeProc()):
            allowed = allowed_module.run(target="203.0.113.10")
    assert allowed["status"] == "ok"
