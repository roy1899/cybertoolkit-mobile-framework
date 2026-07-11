import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli"))

import ctk  # noqa: E402
from engine.core.session_log import append_entry  # noqa: E402


def test_sanitize_filename_component_strips_special_characters():
    assert ctk._sanitize_filename_component("Café Central WiFi") == "Caf_Central_WiFi"


def test_sanitize_filename_component_keeps_safe_characters():
    assert ctk._sanitize_filename_component("Home-Net_5G.local") == "Home-Net_5G.local"


def test_sanitize_filename_component_empty_falls_back_to_network():
    assert ctk._sanitize_filename_component("!!!") == "network"


def test_sanitize_filename_component_truncates_long_names():
    long_name = "a" * 200
    result = ctk._sanitize_filename_component(long_name)
    assert len(result) <= 60


def test_run_reporting_auto_names_output_file(tmp_path, monkeypatch, capsys):
    log_path = tmp_path / "session.jsonl"
    monkeypatch.setenv("CTK_SESSION_LOG", str(log_path))
    monkeypatch.chdir(tmp_path)

    append_entry(
        "context_detector",
        "safe",
        {
            "status": "ok",
            "network_type_guess": "wifi",
            "termux_api_wifi_info": {"ssid": "TestNet"},
        },
    )

    monkeypatch.setattr(sys, "argv", ["ctk", "run", "reporting"])
    ctk.main()

    generated = list(tmp_path.glob("cybertoolkit_report_TestNet_*.html"))
    assert len(generated) == 1
    content = generated[0].read_text()
    assert "TestNet" in content
    assert content.startswith("<!DOCTYPE html>")


def test_run_reporting_explicit_output_still_works(tmp_path, monkeypatch):
    log_path = tmp_path / "session.jsonl"
    monkeypatch.setenv("CTK_SESSION_LOG", str(log_path))
    monkeypatch.chdir(tmp_path)

    append_entry("context_detector", "safe", {"status": "ok", "network_type_guess": "wifi"})

    output_file = tmp_path / "custom_name.md"
    monkeypatch.setattr(sys, "argv", ["ctk", "run", "reporting", "--output", str(output_file)])
    ctk.main()

    assert output_file.exists()
    assert output_file.read_text().startswith("# CyberToolkit Session Report")
