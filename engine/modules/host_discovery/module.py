"""
host_discovery: passively lists hosts already visible in the device's own
ARP/neighbor cache - devices that have already exchanged traffic with
this device or that Android/Linux has otherwise already resolved on the
local segment. Sends no probe packets to anyone.

This is Capability.PASSIVE_OBSERVE, the exact case that capability was
defined for in engine/policy/schema.py ("reading the ARP/neighbor
cache") - not available under the `safe` profile by default. See
docs/adr/ADR-0001-engine-policy-separation.md.

Explicit non-goal: this module never sends a single packet to discover
anything. It only reads what the kernel already knows. On a Wi-Fi network
with client isolation enabled, this will correctly show nothing beyond
the gateway - that's the expected and useful "isolation is working"
result, not a failure of the module.

Platform note (Android/Termux): like context_detector's `ip addr` path,
`ip neigh show` uses netlink and is blocked by Android's SELinux policy
on stock, non-rooted devices ("Permission denied"). Unlike the Wi-Fi/
cellular case, there is currently no Termux:API command that exposes the
ARP/neighbor table as a fallback - so on most non-rooted Android phones,
this module will honestly report `hosts: []` with a note explaining why,
rather than pretending to work. It works normally on rooted devices,
Termux with netlink permission available, and non-Android Linux.
`/proc/net/arp` is tried as a secondary source (some devices expose it
even when netlink is blocked), also handled defensively.
"""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from engine.core.module_base import Module
from engine.policy.schema import Capability

INCOMPLETE_MAC = "00:00:00:00:00:00"


class HostDiscoveryModule(Module):
    name = "host_discovery"
    description = (
        "Passively lists hosts already present in the device's own ARP/"
        "neighbor cache. Sends no probe packets. Requires passive_observe "
        "- not available under the 'safe' profile. On most non-rooted "
        "Android devices this will report no results with an explanatory "
        "note, since there is no Termux:API fallback for this (unlike "
        "Wi-Fi/cellular detection)."
    )

    def run(self, **kwargs) -> Dict[str, Any]:
        decision = self.policy.request(Capability.PASSIVE_OBSERVE)
        if not decision.allowed:
            return {"status": "denied", "reason": decision.reason}

        hosts, netlink_blocked = self._read_ip_neigh()

        if not hosts:
            proc_hosts = self._read_proc_net_arp()
            hosts.extend(proc_hosts)

        result = {
            "status": "ok",
            "hosts_count": len(hosts),
            "hosts": hosts,
        }

        if not hosts and netlink_blocked:
            result["note"] = (
                "Netlink access is blocked by Android (permission denied) and "
                "/proc/net/arp was empty or unreadable. There is currently no "
                "Termux:API fallback for ARP/neighbor data on non-rooted "
                "Android - this module works on rooted devices and standard "
                "Linux. An empty result here does not necessarily mean no "
                "other devices are present."
            )

        return result

    # -- ip neigh (netlink-based, blocked on stock Android) ---------------
    def _read_ip_neigh(self):
        hosts: List[Dict[str, Any]] = []
        netlink_blocked = False

        for cmd in (["ip", "neigh", "show"], ["ip", "-6", "neigh", "show"]):
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

            if "permission denied" in (proc.stderr or "").lower():
                netlink_blocked = True
                continue

            for line in proc.stdout.splitlines():
                parsed = self._parse_ip_neigh_line(line)
                if parsed:
                    hosts.append(parsed)

        return hosts, netlink_blocked

    @staticmethod
    def _parse_ip_neigh_line(line: str):
        # Typical line: "192.168.1.5 dev wlan0 lladdr aa:bb:cc:dd:ee:ff REACHABLE"
        # Incomplete entries (no lladdr yet) look like: "192.168.1.9 dev wlan0 FAILED"
        parts = line.split()
        if not parts:
            return None

        ip = parts[0]
        device = None
        mac = None
        state = parts[-1] if parts else "UNKNOWN"

        if "dev" in parts:
            idx = parts.index("dev")
            if idx + 1 < len(parts):
                device = parts[idx + 1]
        if "lladdr" in parts:
            idx = parts.index("lladdr")
            if idx + 1 < len(parts):
                mac = parts[idx + 1]

        if mac is None:
            # No resolved MAC yet - not a useful discovery result.
            return None

        return {"ip": ip, "mac": mac, "device": device, "state": state, "source": "ip_neigh"}

    # -- /proc/net/arp (plain file read, secondary source) -----------------
    def _read_proc_net_arp(self) -> List[Dict[str, Any]]:
        path = Path("/proc/net/arp")
        try:
            content = path.read_text()
        except (FileNotFoundError, PermissionError, OSError):
            return []

        hosts = []
        lines = content.splitlines()[1:]  # skip header row
        for line in lines:
            fields = re.split(r"\s+", line.strip())
            if len(fields) < 6:
                continue
            ip, _hw_type, _flags, mac, _mask, device = fields[:6]
            if mac == INCOMPLETE_MAC:
                continue
            hosts.append({"ip": ip, "mac": mac, "device": device, "state": None, "source": "proc_net_arp"})

        return hosts
