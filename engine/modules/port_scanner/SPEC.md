# Module: port_scanner

## Capability required
`active_probe`, scoped to `target`. Denied under `safe` and `developer`.
Under `home_lab`/`research`, allowed only inside the profile's pre-declared
ranges. Under `authorized_client`, denied until the operator runs with
`--authorize <cidr_or_host>` for that specific engagement.

## Purpose
Reference implementation of an *active* module, to validate that the
engine/policy separation actually gates active behavior rather than just
looking correct on paper. Wraps `nmap -Pn -p <ports> <target>`.

## Inputs
- `target` (required): host or CIDR to scan.
- `ports` (optional, default `1-1024`): nmap port spec.

## Output shape
```json
{"status": "ok", "target": "192.168.1.10", "ports": "1-1024", "raw_output": "..."}
```
or `{"status": "denied", "reason": "..."}` / `{"status": "error", "reason": "..."}`.

## Dependencies
`nmap`. On Termux: `pkg install nmap`.

## Explicit non-goals
This module does not do service exploitation, vulnerability scoring, or
credential attacks. Capability.ACTIVE_INTRUSIVE is hard-denied at the
policy engine level (see ADR-0001) and no module in this framework is
meant to request it.
