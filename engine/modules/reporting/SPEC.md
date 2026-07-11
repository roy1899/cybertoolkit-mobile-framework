# Module: reporting

## Capability required
`passive_local` — reads the local session log file only. No network
access, no dependency on any other module being installed. Permitted
under every profile, including `safe`.

## Purpose
Aggregates whatever the current session has already run (via the local
session log written by the CLI after each `ctk run`) into a single
Markdown report — useful for documenting an analysis session or sharing
results without hand-copying JSON output.

## Inputs
- `session_log` (optional): path to a session log file. Defaults to
  `~/.cache/cybertoolkit/session.jsonl` (or the `CTK_SESSION_LOG`
  environment variable if set).

## Output shape
```json
{
  "status": "ok",
  "entries_count": 3,
  "report_markdown": "# CyberToolkit Session Report\n\n...",
  "report_html": "<!DOCTYPE html>\n<html>...</html>",
  "network_label": "HomeNet"
}
```
Both formats are always generated (rendered from the same intermediate
structure, so they can't drift out of sync). `network_label` is the SSID
(or `network_type_guess` if no SSID is available) from the *most recent*
`context_detector` entry in the log, or `null` if none exists — used by
the CLI to auto-name the output file. If the log is empty or missing,
`entries_count` is `0` and both report bodies explain how to populate it,
rather than being empty.

Each `context_detector` entry's summary now includes the full interface
list and, when available, all Termux:API Wi-Fi details (SSID, BSSID,
frequency, link speed, RSSI, hidden flag) or cellular details (cell
type) — not just the coarse `network_type_guess`. `wifi_scan` entries
render as a sortable-by-eye table (SSID, signal, RSSI, channel, security,
BSSID). `host_discovery` entries render as a table of hosts found in the
ARP/neighbor cache (IP, MAC, device, state, source). Every section also
carries a collapsible "Raw data" block with the complete underlying JSON,
so nothing the curated summary chose not to surface is ever lost from the
report.

Via the CLI:
- `ctk run reporting --output report.md` writes Markdown.
- `ctk run reporting --output report.html` writes HTML.
- `ctk run reporting` (no `--output`) auto-generates an HTML file named
  `cybertoolkit_report_<network>_<timestamp>.html` in the current
  directory, using `network_label` (sanitized for filesystem safety).

## How entries get into the log
The CLI (`cli/ctk.py`) appends one entry per `ctk run <module>` invocation
automatically — this module does not run other modules itself, it only
reads what's already there. See `engine/core/session_log.py`.

## Per-module rendering
`context_detector` and `port_scanner` get a readable summary. Any other
module (including ones added after this file was last updated) falls back
to a generic JSON code block, so nothing from the log is ever silently
dropped from the report.

## Known limitations
- All output (including `raw_output` from `port_scanner`, which could in
  principle contain unusual characters) is HTML-escaped before being
  embedded, so the HTML report can't be broken or turned into a script
  injection by scan output. This is defensive hygiene for a local file
  you'll open in a browser, not a security boundary against a hostile
  target - `port_scanner` itself remains gated by `active_probe`
  authorization regardless.
- The session log is a flat file with no rotation or size cap; a very
  long-running session could produce a large log/report. Not a concern at
  current expected usage patterns, but worth revisiting if it becomes one.
