# Module: context_detector

## Capability required
`passive_local` — reads local device state only, sends no packets to any
other host. Permitted under every profile, including `safe`.

## Purpose
Answers "what network am I probably on" so other modules (and the CLI /
future reporting layer) can adapt without the operator typing an interface
name, IP range, or network type by hand.

## Inputs
None.

## Output shape
```json
{
  "status": "ok",
  "interfaces": [{"name": "wlan0", "state": "UP", "addresses": ["192.168.1.42/24"]}],
  "default_route": {"gateway": "192.168.1.1", "device": "wlan0"},
  "vpn_active": false,
  "ipv6_available": true,
  "network_type_guess": "wifi",
  "detection_method": "ip",
  "captive_portal": false
}
```
`captive_portal` is `true` / `false` / `null` (undetermined — e.g. device
offline or DNS blocked; not treated as an error). See
`docs/adr/ADR-0004-captive-portal-passive-scope.md` for why this check —
the only one in this module that sends a packet off-device — still counts
as `passive_local`.

If the policy engine denies the request (should not normally happen, since
`passive_local` is allowed everywhere), the module returns
`{"status": "denied", "reason": "..."}` instead.

## Dependencies
`ip` (iproute2). On Termux: `pkg install iproute2`.

**Android/Termux platform note**: on stock (non-rooted) Android, `ip addr`
/ `ip route` fail with `Cannot bind netlink socket: Permission denied` —
this is an Android SELinux restriction on unprivileged apps opening
`AF_NETLINK` sockets, not a missing-package issue, and installing
`iproute2` does not fix it. When this is detected, the module
automatically falls back to Termux:API, trying Wi-Fi first
(`termux-wifi-connectioninfo`) then cellular (`termux-telephony-cellinfo`).
This requires both `pkg install termux-api` and the separate
**Termux:API** companion app installed from F-Droid or Play Store.
Without either fallback, the module still returns `status: "ok"` with
`detection_method: "unavailable"` and a `note` field explaining what to
install, rather than failing.

The `detection_method` field in the output (`"ip"` | `"termux_api"` |
`"unavailable"`) tells you which path produced the result.

## Known limitations
- `network_type_guess` is a heuristic based on interface naming
  conventions (`wlan*`, `rmnet*`, `usb*`, `tun*`/`wg*`...) when using the
  `ip`-based path. Treat it as a best guess, not ground truth.
- The Termux:API cellular fallback only reports cell `type` (e.g. `lte`,
  `gsm`, `wcdma`) and registration status — no IP address or gateway is
  available through this path (`interfaces` stays empty, `default_route`
  stays `null` even though `network_type_guess` is `"cellular"`).
- VPN detection is not available through either Termux:API fallback path;
  it's only reported accurately when the `ip`-based path works.
- Captive portal detection uses a single fixed HTTP endpoint
  (`connectivitycheck.gstatic.com`); some captive portals allowlist that
  specific host to fool exactly this kind of check, so `false` is not an
  absolute guarantee. `true` and redirect-based detection are reliable;
  a small number of false negatives on sophisticated portals are possible.
