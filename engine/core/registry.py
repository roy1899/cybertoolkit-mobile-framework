"""
Static module registry.

Deliberately simple (a dict) for V0.1: new modules are added here by
importing their class and adding one entry. If/when the module count grows
large enough that this becomes unwieldy, a decision to move to
auto-discovery (e.g. scanning engine/modules/*/module.py for a Module
subclass) should get its own ADR rather than being folded in silently -
that's a real design tradeoff (explicitness vs convenience), not a trivial
technical detail.
"""

from engine.modules.context_detector.module import ContextDetectorModule
from engine.modules.host_discovery.module import HostDiscoveryModule
from engine.modules.port_scanner.module import PortScannerModule
from engine.modules.reporting.module import ReportingModule
from engine.modules.wifi_scan.module import WifiScanModule

MODULE_REGISTRY = {
    ContextDetectorModule.name: ContextDetectorModule,
    HostDiscoveryModule.name: HostDiscoveryModule,
    PortScannerModule.name: PortScannerModule,
    ReportingModule.name: ReportingModule,
    WifiScanModule.name: WifiScanModule,
}


def get_module_class(name: str):
    if name not in MODULE_REGISTRY:
        raise KeyError(f"Unknown module '{name}'. Available: {sorted(MODULE_REGISTRY)}")
    return MODULE_REGISTRY[name]
