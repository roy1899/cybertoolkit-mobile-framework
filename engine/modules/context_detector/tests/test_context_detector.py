from unittest.mock import patch

from engine.core.policy_client import PolicyClient
from engine.modules.context_detector.module import ContextDetectorModule
from engine.policy.policy_engine import PolicyEngine

WLAN_ADDR_OUTPUT = "lo               UNKNOWN        127.0.0.1/8\nwlan0            UP             192.168.1.42/24\n"
DEFAULT_ROUTE_OUTPUT = "default via 192.168.1.1 dev wlan0\n"
IPV6_OUTPUT = "2: wlan0    inet6 2001:db8::1/64 scope global\n"
VPN_ADDR_OUTPUT = WLAN_ADDR_OUTPUT + "tun0             UNKNOWN        10.8.0.2/24\n"


def _fake_run(cmd, **kwargs):
    class Result:
        def __init__(self, stdout):
            self.stdout = stdout
            self.stderr = ""
            self.returncode = 0

    joined = " ".join(cmd)
    if joined == "ip -brief addr":
        return Result(WLAN_ADDR_OUTPUT)
    if joined == "ip route show default":
        return Result(DEFAULT_ROUTE_OUTPUT)
    if joined.startswith("ip -6 addr"):
        return Result(IPV6_OUTPUT)
    return Result("")


def _make_module():
    engine = PolicyEngine(profile_name="safe")
    client = PolicyClient(engine, module_name="context_detector")
    return ContextDetectorModule(client)


def test_context_detector_reports_wifi_and_ipv6():
    module = _make_module()
    with patch("subprocess.run", side_effect=_fake_run):
        result = module.run()

    assert result["status"] == "ok"
    assert result["network_type_guess"] == "wifi"
    assert result["default_route"] == {"gateway": "192.168.1.1", "device": "wlan0"}
    assert result["ipv6_available"] is True
    assert result["vpn_active"] is False


def test_context_detector_detects_vpn_interface():
    module = _make_module()

    def fake_run_with_vpn(cmd, **kwargs):
        class Result:
            def __init__(self, stdout):
                self.stdout = stdout
                self.stderr = ""
                self.returncode = 0

        joined = " ".join(cmd)
        if joined == "ip -brief addr":
            return Result(VPN_ADDR_OUTPUT)
        if joined == "ip route show default":
            return Result(DEFAULT_ROUTE_OUTPUT)
        return Result("")

    with patch("subprocess.run", side_effect=fake_run_with_vpn):
        result = module.run()

    assert result["vpn_active"] is True


def test_context_detector_handles_missing_ip_binary_gracefully():
    module = _make_module()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = module.run()

    assert result["status"] == "ok"
    assert result["interfaces"] == []
    assert result["default_route"] is None
    assert result["network_type_guess"] == "unknown"


def test_context_detector_falls_back_to_termux_api_when_netlink_blocked():
    module = _make_module()

    def fake_run(cmd, **kwargs):
        class Result:
            def __init__(self, stdout="", stderr=""):
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = 0

        joined = " ".join(cmd)
        if joined == "ip -brief addr":
            return Result(stdout="", stderr="Cannot bind netlink socket: Permission denied")
        if joined == "ip route show default":
            return Result(stdout="", stderr="Cannot bind netlink socket: Permission denied")
        if joined == "termux-wifi-connectioninfo":
            payload = (
                '{"ip": "192.168.1.55", "dhcp_server": "192.168.1.1", '
                '"supplicant_state": "COMPLETED", "ssid": "HomeNet"}'
            )
            return Result(stdout=payload)
        return Result()

    with patch("subprocess.run", side_effect=fake_run), patch(
        "shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-wifi-connectioninfo"
    ):
        result = module.run()

    assert result["status"] == "ok"
    assert result["detection_method"] == "termux_api"
    assert result["network_type_guess"] == "wifi"
    assert result["default_route"] == {"gateway": "192.168.1.1", "device": "wlan0"}


def test_context_detector_termux_api_gateway_null_when_dhcp_server_absent():
    # Reflects real on-device output: some Android/Termux:API versions don't
    # include a dhcp_server field at all. Gateway must be null, not a
    # misleading "unknown" string, so JSON consumers can distinguish
    # "we don't know" from an actual value.
    module = _make_module()

    def fake_run(cmd, **kwargs):
        class Result:
            def __init__(self, stdout="", stderr=""):
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = 0

        joined = " ".join(cmd)
        if joined in ("ip -brief addr", "ip route show default"):
            return Result(stdout="", stderr="Cannot bind netlink socket: Permission denied")
        if joined == "termux-wifi-connectioninfo":
            payload = (
                '{"ip": "192.168.1.27", "supplicant_state": "COMPLETED", '
                '"ssid": "TestNet-Example", "bssid": "aa:bb:cc:dd:ee:ff"}'
            )
            return Result(stdout=payload)
        return Result()

    with patch("subprocess.run", side_effect=fake_run), patch(
        "shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-wifi-connectioninfo"
    ):
        result = module.run()

    assert result["default_route"] == {"gateway": None, "device": "wlan0"}
    assert result["network_type_guess"] == "wifi"


def test_context_detector_falls_back_to_cellular_when_wifi_not_connected():
    module = _make_module()

    def fake_run(cmd, **kwargs):
        class Result:
            def __init__(self, stdout="", stderr=""):
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = 0

        joined = " ".join(cmd)
        if joined in ("ip -brief addr", "ip route show default"):
            return Result(stdout="", stderr="Cannot bind netlink socket: Permission denied")
        if joined == "termux-wifi-connectioninfo":
            return Result(stdout='{"supplicant_state": "DISCONNECTED"}')
        if joined == "termux-telephony-cellinfo":
            payload = '[{"type": "lte", "registered": true, "dbm": -85}, ' '{"type": "lte", "registered": false}]'
            return Result(stdout=payload)
        return Result()

    def fake_which(binary):
        if binary in ("termux-wifi-connectioninfo", "termux-telephony-cellinfo"):
            return f"/data/data/com.termux/files/usr/bin/{binary}"
        return None

    with patch("subprocess.run", side_effect=fake_run), patch("shutil.which", side_effect=fake_which):
        result = module.run()

    assert result["status"] == "ok"
    assert result["detection_method"] == "termux_api"
    assert result["network_type_guess"] == "cellular"
    assert result["termux_api_cell_info"]["type"] == "lte"


def test_context_detector_no_cellular_fallback_when_no_registered_cell():
    module = _make_module()

    def fake_run(cmd, **kwargs):
        class Result:
            def __init__(self, stdout="", stderr=""):
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = 0

        joined = " ".join(cmd)
        if joined in ("ip -brief addr", "ip route show default"):
            return Result(stdout="", stderr="Cannot bind netlink socket: Permission denied")
        if joined == "termux-wifi-connectioninfo":
            return Result(stdout='{"supplicant_state": "DISCONNECTED"}')
        if joined == "termux-telephony-cellinfo":
            return Result(stdout='[{"type": "lte", "registered": false}]')
        return Result()

    def fake_which(binary):
        if binary in ("termux-wifi-connectioninfo", "termux-telephony-cellinfo"):
            return f"/data/data/com.termux/files/usr/bin/{binary}"
        return None

    with patch("subprocess.run", side_effect=fake_run), patch("shutil.which", side_effect=fake_which):
        result = module.run()

    assert result["detection_method"] == "unavailable"
    assert "note" in result


def test_context_detector_reports_unavailable_when_no_fallback_exists():
    module = _make_module()

    def fake_run(cmd, **kwargs):
        class Result:
            def __init__(self, stdout="", stderr=""):
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = 0

        return Result(stdout="", stderr="Cannot bind netlink socket: Permission denied")

    with patch("subprocess.run", side_effect=fake_run), patch("shutil.which", return_value=None):
        result = module.run()

    assert result["status"] == "ok"
    assert result["detection_method"] == "unavailable"
    assert "note" in result


def test_context_detector_captive_portal_false_on_clean_204():
    # Uses the autouse conftest fixture's default 204/empty-body response.
    module = _make_module()
    with patch("subprocess.run", side_effect=_fake_run):
        result = module.run()

    assert result["captive_portal"] is False


def test_context_detector_captive_portal_true_on_redirect():
    module = _make_module()

    class RedirectedResponse:
        status = 200

        def read(self):
            return b"<html>login here</html>"

        def geturl(self):
            return "http://hotel-wifi.example/login"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    with patch("subprocess.run", side_effect=_fake_run), patch(
        "urllib.request.urlopen", return_value=RedirectedResponse()
    ):
        result = module.run()

    assert result["captive_portal"] is True


def test_context_detector_captive_portal_true_on_unexpected_status():
    module = _make_module()

    class WrongStatusResponse:
        status = 200

        def read(self):
            return b""

        def geturl(self):
            return "http://connectivitycheck.gstatic.com/generate_204"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    with patch("subprocess.run", side_effect=_fake_run), patch(
        "urllib.request.urlopen", return_value=WrongStatusResponse()
    ):
        result = module.run()

    assert result["captive_portal"] is True


def test_context_detector_captive_portal_none_when_offline():
    import urllib.error

    module = _make_module()
    with patch("subprocess.run", side_effect=_fake_run), patch(
        "urllib.request.urlopen", side_effect=urllib.error.URLError("no route to host")
    ):
        result = module.run()

    assert result["captive_portal"] is None
    # Offline shouldn't take down the rest of the (unrelated) result.
    assert result["status"] == "ok"


def test_context_detector_denied_under_capability_less_profile(tmp_path):
    # A hypothetical profile that grants nothing at all - confirms the
    # module honors a denial rather than running anyway.
    (tmp_path / "locked_down.yaml").write_text("name: locked_down\nallow_capabilities: []\n")
    engine = PolicyEngine(profile_name="locked_down", profiles_dir=tmp_path)
    client = PolicyClient(engine, module_name="context_detector")
    module = ContextDetectorModule(client)

    result = module.run()
    assert result["status"] == "denied"
