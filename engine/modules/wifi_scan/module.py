"""
wifi_scan: passively lists nearby Wi-Fi networks visible to the device,
with signal strength, frequency/channel, and the security type each
network's beacon advertises.

Uses `termux-wifi-scaninfo`, which returns Android's last completed Wi-Fi
scan (it does not trigger a new scan itself). This is Capability.
PASSIVE_OBSERVE, not PASSIVE_LOCAL - see
docs/adr/ADR-0005-wifi-scan-passive-observe.md for why: this reveals
information about the environment around the device, including networks
the operator hasn't joined, not just the device's own connection. It is
therefore not available under the `safe` profile by default.

Platform note: Android requires the ACCESS_FINE_LOCATION permission to
return Wi-Fi scan results (a system-level privacy restriction, not
something this framework controls), and returns no results if location
services are disabled on the device, with an explicit API_ERROR message.
This module surfaces that message as-is rather than masking it.

Scope note: this module reports what each access point's beacon
advertises (SSID, BSSID, RSSI, frequency, and the encryption type it
announces - WPA2/WPA3/WEP/open). It does not test, exploit, or guess
credentials, and "security type" here is the AP's own announcement, not
an assessment of its actual strength. This is not a vulnerability
scanner.
"""

import json
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from engine.core.module_base import Module
from engine.policy.schema import Capability

# Rough RSSI (dBm) bands for a human-readable label. Boundaries follow
# common Wi-Fi tooling conventions; treat as indicative, not a spec.
_SIGNAL_BANDS = (
    (-50, "excellent"),
    (-60, "good"),
    (-70, "fair"),
    (-80, "weak"),
)

# Checked in this order (strongest first) against the AP's advertised
# capabilities string, e.g. "[WPA2-PSK-CCMP][ESS]".
_SECURITY_MARKERS = (
    ("WPA3", "WPA3"),
    ("WPA2", "WPA2"),
    ("WPA", "WPA"),
    ("WEP", "WEP"),
)


class WifiScanModule(Module):
    name = "wifi_scan"
    description = (
        "Passively lists nearby Wi-Fi networks (SSID, BSSID, signal "
        "strength, frequency, advertised security type) from Android's "
        "last Wi-Fi scan. Requires passive_observe - not available under "
        "the 'safe' profile. See ADR-0005."
    )

    def run(self, **kwargs) -> Dict[str, Any]:
        decision = self.policy.request(Capability.PASSIVE_OBSERVE)
        if not decision.allowed:
            return {"status": "denied", "reason": decision.reason}

        if shutil.which("termux-wifi-scaninfo") is None:
            return {
                "status": "error",
                "reason": (
                    "termux-wifi-scaninfo is not available. Install with "
                    "`pkg install termux-api` and the Termux:API companion app."
                ),
            }

        raw = self._run(["termux-wifi-scaninfo"])
        if not raw.strip():
            return {"status": "error", "reason": "No output from termux-wifi-scaninfo."}

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "error", "reason": "Could not parse termux-wifi-scaninfo output."}

        if isinstance(data, dict) and "API_ERROR" in data:
            # Android itself refused (commonly: location services disabled,
            # which is required for Wi-Fi scan results on modern Android).
            return {"status": "error", "reason": str(data["API_ERROR"])}

        if not isinstance(data, list):
            return {"status": "error", "reason": "Unexpected termux-wifi-scaninfo output format."}

        networks = [self._parse_network(n) for n in data if isinstance(n, dict)]
        networks.sort(key=lambda n: n["rssi_dbm"] if n["rssi_dbm"] is not None else -999, reverse=True)

        return {"status": "ok", "networks_count": len(networks), "networks": networks}

    @staticmethod
    def _run(cmd: List[str]) -> str:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return proc.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    @classmethod
    def _parse_network(cls, entry: Dict[str, Any]) -> Dict[str, Any]:
        # Field names are defensive: real-device Termux:API output has
        # drifted before (see context_detector's dhcp_server history), so
        # this accepts a couple of plausible variants rather than assuming
        # one is definitive.
        rssi = entry.get("rssi", entry.get("level"))
        frequency = entry.get("frequency_mhz", entry.get("frequency"))
        ssid = entry.get("ssid") or "<hidden>"

        return {
            "ssid": ssid,
            "bssid": entry.get("bssid"),
            "frequency_mhz": frequency,
            "channel": cls._frequency_to_channel(frequency),
            "rssi_dbm": rssi,
            "signal_quality": cls._signal_quality(rssi),
            "security": cls._parse_security(entry.get("capabilities")),
        }

    @staticmethod
    def _signal_quality(rssi: Optional[int]) -> str:
        if rssi is None:
            return "unknown"
        for threshold, label in _SIGNAL_BANDS:
            if rssi >= threshold:
                return label
        return "very weak"

    @staticmethod
    def _parse_security(capabilities: Optional[str]) -> str:
        if not capabilities:
            return "unknown"
        for marker, label in _SECURITY_MARKERS:
            if marker in capabilities:
                return label
        return "open"

    @staticmethod
    def _frequency_to_channel(frequency_mhz: Optional[int]) -> Optional[int]:
        if frequency_mhz is None:
            return None
        # 2.4 GHz band
        if 2412 <= frequency_mhz <= 2472:
            return (frequency_mhz - 2412) // 5 + 1
        if frequency_mhz == 2484:
            return 14
        # 5 GHz band (common range; not exhaustive of every regional plan)
        if 5000 <= frequency_mhz <= 5895:
            return (frequency_mhz - 5000) // 5
        # 6 GHz band (Wi-Fi 6E)
        if 5955 <= frequency_mhz <= 7115:
            return (frequency_mhz - 5950) // 5
        return None
