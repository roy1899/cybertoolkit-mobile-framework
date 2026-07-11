from unittest.mock import mock_open, patch

from engine.core.policy_client import PolicyClient
from engine.modules.host_discovery.module import HostDiscoveryModule
from engine.policy.policy_engine import PolicyEngine


def _make_module(profile_name="home_lab"):
    engine = PolicyEngine(profile_name=profile_name)
    client = PolicyClient(engine, module_name="host_discovery")
    return HostDiscoveryModule(client)


def test_denied_under_safe_profile():
    module = _make_module(profile_name="safe")
    result = module.run()
    assert result["status"] == "denied"


def test_denied_under_developer_profile():
    module = _make_module(profile_name="developer")
    result = module.run()
    assert result["status"] == "denied"


def test_parses_ip_neigh_output():
    module = _make_module()

    def fake_run(cmd, **kwargs):
        class Result:
            stdout = ""
            stderr = ""

        joined = " ".join(cmd)
        if joined == "ip neigh show":
            r = Result()
            r.stdout = (
                "192.168.1.1 dev wlan0 lladdr aa:bb:cc:dd:ee:ff REACHABLE\n"
                "192.168.1.9 dev wlan0 FAILED\n"  # incomplete, no lladdr - skipped
            )
            return r
        return Result()

    with patch("subprocess.run", side_effect=fake_run), patch(
        "pathlib.Path.read_text", side_effect=FileNotFoundError
    ):
        result = module.run()

    assert result["status"] == "ok"
    assert result["hosts_count"] == 1
    assert result["hosts"][0]["ip"] == "192.168.1.1"
    assert result["hosts"][0]["mac"] == "aa:bb:cc:dd:ee:ff"
    assert result["hosts"][0]["source"] == "ip_neigh"


def test_netlink_blocked_falls_back_to_proc_net_arp():
    module = _make_module()

    def fake_run(cmd, **kwargs):
        class Result:
            stdout = ""
            stderr = "Cannot bind netlink socket: Permission denied"

        return Result()

    arp_content = (
        "IP address       HW type     Flags       HW address            Mask     Device\n"
        "192.168.1.1      0x1         0x2         aa:bb:cc:dd:ee:ff     *        wlan0\n"
        "192.168.1.9      0x1         0x0         00:00:00:00:00:00     *        wlan0\n"
    )

    with patch("subprocess.run", side_effect=fake_run), patch(
        "pathlib.Path.read_text", return_value=arp_content
    ):
        result = module.run()

    assert result["status"] == "ok"
    assert result["hosts_count"] == 1
    assert result["hosts"][0]["ip"] == "192.168.1.1"
    assert result["hosts"][0]["source"] == "proc_net_arp"


def test_netlink_blocked_and_no_proc_net_arp_reports_honest_note():
    module = _make_module()

    def fake_run(cmd, **kwargs):
        class Result:
            stdout = ""
            stderr = "Cannot bind netlink socket: Permission denied"

        return Result()

    with patch("subprocess.run", side_effect=fake_run), patch(
        "pathlib.Path.read_text", side_effect=PermissionError
    ):
        result = module.run()

    assert result["status"] == "ok"
    assert result["hosts_count"] == 0
    assert "note" in result
    assert "no Termux:API fallback" in result["note"]


def test_incomplete_arp_entries_are_skipped():
    module = _make_module()

    def fake_run(cmd, **kwargs):
        class Result:
            stdout = ""
            stderr = ""

        return Result()

    arp_content = (
        "IP address       HW type     Flags       HW address            Mask     Device\n"
        "192.168.1.9      0x1         0x0         00:00:00:00:00:00     *        wlan0\n"
    )

    with patch("subprocess.run", side_effect=fake_run), patch(
        "pathlib.Path.read_text", return_value=arp_content
    ):
        result = module.run()

    assert result["hosts_count"] == 0
    assert "note" not in result  # netlink wasn't blocked, just genuinely empty


def test_authorized_client_profile_also_allowed():
    module = _make_module(profile_name="authorized_client")

    def fake_run(cmd, **kwargs):
        class Result:
            stdout = ""
            stderr = ""

        return Result()

    with patch("subprocess.run", side_effect=fake_run), patch(
        "pathlib.Path.read_text", side_effect=FileNotFoundError
    ):
        result = module.run()

    assert result["status"] == "ok"
