import json

from engine.core.policy_client import PolicyClient
from engine.modules.reporting.module import ReportingModule
from engine.policy.policy_engine import PolicyEngine


def _make_module():
    engine = PolicyEngine(profile_name="safe")
    client = PolicyClient(engine, module_name="reporting")
    return ReportingModule(client)


def _write_log(path, entries):
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def test_empty_log_reports_helpful_message(tmp_path):
    module = _make_module()
    result = module.run(session_log=str(tmp_path / "does_not_exist.jsonl"))

    assert result["status"] == "ok"
    assert result["entries_count"] == 0
    assert "No entries found" in result["report_markdown"]


def test_renders_context_detector_entry(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "context_detector",
                "profile": "safe",
                "result": {
                    "status": "ok",
                    "network_type_guess": "wifi",
                    "detection_method": "termux_api",
                    "default_route": {"gateway": None, "device": "wlan0"},
                    "vpn_active": False,
                    "ipv6_available": False,
                    "captive_portal": False,
                },
            }
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    assert result["status"] == "ok"
    assert result["entries_count"] == 1
    md = result["report_markdown"]
    assert "context_detector" in md
    assert "**Network type:** wifi" in md
    assert "**Captive portal:** no" in md


def test_renders_port_scanner_entry(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:05:00+00:00",
                "module": "port_scanner",
                "profile": "home_lab",
                "result": {
                    "status": "ok",
                    "target": "192.168.1.10",
                    "ports": "22",
                    "raw_output": "22/tcp open ssh",
                },
            }
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    md = result["report_markdown"]
    assert "192.168.1.10" in md
    assert "22/tcp open ssh" in md


def test_renders_denied_entry():
    module = _make_module()
    result = module.run(session_log=None)
    # No log written yet for this test - just confirm the module doesn't
    # crash when given a fresh/default path in an isolated test run.
    assert result["status"] == "ok"


def test_renders_denied_status_from_log(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:10:00+00:00",
                "module": "port_scanner",
                "profile": "safe",
                "result": {"status": "denied", "reason": "Profile 'safe' does not grant capability 'active_probe'."},
            }
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    md = result["report_markdown"]
    assert "denied" in md
    assert "does not grant capability" in md


def test_unknown_module_falls_back_to_json_block(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:15:00+00:00",
                "module": "some_future_module",
                "profile": "safe",
                "result": {"status": "ok", "custom_field": "custom_value"},
            }
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    md = result["report_markdown"]
    assert "some_future_module" in md
    assert "custom_value" in md


def test_multiple_entries_all_appear_in_order(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "context_detector",
                "profile": "safe",
                "result": {"status": "ok", "network_type_guess": "wifi"},
            },
            {
                "timestamp": "2026-07-10T12:05:00+00:00",
                "module": "port_scanner",
                "profile": "home_lab",
                "result": {"status": "ok", "target": "192.168.1.10", "ports": "22", "raw_output": ""},
            },
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    assert result["entries_count"] == 2
    md = result["report_markdown"]
    assert md.index("context_detector") < md.index("port_scanner")


def test_html_report_is_well_formed_and_escapes_content(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "context_detector",
                "profile": "safe",
                "result": {
                    "status": "ok",
                    "network_type_guess": "wifi",
                    "detection_method": "termux_api",
                    "default_route": {"gateway": None, "device": "wlan0"},
                    "vpn_active": False,
                    "ipv6_available": False,
                    "captive_portal": False,
                },
            },
            {
                "timestamp": "2026-07-10T12:05:00+00:00",
                "module": "port_scanner",
                "profile": "home_lab",
                "result": {
                    "status": "ok",
                    "target": "192.168.1.10",
                    "ports": "22",
                    "raw_output": "<script>alert('x')</script>",
                },
            },
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    html_report = result["report_html"]
    assert html_report.startswith("<!DOCTYPE html>")
    assert "<title>CyberToolkit Session Report</title>" in html_report
    assert 'name="viewport"' in html_report  # mobile-friendly
    assert "context_detector" in html_report
    # The raw_output must be escaped, not injected as live HTML.
    assert "<script>alert" not in html_report
    assert "&lt;script&gt;" in html_report


def test_html_report_empty_log_has_helpful_message(tmp_path):
    module = _make_module()
    result = module.run(session_log=str(tmp_path / "does_not_exist.jsonl"))

    assert "No entries found" in result["report_html"]
    assert result["report_html"].startswith("<!DOCTYPE html>")


def test_html_and_markdown_report_same_entries_count(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "context_detector",
                "profile": "safe",
                "result": {"status": "ok", "network_type_guess": "wifi"},
            },
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    assert "context_detector" in result["report_markdown"]
    assert "context_detector" in result["report_html"]


def test_context_detector_full_wifi_details_included(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "context_detector",
                "profile": "safe",
                "result": {
                    "status": "ok",
                    "network_type_guess": "wifi",
                    "detection_method": "termux_api",
                    "default_route": {"gateway": None, "device": "wlan0"},
                    "vpn_active": False,
                    "ipv6_available": False,
                    "captive_portal": False,
                    "interfaces": [
                        {"name": "wlan0 (via termux-api)", "state": "UP", "addresses": ["192.168.1.27"]}
                    ],
                    "termux_api_wifi_info": {
                        "ssid": "HomeNet",
                        "bssid": "aa:bb:cc:dd:ee:ff",
                        "frequency_mhz": 5200,
                        "link_speed_mbps": 433,
                        "rssi": -39,
                        "ssid_hidden": False,
                    },
                },
            }
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    md = result["report_markdown"]
    html_report = result["report_html"]

    for expected in ("HomeNet", "aa:bb:cc:dd:ee:ff", "5200 MHz", "433 Mbps", "-39 dBm", "192.168.1.27"):
        assert expected in md, f"{expected!r} missing from markdown report"
        assert expected in html_report, f"{expected!r} missing from html report"

    # Raw data block preserves everything, including fields the curated
    # kv view doesn't explicitly surface.
    assert "Raw data" in md
    assert "<details>" in html_report


def test_infer_network_label_prefers_ssid(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "context_detector",
                "profile": "safe",
                "result": {
                    "status": "ok",
                    "network_type_guess": "wifi",
                    "termux_api_wifi_info": {"ssid": "TestNet-Example"},
                },
            }
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    assert result["network_label"] == "TestNet-Example"


def test_infer_network_label_falls_back_to_network_type(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "context_detector",
                "profile": "safe",
                "result": {"status": "ok", "network_type_guess": "cellular"},
            }
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    assert result["network_label"] == "cellular"


def test_infer_network_label_uses_most_recent_context_detector_entry(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "context_detector",
                "profile": "safe",
                "result": {"status": "ok", "termux_api_wifi_info": {"ssid": "OldNet"}},
            },
            {
                "timestamp": "2026-07-10T12:05:00+00:00",
                "module": "port_scanner",
                "profile": "home_lab",
                "result": {"status": "ok", "target": "192.168.1.10", "ports": "22", "raw_output": ""},
            },
            {
                "timestamp": "2026-07-10T12:10:00+00:00",
                "module": "context_detector",
                "profile": "safe",
                "result": {"status": "ok", "termux_api_wifi_info": {"ssid": "NewNet"}},
            },
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    assert result["network_label"] == "NewNet"


def test_infer_network_label_none_when_no_context_detector_entry(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "port_scanner",
                "profile": "home_lab",
                "result": {"status": "ok", "target": "192.168.1.10", "ports": "22", "raw_output": ""},
            }
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    assert result["network_label"] is None


def test_renders_wifi_scan_table(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "wifi_scan",
                "profile": "home_lab",
                "result": {
                    "status": "ok",
                    "networks_count": 2,
                    "networks": [
                        {
                            "ssid": "HomeNet",
                            "bssid": "aa:bb:cc:dd:ee:ff",
                            "frequency_mhz": 5200,
                            "channel": 40,
                            "rssi_dbm": -42,
                            "signal_quality": "excellent",
                            "security": "WPA2",
                        },
                        {
                            "ssid": "<hidden>",
                            "bssid": "aa:bb:cc:dd:ee:ff",
                            "frequency_mhz": 2437,
                            "channel": 6,
                            "rssi_dbm": -78,
                            "signal_quality": "weak",
                            "security": "open",
                        },
                    ],
                },
            }
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    md = result["report_markdown"]
    html_report = result["report_html"]

    assert "Networks found" in md
    assert "HomeNet" in md and "HomeNet" in html_report
    assert "WPA2" in md and "WPA2" in html_report
    assert "excellent" in md
    assert "<table>" in html_report
    assert "<th>SSID</th>" in html_report


def test_renders_host_discovery_table(tmp_path):
    log_path = tmp_path / "session.jsonl"
    _write_log(
        log_path,
        [
            {
                "timestamp": "2026-07-10T12:00:00+00:00",
                "module": "host_discovery",
                "profile": "home_lab",
                "result": {
                    "status": "ok",
                    "hosts_count": 1,
                    "hosts": [
                        {
                            "ip": "192.168.1.1",
                            "mac": "aa:bb:cc:dd:ee:ff",
                            "device": "wlan0",
                            "state": "REACHABLE",
                            "source": "ip_neigh",
                        }
                    ],
                },
            }
        ],
    )

    module = _make_module()
    result = module.run(session_log=str(log_path))

    md = result["report_markdown"]
    html_report = result["report_html"]

    assert "Hosts found" in md
    assert "192.168.1.1" in md and "192.168.1.1" in html_report
    assert "aa:bb:cc:dd:ee:ff" in md


def test_denied_under_capability_less_profile(tmp_path):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "locked_down.yaml").write_text("name: locked_down\nallow_capabilities: []\n")
    engine = PolicyEngine(profile_name="locked_down", profiles_dir=profiles_dir)
    client = PolicyClient(engine, module_name="reporting")
    module = ReportingModule(client)

    result = module.run()
    assert result["status"] == "denied"
