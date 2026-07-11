from unittest.mock import patch

from engine.core.policy_client import PolicyClient
from engine.modules.wifi_scan.module import WifiScanModule
from engine.policy.policy_engine import PolicyEngine


def _make_module(profile_name="home_lab"):
    engine = PolicyEngine(profile_name=profile_name)
    client = PolicyClient(engine, module_name="wifi_scan")
    return WifiScanModule(client)


def test_denied_under_safe_profile():
    module = _make_module(profile_name="safe")
    result = module.run()
    assert result["status"] == "denied"


def test_denied_under_developer_profile():
    module = _make_module(profile_name="developer")
    result = module.run()
    assert result["status"] == "denied"


def test_error_when_termux_api_not_installed():
    module = _make_module()
    with patch("shutil.which", return_value=None):
        result = module.run()
    assert result["status"] == "error"
    assert "termux-api" in result["reason"]


def test_error_when_location_disabled(monkeypatch):
    module = _make_module()
    monkeypatch.setattr("shutil.which", lambda _: "/data/data/com.termux/files/usr/bin/termux-wifi-scaninfo")

    class Result:
        stdout = '{"API_ERROR": "Location needs to be enabled on the device"}'

    with patch("subprocess.run", return_value=Result()):
        result = module.run()

    assert result["status"] == "error"
    assert "Location" in result["reason"]


def test_error_on_unparseable_output(monkeypatch):
    module = _make_module()
    monkeypatch.setattr("shutil.which", lambda _: "/data/data/com.termux/files/usr/bin/termux-wifi-scaninfo")

    class Result:
        stdout = "not json at all"

    with patch("subprocess.run", return_value=Result()):
        result = module.run()

    assert result["status"] == "error"


def test_parses_and_sorts_networks_by_signal_strength(monkeypatch):
    module = _make_module()
    monkeypatch.setattr("shutil.which", lambda _: "/data/data/com.termux/files/usr/bin/termux-wifi-scaninfo")

    payload = (
        '[{"ssid": "WeakNet", "bssid": "aa:bb:cc:dd:ee:01", "frequency_mhz": 2437, '
        '"rssi": -78, "capabilities": "[ESS]"},'
        '{"ssid": "HomeNet", "bssid": "aa:bb:cc:dd:ee:02", "frequency_mhz": 5200, '
        '"rssi": -42, "capabilities": "[WPA2-PSK-CCMP][ESS]"}]'
    )

    class Result:
        stdout = payload

    with patch("subprocess.run", return_value=Result()):
        result = module.run()

    assert result["status"] == "ok"
    assert result["networks_count"] == 2
    # Strongest signal first.
    assert result["networks"][0]["ssid"] == "HomeNet"
    assert result["networks"][0]["security"] == "WPA2"
    assert result["networks"][0]["signal_quality"] == "excellent"
    assert result["networks"][0]["channel"] == 40
    assert result["networks"][1]["ssid"] == "WeakNet"
    assert result["networks"][1]["security"] == "open"
    assert result["networks"][1]["signal_quality"] == "weak"
    assert result["networks"][1]["channel"] == 6


def test_hidden_ssid_labeled(monkeypatch):
    module = _make_module()
    monkeypatch.setattr("shutil.which", lambda _: "/data/data/com.termux/files/usr/bin/termux-wifi-scaninfo")

    class Result:
        stdout = '[{"ssid": "", "bssid": "aa:bb:cc:dd:ee:03", "frequency_mhz": 2412, "rssi": -60}]'

    with patch("subprocess.run", return_value=Result()):
        result = module.run()

    assert result["networks"][0]["ssid"] == "<hidden>"


def test_wpa3_takes_priority_over_wpa2_marker(monkeypatch):
    module = _make_module()
    monkeypatch.setattr("shutil.which", lambda _: "/data/data/com.termux/files/usr/bin/termux-wifi-scaninfo")

    class Result:
        stdout = (
            '[{"ssid": "Net1", "bssid": "x", "frequency_mhz": 5200, "rssi": -50, '
            '"capabilities": "[WPA3-SAE-CCMP][WPA2-PSK-CCMP][ESS]"}]'
        )

    with patch("subprocess.run", return_value=Result()):
        result = module.run()

    assert result["networks"][0]["security"] == "WPA3"


def test_authorized_client_profile_also_allowed():
    module = _make_module(profile_name="authorized_client")
    with patch("shutil.which", return_value=None):
        result = module.run()
    # Not denied by policy (would be an error for a different reason -
    # missing binary - confirming the capability check passed).
    assert result["status"] == "error"
    assert "termux-api" in result["reason"]
