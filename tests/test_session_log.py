import json

from engine.core.session_log import append_entry, clear, read_entries


def test_append_and_read_roundtrip(tmp_path):
    log_path = tmp_path / "session.jsonl"

    # Test the lower-level file format directly (append_entry itself is
    # covered separately, with CTK_SESSION_LOG set, in
    # test_append_entry_creates_parent_dirs_and_uses_env_override below) -
    # this keeps that concern from leaking into a real home directory.
    entry = {
        "timestamp": "2026-07-10T12:00:00+00:00",
        "module": "context_detector",
        "profile": "safe",
        "result": {"status": "ok"},
    }
    with open(log_path, "w") as f:
        f.write(json.dumps(entry) + "\n")

    entries = list(read_entries(log_path))
    assert len(entries) == 1
    assert entries[0]["module"] == "context_detector"


def test_read_entries_skips_corrupted_lines(tmp_path):
    log_path = tmp_path / "session.jsonl"
    with open(log_path, "w") as f:
        f.write('{"module": "a", "result": {}}\n')
        f.write("not valid json\n")
        f.write('{"module": "b", "result": {}}\n')

    entries = list(read_entries(log_path))
    assert [e["module"] for e in entries] == ["a", "b"]


def test_read_entries_missing_file_returns_empty(tmp_path):
    entries = list(read_entries(tmp_path / "does_not_exist.jsonl"))
    assert entries == []


def test_append_entry_creates_parent_dirs_and_uses_env_override(tmp_path, monkeypatch):
    log_path = tmp_path / "nested" / "dir" / "session.jsonl"
    monkeypatch.setenv("CTK_SESSION_LOG", str(log_path))

    append_entry("context_detector", "safe", {"status": "ok"})
    append_entry("port_scanner", "home_lab", {"status": "ok"})

    entries = list(read_entries())
    assert len(entries) == 2
    assert entries[0]["module"] == "context_detector"
    assert entries[1]["module"] == "port_scanner"


def test_clear_removes_the_log_file(tmp_path, monkeypatch):
    log_path = tmp_path / "session.jsonl"
    monkeypatch.setenv("CTK_SESSION_LOG", str(log_path))

    append_entry("context_detector", "safe", {"status": "ok"})
    assert log_path.exists()

    clear()
    assert not log_path.exists()
    assert list(read_entries()) == []
