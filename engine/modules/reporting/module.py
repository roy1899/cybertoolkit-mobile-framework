"""
reporting: aggregates the local session log into a human-readable
Markdown or HTML report.

Reads what other modules already wrote to the session log (see
engine/core/session_log.py) - it does not run any module itself, doesn't
touch the network, and doesn't need any capability beyond passive_local
(reading a local file is local device state, same as everything else
under that capability).

Per-module formatting is intentionally simple and defensive: known
modules (context_detector, port_scanner) get a slightly nicer summary;
anything else - including modules added later that this file hasn't been
updated for - falls back to a generic JSON code block rather than being
silently dropped from the report.

Markdown and HTML are both rendered from the same intermediate "sections"
structure (built once by _build_sections), so the two formats can't drift
out of sync with each other as new module types are added.
"""

import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.core.module_base import Module
from engine.core.session_log import read_entries
from engine.policy.schema import Capability


class ReportingModule(Module):
    name = "reporting"
    description = (
        "Aggregates this session's module runs (from the local session log) "
        "into a Markdown or HTML report. Reads local application state "
        "only; requires no network capability. Runs under the 'safe' "
        "profile."
    )

    def run(self, session_log: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        decision = self.policy.request(Capability.PASSIVE_LOCAL)
        if not decision.allowed:
            return {"status": "denied", "reason": decision.reason}

        log_path = Path(session_log) if session_log else None
        entries = list(read_entries(log_path))

        if not entries:
            empty_note = (
                "No entries found in the session log. Run some modules "
                "with `ctk run <module>` first - each run is logged "
                "automatically."
            )
            return {
                "status": "ok",
                "entries_count": 0,
                "report_markdown": f"# CyberToolkit Session Report\n\n{empty_note}\n",
                "report_html": self._render_html([], empty_note=empty_note),
            }

        sections = self._build_sections(entries)
        return {
            "status": "ok",
            "entries_count": len(entries),
            "report_markdown": self._render_markdown(entries, sections),
            "report_html": self._render_html(sections),
            "network_label": self._infer_network_label(entries),
        }

    @staticmethod
    def _infer_network_label(entries: List[Dict[str, Any]]) -> Optional[str]:
        """Best-effort network name for the *most recent* context_detector
        entry, for use in filenames (e.g. report_HomeNet_20260710.html).
        Prefers SSID; falls back to network_type_guess; returns None if
        neither is available so the caller can fall back to a generic name.
        """
        for entry in reversed(entries):
            if entry.get("module") != "context_detector":
                continue
            result = entry.get("result", {})
            if result.get("status") != "ok":
                continue
            wifi_info = result.get("termux_api_wifi_info")
            if wifi_info and wifi_info.get("ssid"):
                return str(wifi_info["ssid"])
            if result.get("network_type_guess"):
                return str(result["network_type_guess"])
        return None

    # -- intermediate structure ------------------------------------------
    def _build_sections(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sections = []
        for i, entry in enumerate(entries, start=1):
            module_name = entry.get("module", "unknown")
            profile = entry.get("profile", "unknown")
            timestamp = entry.get("timestamp", "unknown")
            result = entry.get("result", {})
            status = result.get("status", "unknown")

            section = {
                "index": i,
                "module": module_name,
                "status": status,
                "timestamp": timestamp,
                "profile": profile,
                "kv": [],
                "code": None,
                "message": None,
                "table": None,
                # Always kept, regardless of module type, so the report
                # never loses information the curated kv/code views chose
                # not to surface - the operator asked for this explicitly
                # after finding the curated view too thin for field use.
                "raw": result,
            }

            if module_name == "context_detector" and status == "ok":
                section["kv"] = self._context_detector_kv(result)
            elif module_name == "port_scanner" and status == "ok":
                section["kv"] = [("Target", str(result.get("target"))), ("Ports", str(result.get("ports")))]
                section["code"] = result.get("raw_output", "").strip()
            elif module_name == "wifi_scan" and status == "ok":
                section["kv"] = [("Networks found", str(result.get("networks_count", 0)))]
                section["table"] = self._wifi_scan_table(result)
            elif module_name == "host_discovery" and status == "ok":
                section["kv"] = [("Hosts found", str(result.get("hosts_count", 0)))]
                if result.get("note"):
                    section["kv"].append(("Note", result["note"]))
                section["table"] = self._host_discovery_table(result)
            elif status == "denied":
                section["message"] = f"Denied: {result.get('reason', 'no reason given')}"
            elif status == "error":
                section["message"] = f"Error: {result.get('reason', 'no reason given')}"
            else:
                # Unknown module or unhandled status - nothing gets
                # silently dropped from the report.
                section["code"] = json.dumps(result, indent=2)

            sections.append(section)
        return sections

    @staticmethod
    def _context_detector_kv(result: Dict[str, Any]) -> List[tuple]:
        kv = [
            ("Network type", str(result.get("network_type_guess", "unknown"))),
            ("Detection method", str(result.get("detection_method", "unknown"))),
        ]

        route = result.get("default_route")
        if route:
            kv.append(("Gateway", f"{route.get('gateway') or 'unknown'} (via {route.get('device')})"))
        else:
            kv.append(("Gateway", "none/unknown"))

        kv.append(("VPN active", str(result.get("vpn_active"))))
        kv.append(("IPv6 available", str(result.get("ipv6_available"))))

        captive = result.get("captive_portal")
        captive_label = "yes" if captive is True else "no" if captive is False else "undetermined"
        kv.append(("Captive portal", captive_label))

        # Full interface list (ip-based path), not just the default route's
        # device - useful for field diagnostics beyond just "am I online".
        interfaces = result.get("interfaces") or []
        for iface in interfaces:
            addrs = ", ".join(iface.get("addresses", [])) or "no address"
            kv.append((f"Interface {iface.get('name', '?')}", f"{iface.get('state', '?')} · {addrs}"))

        # Full Termux:API Wi-Fi details, when the wifi fallback path was
        # used - SSID/BSSID/RSSI/frequency/link speed, not just "wifi".
        wifi_info = result.get("termux_api_wifi_info")
        if wifi_info:
            if wifi_info.get("ssid"):
                kv.append(("SSID", str(wifi_info["ssid"])))
            if wifi_info.get("bssid"):
                kv.append(("BSSID", str(wifi_info["bssid"])))
            if wifi_info.get("frequency_mhz") is not None:
                kv.append(("Frequency", f"{wifi_info['frequency_mhz']} MHz"))
            if wifi_info.get("link_speed_mbps") is not None:
                kv.append(("Link speed", f"{wifi_info['link_speed_mbps']} Mbps"))
            if wifi_info.get("rssi") is not None:
                kv.append(("Signal (RSSI)", f"{wifi_info['rssi']} dBm"))
            if "ssid_hidden" in wifi_info:
                kv.append(("SSID hidden", str(wifi_info["ssid_hidden"])))

        # Full Termux:API cellular details, when that fallback path was
        # used instead.
        cell_info = result.get("termux_api_cell_info")
        if cell_info:
            kv.append(("Cell type", str(cell_info.get("type", "unknown"))))

        if result.get("note"):
            kv.append(("Note", result["note"]))

        return kv

    @staticmethod
    def _wifi_scan_table(result: Dict[str, Any]) -> Dict[str, Any]:
        headers = ["SSID", "Signal", "RSSI", "Channel", "Security", "BSSID"]
        rows = []
        for net in result.get("networks", []):
            rows.append(
                [
                    str(net.get("ssid", "?")),
                    str(net.get("signal_quality", "?")),
                    f"{net.get('rssi_dbm')} dBm" if net.get("rssi_dbm") is not None else "?",
                    str(net.get("channel")) if net.get("channel") is not None else "?",
                    str(net.get("security", "?")),
                    str(net.get("bssid", "?")),
                ]
            )
        return {"headers": headers, "rows": rows}

    @staticmethod
    def _host_discovery_table(result: Dict[str, Any]) -> Dict[str, Any]:
        headers = ["IP", "MAC", "Device", "State", "Source"]
        rows = []
        for host in result.get("hosts", []):
            rows.append(
                [
                    str(host.get("ip", "?")),
                    str(host.get("mac", "?")),
                    str(host.get("device") or "?"),
                    str(host.get("state") or "?"),
                    str(host.get("source", "?")),
                ]
            )
        return {"headers": headers, "rows": rows}

    # -- Markdown rendering -----------------------------------------------
    def _render_markdown(self, entries: List[Dict[str, Any]], sections: List[Dict[str, Any]]) -> str:
        lines = ["# CyberToolkit Session Report", ""]
        lines.append(f"**Entries:** {len(entries)}")
        first_ts = entries[0].get("timestamp", "unknown")
        last_ts = entries[-1].get("timestamp", "unknown")
        lines.append(f"**Session span:** {first_ts} → {last_ts}")
        lines.append("")

        for section in sections:
            lines.append(f"## {section['index']}. `{section['module']}` — {section['status']}")
            lines.append(f"*{section['timestamp']} · profile: {section['profile']}*")
            lines.append("")

            for key, value in section["kv"]:
                lines.append(f"- **{key}:** {value}")

            if section["message"]:
                lines.append(f"**{section['message']}**")

            if section["table"]:
                if section["kv"]:
                    lines.append("")
                headers = section["table"]["headers"]
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("|" + "|".join(["---"] * len(headers)) + "|")
                for row in section["table"]["rows"]:
                    lines.append("| " + " | ".join(row) + " |")

            if section["code"] is not None:
                if section["kv"]:
                    lines.append("")
                lines.append("```")
                lines.append(section["code"])
                lines.append("```")

            # Full raw JSON, for anything that only got a curated summary -
            # keeps the report from silently dropping fields the kv/code
            # views didn't choose to surface.
            if section["kv"]:
                lines.append("")
                lines.append("<details><summary>Raw data</summary>")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(section["raw"], indent=2))
                lines.append("```")
                lines.append("</details>")

            lines.append("")

        return "\n".join(lines)

    # -- HTML rendering -----------------------------------------------
    def _render_html(self, sections: List[Dict[str, Any]], empty_note: Optional[str] = None) -> str:
        parts = [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>CyberToolkit Session Report</title>",
            "<style>",
            "body{font-family:system-ui,-apple-system,sans-serif;max-width:720px;"
            "margin:0 auto;padding:1rem;line-height:1.5;color:#1a1a1a;"
            "background:#fafafa;}",
            "h1{font-size:1.4rem;} h2{font-size:1.1rem;margin-top:2rem;"
            "border-top:1px solid #ddd;padding-top:1rem;}",
            ".meta{color:#666;font-size:0.85rem;margin-bottom:0.75rem;}",
            ".status-ok{color:#1a7f37;} .status-denied{color:#9a6700;} "
            ".status-error{color:#cf222e;}",
            "table{border-collapse:collapse;width:100%;margin:0.5rem 0;}",
            "td,th{padding:0.25rem 0.5rem 0.25rem 0;vertical-align:top;text-align:left;}",
            "th{border-bottom:1px solid #ccc;font-size:0.8rem;color:#555;}",
            "td.key{font-weight:600;white-space:nowrap;color:#444;}",
            "pre{background:#1a1a1a;color:#e6e6e6;padding:0.75rem;"
            "border-radius:6px;overflow-x:auto;font-size:0.85rem;}",
            "details{margin-top:0.5rem;} summary{cursor:pointer;color:#0969da;"
            "font-size:0.85rem;}",
            "</style>",
            "</head>",
            "<body>",
            "<h1>CyberToolkit Session Report</h1>",
        ]

        if empty_note:
            parts.append(f"<p>{html.escape(empty_note)}</p>")
        else:
            parts.append(f"<p><strong>Entries:</strong> {len(sections)}</p>")

        for section in sections:
            status_class = f"status-{section['status']}" if section["status"] in ("ok", "denied", "error") else ""
            parts.append(
                f"<h2>{section['index']}. <code>{html.escape(section['module'])}</code> "
                f'— <span class="{status_class}">{html.escape(section["status"])}</span></h2>'
            )
            parts.append(
                f'<div class="meta">{html.escape(section["timestamp"])} · '
                f'profile: {html.escape(section["profile"])}</div>'
            )

            if section["kv"]:
                parts.append("<table>")
                for key, value in section["kv"]:
                    parts.append(
                        f'<tr><td class="key">{html.escape(key)}</td>'
                        f"<td>{html.escape(str(value))}</td></tr>"
                    )
                parts.append("</table>")

            if section["message"]:
                parts.append(f"<p><strong>{html.escape(section['message'])}</strong></p>")

            if section["table"]:
                headers = section["table"]["headers"]
                parts.append("<table>")
                parts.append("<tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in headers) + "</tr>")
                for row in section["table"]["rows"]:
                    parts.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>")
                parts.append("</table>")

            if section["code"] is not None:
                parts.append(f"<pre>{html.escape(section['code'])}</pre>")

            if section["kv"]:
                parts.append(
                    "<details><summary>Raw data</summary>"
                    f"<pre>{html.escape(json.dumps(section['raw'], indent=2))}</pre></details>"
                )

        parts.append("</body></html>")
        return "\n".join(parts)
