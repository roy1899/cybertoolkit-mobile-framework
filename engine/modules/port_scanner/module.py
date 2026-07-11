"""
port_scanner: active TCP port scan of a specific target using nmap.

This module never decides for itself whether a target is "ok to scan" - it
asks the policy engine for Capability.ACTIVE_PROBE against the requested
target and only proceeds if authorized. Under the `safe` and `developer`
profiles this is always denied. Under `home_lab` / `research` it is
allowed against the profile's pre-declared private/lab ranges. Under
`authorized_client` it is denied until the operator explicitly confirms
the engagement's scope via `authorize_scope()` / `ctk --authorize`.
"""

import shutil
import subprocess
from typing import Any, Dict

from engine.core.module_base import Module
from engine.policy.schema import Capability


class PortScannerModule(Module):
    name = "port_scanner"
    description = (
        "Active TCP port scan of a single target/subnet via nmap. Requires "
        "ACTIVE_PROBE authorization for that target under the active profile."
    )

    def run(self, target: str, ports: str = "1-1024", **kwargs) -> Dict[str, Any]:
        if not target:
            return {"status": "error", "reason": "target is required"}

        decision = self.policy.request(Capability.ACTIVE_PROBE, target=target)
        if not decision.allowed:
            return {"status": "denied", "reason": decision.reason}

        if shutil.which("nmap") is None:
            return {
                "status": "error",
                "reason": "nmap is not installed. On Termux: pkg install nmap",
            }

        cmd = ["nmap", "-Pn", "-p", ports, target]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            return {"status": "error", "reason": "scan timed out after 180s"}

        if proc.returncode != 0:
            return {"status": "error", "reason": proc.stderr.strip() or "nmap failed"}

        return {
            "status": "ok",
            "target": target,
            "ports": ports,
            "raw_output": proc.stdout,
        }
