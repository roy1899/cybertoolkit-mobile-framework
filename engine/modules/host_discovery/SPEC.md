# Module: host_discovery

## Capability required
`passive_observe` — reads the device's own ARP/neighbor cache. This is
the canonical example that capability was defined for (see
`engine/policy/schema.py`). Sends no probe packets to anyone. **Not
available under the `safe` profile** by default; requires `home_lab`,
`authorized_client`, or `research`.

## Purpose
Shows which hosts are already visible in the device's ARP/neighbor cache
— useful to check whether Wi-Fi client isolation is actually enabled on a
network. If isolation works, this should show essentially nothing beyond
the gateway. If it shows other clients' IPs/MACs, that's evidence of a
misconfiguration worth reporting to the network owner (under an
`authorized_client` engagement).

## Explicit non-goal
This module never sends a packet to discover anything - no ping sweep, no
ARP request, no probe of any kind. It only reads what the kernel has
already resolved through normal traffic. An empty result on a
well-isolated network is the *correct*, useful answer, not a failure.

## Inputs
None.

## Output shape
```json
{
  "status": "ok",
  "hosts_count": 1,
  "hosts": [
    {"ip": "192.168.1.1", "mac": "aa:bb:cc:dd:ee:ff", "device": "wlan0", "state": "REACHABLE", "source": "ip_neigh"}
  ]
}
```
If nothing was found and netlink was blocked, a `note` field explains why
(see platform note below) rather than leaving the empty result
unexplained.

## Platform notes (important)
- **Most non-rooted Android phones will report empty results.** `ip
  neigh show` requires netlink access, which Android's SELinux policy
  blocks for unprivileged apps (same restriction as `context_detector`'s
  `ip addr` path). Unlike Wi-Fi/cellular detection, **there is currently
  no Termux:API command that exposes ARP/neighbor data**, so there is no
  fallback here. This is a real platform limitation, not a bug — the
  module reports it honestly via the `note` field rather than faking
  data.
- Works normally on: rooted Android devices, Termux environments where
  netlink permission is available, and standard (non-Android) Linux.
- `/proc/net/arp` is tried as a secondary source when `ip neigh` finds
  nothing, since some environments expose it even when netlink access is
  blocked - but this is not guaranteed either.

## Dependencies
`ip` (iproute2), already required by `context_detector`. No additional
package needed for the primary path; no Termux:API command exists yet for
the fallback path on Android.
