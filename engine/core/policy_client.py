"""
PolicyClient: the only thing an analysis module is allowed to hold a
reference to for authorization purposes.

It is a thin, module-scoped wrapper around PolicyEngine. Modules call
`policy.request(capability, target=...)` and get an AuthorizationDecision
back; they never see the PolicyEngine itself, its profile data, or its
scope list. This is what lets the engine/policy separation in
docs/adr/ADR-0001 actually hold in practice rather than just on paper.
"""

from engine.policy.policy_engine import PolicyEngine
from engine.policy.schema import AuthorizationDecision, AuthorizationRequest, Capability


class PolicyClient:
    def __init__(self, engine: PolicyEngine, module_name: str):
        self._engine = engine
        self._module_name = module_name

    def request(self, capability: Capability, target: str = None) -> AuthorizationDecision:
        req = AuthorizationRequest(
            module_name=self._module_name, capability=capability, target=target
        )
        return self._engine.authorize(req)
