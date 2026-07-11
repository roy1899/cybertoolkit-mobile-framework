"""
Shared data contract between analysis modules and the Execution Policy engine.

Modules never implement security logic themselves. They describe *what kind of
action* they want to perform (a Capability) and *against what* (a target, or
None for actions that never leave the device), then ask the policy engine
whether that is currently allowed. The policy engine is the only component
that knows about profiles, scopes, and authorization rules.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Capability(str, Enum):
    """Coarse-grained classes of action a module can request.

    PASSIVE_LOCAL   - reads information already available on the device
                       (interfaces, routes, DNS config, etc). Sends no
                       packets to any other host.
    PASSIVE_OBSERVE - passively observes traffic/state that already exists
                       on the local segment (e.g. reading the ARP/neighbor
                       cache). Sends no probe packets.
    ACTIVE_PROBE    - sends packets to a specific target/subnet (ping
                       sweep, port scan, service detection). Always
                       requires the target to be in an explicitly
                       authorized scope, regardless of profile.
    ACTIVE_INTRUSIVE- exploitation, credential attacks, or anything that
                       attempts to gain access rather than observe. Not
                       implemented by this framework and permanently
                       denied by the policy engine (see HARD_DENY in
                       policy_engine.py). Reserved so the enum exists if a
                       future ADR revisits this decision explicitly.
    """

    PASSIVE_LOCAL = "passive_local"
    PASSIVE_OBSERVE = "passive_observe"
    ACTIVE_PROBE = "active_probe"
    ACTIVE_INTRUSIVE = "active_intrusive"


@dataclass
class AuthorizationRequest:
    module_name: str
    capability: Capability
    target: Optional[str] = None  # host or CIDR; None for device-local actions


@dataclass
class AuthorizationDecision:
    allowed: bool
    reason: str

    def __bool__(self) -> bool:
        return self.allowed
