"""
context_detector: passive network context detection.

Reads the device's own interfaces/routes/DNS state to answer "what kind of
network am I probably on" (home / public wifi / cellular / usb tether /
vpn active) without sending a single packet to any other host. This is
what lets the rest of the framework auto-adapt without the operator having
to type an interface name or IP address, per the project's core goal, and
it is safe to run under the `safe` profile on any network.

Platform note (Android/Termux): recent Android versions block unprivileged
apps, including Termux, from opening AF_NETLINK sockets (SELinux policy).
This means `ip addr` / `ip route` reliably fail with "Cannot bind netlink
socket: Permission denied" on stock, non-rooted Android, regardless of
whether iproute2 is installed. When that happens, this module falls back
to Termux:API, trying Wi-Fi first (`termux-wifi-connectioninfo`, richest
data) then cellular (`termux-telephony-cellinfo`, type + registration
only - no IP/gateway available through this path), both of which go
through Android's own APIs instead of netlink and work without root.
Termux:API requires both `pkg install termux-api` and the separate
Termux:API companion app installed on the device. If neither `ip` nor
Termux:API is available, the module still returns `status: ok` with
best-effort/unknown fields rather than failing, since the absence of
tooling is not a policy denial.
"""

import json
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from engine.core.module_base import Module
from engine.policy.schema import Capability

VPN_INTERFACE_PREFIXES = ("tun", "tap", "wg", "ppp")
WIFI_INTERFACE_PREFIXES = ("wlan", "wlp")
CELLULAR_INTERFACE_PREFIXES = ("rmnet", "ccmni", "wwan")
TETHER_INTERFACE_PREFIXES = ("usb", "rndis", "ncm")

# Well-known, no-payload connectivity-check endpoints. Deliberately not
# configurable (see docs/adr/ADR-0004-captive-portal-passive-scope.md):
# staying passive_local depends on this always being a fixed, public,
# non-local-network target rather than something an operator or another
# module could point at an arbitrary host.
CAPTIVE_PORTAL_CHECK_URL = "http://connectivitycheck.gstatic.com/generate_204"
CAPTIVE_PORTAL_EXPECTED_STATUS = 204


class ContextDetectorModule(Module):
    name = "context_detector"
    description = (
        "Passively detects the current network context: interfaces, default "
        "route, IPv4/IPv6 availability, VPN presence, and captive portal "
        "status. Sends no packets to other hosts except a single GET to a "
        "well-known public connectivity-check endpoint (see ADR-0004). Runs "
        "under the 'safe' profile. Falls back to Termux:API (Wi-Fi, then "
        "cellular) when netlink access is blocked by Android."
    )

    def run(self, **kwargs) -> Dict[str, Any]:
        decision = self.policy.request(Capability.PASSIVE_LOCAL)
        if not decision.allowed:
            return {"status": "denied", "reason": decision.reason}

        default_route = self._get_default_route()
        netlink_blocked = self._netlink_permission_denied()

        result = {
            "status": "ok",
            "interfaces": self._get_interfaces(),
            "default_route": default_route,
            "vpn_active": self._detect_vpn(),
            "ipv6_available": self._has_global_ipv6(),
            "network_type_guess": self._guess_network_type(default_route),
            "detection_method": "ip",
            "captive_portal": self._detect_captive_portal(),
        }

        if netlink_blocked or not result["interfaces"]:
            termux_info = self._termux_api_fallback()
            if termux_info is not None:
                result.update(termux_info)
                result["detection_method"] = "termux_api"
            elif netlink_blocked:
                result["detection_method"] = "unavailable"
                result["note"] = (
                    "Netlink access is blocked by Android (permission denied) and "
                    "Termux:API is not available. Install with `pkg install "
                    "termux-api` and the Termux:API companion app for network "
                    "context detection to work on this device."
                )

        return result

    # -- shell helpers -----------------------------------------------------
    @staticmethod
    def _run(cmd: List[str]) -> str:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return proc.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # `ip` may be missing (rare on Termux without iproute2 installed)
            # or unresponsive; treat as "no data" rather than crashing.
            return ""

    @staticmethod
    def _run_capture(cmd: List[str]):
        """Like _run, but also returns stderr and returncode for diagnostics."""
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return proc.stdout, proc.stderr, proc.returncode
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return "", "", None

    def _netlink_permission_denied(self) -> bool:
        _, stderr, _ = self._run_capture(["ip", "-brief", "addr"])
        return "permission denied" in stderr.lower() or "operation not permitted" in stderr.lower()

    # -- captive portal detection ---------------------------------------
    def _detect_captive_portal(self) -> Optional[bool]:
        """Returns True if a captive portal is likely intercepting traffic,
        False if the connectivity check succeeded normally, or None if the
        check itself couldn't be completed (offline, DNS failure, etc.) —
        in which case we simply don't know, rather than guessing.
        """
        try:
            request = urllib.request.Request(CAPTIVE_PORTAL_CHECK_URL, method="GET")
            with urllib.request.urlopen(request, timeout=5) as response:
                status = response.status
                body = response.read()
                final_url = response.geturl()
        except (urllib.error.URLError, TimeoutError, OSError):
            # No connectivity, DNS blocked, or the request otherwise
            # couldn't complete - we can't determine captive-portal status
            # from this, so report "unknown" rather than a false positive.
            return None

        if final_url != CAPTIVE_PORTAL_CHECK_URL:
            # Redirected somewhere else entirely - classic captive portal
            # behavior (redirect to a login page).
            return True

        return not (status == CAPTIVE_PORTAL_EXPECTED_STATUS and len(body) == 0)

    def _termux_api_fallback(self) -> Optional[Dict[str, Any]]:
        """Tries Termux:API sources in order: Wi-Fi first (most common,
        richest data), then cellular. Returns the first one that indicates
        an active connection, or None if neither Termux:API command is
        usable / neither shows a connected state.
        """
        wifi_info = self._termux_api_wifi_fallback()
        if wifi_info is not None:
            return wifi_info
        return self._termux_api_cellular_fallback()

    def _termux_api_wifi_fallback(self) -> Optional[Dict[str, Any]]:
        if shutil.which("termux-wifi-connectioninfo") is None:
            return None

        raw = self._run(["termux-wifi-connectioninfo"])
        if not raw.strip():
            return None

        try:
            info = json.loads(raw)
        except json.JSONDecodeError:
            return None

        state = str(info.get("supplicant_state", "")).upper()
        connected = state == "COMPLETED"
        if not connected:
            # Not actually on Wi-Fi right now - let the dispatcher try the
            # cellular fallback instead of reporting "wifi, unknown".
            return None

        gateway = info.get("dhcp_server")  # not present on all Android/Termux:API versions

        return {
            "interfaces": (
                [{"name": "wlan0 (via termux-api)", "state": "UP", "addresses": [info.get("ip", "")]}]
                if info.get("ip")
                else []
            ),
            "default_route": {"gateway": gateway, "device": "wlan0"},
            "network_type_guess": "wifi",
            "termux_api_wifi_info": info,
        }

    def _termux_api_cellular_fallback(self) -> Optional[Dict[str, Any]]:
        if shutil.which("termux-telephony-cellinfo") is None:
            return None

        raw = self._run(["termux-telephony-cellinfo"])
        if not raw.strip():
            return None

        try:
            cells = json.loads(raw)
        except json.JSONDecodeError:
            return None

        if not isinstance(cells, list):
            return None

        # Look for a registered cell - that's the one we're actually
        # attached to; the list can otherwise include neighboring cells
        # that are visible but not in use.
        registered = [c for c in cells if isinstance(c, dict) and c.get("registered") is True]
        if not registered:
            return None

        cell = registered[0]
        cell_type = str(cell.get("type", "")).lower() or "cellular"

        return {
            "interfaces": [],
            "default_route": None,
            "network_type_guess": "cellular",
            "termux_api_cell_info": {"type": cell_type, "raw": cell},
        }

    # -- parsing -------------------------------------------------------
    def _get_interfaces(self) -> List[Dict[str, Any]]:
        out = self._run(["ip", "-brief", "addr"])
        interfaces = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                interfaces.append(
                    {
                        "name": parts[0],
                        "state": parts[1],
                        "addresses": parts[2:],
                    }
                )
        return interfaces

    def _get_default_route(self) -> Optional[Dict[str, str]]:
        out = self._run(["ip", "route", "show", "default"])
        first_line = out.strip().splitlines()[0] if out.strip() else ""
        match = re.search(r"default via (\S+) dev (\S+)", first_line)
        if match:
            return {"gateway": match.group(1), "device": match.group(2)}
        return None

    def _detect_vpn(self) -> bool:
        out = self._run(["ip", "-brief", "addr"])
        for line in out.splitlines():
            parts = line.split()
            if parts and parts[0].startswith(VPN_INTERFACE_PREFIXES):
                return True
        return False

    def _has_global_ipv6(self) -> bool:
        out = self._run(["ip", "-6", "addr", "show", "scope", "global"])
        return bool(out.strip())

    def _guess_network_type(self, default_route: Optional[Dict[str, str]]) -> str:
        if not default_route:
            return "unknown"
        device = default_route["device"]
        if device.startswith(VPN_INTERFACE_PREFIXES):
            return "vpn"
        if device.startswith(WIFI_INTERFACE_PREFIXES):
            return "wifi"
        if device.startswith(CELLULAR_INTERFACE_PREFIXES):
            return "cellular"
        if device.startswith(TETHER_INTERFACE_PREFIXES):
            return "usb_tether"
        return "unknown"
