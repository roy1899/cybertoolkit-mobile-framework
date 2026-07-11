"""
Execution Policy engine.

This is the single component in the framework that is allowed to make
security decisions. Analysis modules never check "am I on a public network"
or "do I own this target" themselves - they call PolicyClient.request(...)
and get back an AuthorizationDecision. This module is what backs that
decision.

Design rules (see docs/adr/ADR-0001-engine-policy-separation.md):
  1. Capability.ACTIVE_INTRUSIVE is hard-denied for every profile, always.
     There is no configuration path that enables it. This framework does
     not implement exploitation/credential-attack tooling.
  2. Capability.ACTIVE_PROBE is only granted when the target is inside a
     scope the operator has explicitly authorized - either pre-declared in
     the profile file, or added at runtime via authorize_scope() /
     `ctk --authorize <cidr>`. A profile that "allows" active_probe as a
     capability class does NOT mean every target is authorized; scope is
     checked independently, every time.
"""

from __future__ import annotations

import ipaddress
from pathlib import Path
from typing import Iterable, Optional

import yaml

from engine.policy.schema import AuthorizationDecision, AuthorizationRequest, Capability

PROFILES_DIR = Path(__file__).parent / "profiles"

# Capabilities no profile can ever grant, no matter how it is configured.
HARD_DENY = {Capability.ACTIVE_INTRUSIVE}


class PolicyEngine:
    def __init__(
        self,
        profile_name: str = "safe",
        profiles_dir: Optional[Path] = None,
        authorized_scopes: Optional[Iterable[str]] = None,
    ):
        self.profiles_dir = Path(profiles_dir) if profiles_dir else PROFILES_DIR
        self.profile_name = profile_name
        self.profile = self._load_profile(profile_name)

        # Scopes the operator has confirmed authorization for, for this
        # session: whatever the profile file pre-declares, plus anything
        # passed in explicitly (e.g. from the CLI --authorize flag).
        self.authorized_scopes = list(self.profile.get("authorized_scopes") or [])
        if authorized_scopes:
            self.authorized_scopes.extend(authorized_scopes)

    def _load_profile(self, name: str) -> dict:
        path = self.profiles_dir / f"{name}.yaml"
        if not path.exists():
            available = sorted(p.stem for p in self.profiles_dir.glob("*.yaml"))
            raise ValueError(
                f"Unknown execution policy profile '{name}'. Available profiles: {available}"
            )
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        data.setdefault("allow_capabilities", [])
        data.setdefault("authorized_scopes", [])
        return data

    def authorize_scope(self, cidr_or_host: str) -> None:
        """Explicitly confirm authorization for a target for the rest of this session."""
        self.authorized_scopes.append(cidr_or_host)

    def _target_in_scope(self, target: Optional[str]) -> bool:
        if target is None:
            return True
        for scope in self.authorized_scopes:
            try:
                if ipaddress.ip_address(target) in ipaddress.ip_network(scope, strict=False):
                    return True
            except ValueError:
                # Not a bare IP (could be a hostname, or `scope` could be a
                # hostname/CIDR mismatch) - fall back to exact string match.
                if target == scope:
                    return True
        return False

    def authorize(self, request: AuthorizationRequest) -> AuthorizationDecision:
        cap = request.capability

        if cap in HARD_DENY:
            return AuthorizationDecision(
                allowed=False,
                reason=(
                    f"Capability '{cap.value}' is permanently disabled in this framework "
                    f"(see ADR-0001). No profile can enable it."
                ),
            )

        allowed_caps = self.profile.get("allow_capabilities", [])
        if cap.value not in allowed_caps:
            return AuthorizationDecision(
                allowed=False,
                reason=f"Profile '{self.profile_name}' does not grant capability '{cap.value}'.",
            )

        if cap == Capability.ACTIVE_PROBE and not self._target_in_scope(request.target):
            return AuthorizationDecision(
                allowed=False,
                reason=(
                    f"Target '{request.target}' is not in an explicitly authorized scope for "
                    f"profile '{self.profile_name}'. Confirm authorization first, e.g. "
                    f"`ctk --profile {self.profile_name} --authorize {request.target} run ...`."
                ),
            )

        return AuthorizationDecision(allowed=True, reason="Authorized")
