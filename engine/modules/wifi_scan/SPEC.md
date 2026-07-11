# Module: wifi_scan

## Capability required
`passive_observe` — reads Android's own last Wi-Fi scan result cache
(`termux-wifi-scaninfo`), sends no packets, attempts no association. See
`docs/adr/ADR-0005-wifi-scan-passive-observe.md` for why this is
classified `passive_observe` rather than `passive_local`: it's information
about the environment around the device (including networks not joined),
not about the device's own connection.

**Not available under the `safe` profile.** Requires `home_lab`,
`authorized_client`, or `research` (the profiles that already grant
`passive_observe`).

## Purpose
Lists nearby visible Wi-Fi networks with signal strength and the security
type each one's beacon advertises — useful for a quick site survey (e.g.
"what's the strongest network here, is it open or encrypted").

## Explicit non-goals
This module does **not**:
- test or guess any password / passphrase,
- attempt to join, associate with, or otherwise interact with any listed
  network,
- assess the actual cryptographic strength of a network's security — only
  reports the encryption type its beacon claims to support (WPA2/WPA3/
  WEP/open), which is publicly broadcast information, not an evaluation.

If you're looking for something closer to a vulnerability assessment,
that would need a new, more restrictive capability and its own ADR - it
isn't in scope here.

## Inputs
None.

## Output shape
```json
{
  "status": "ok",
  "networks_count": 2,
  "networks": [
    {
      "ssid": "HomeNet",
      "bssid": "aa:bb:cc:dd:ee:ff",
      "frequency_mhz": 5200,
      "channel": 40,
      "rssi_dbm": -42,
      "signal_quality": "excellent",
      "security": "WPA2"
    },
    {
      "ssid": "<hidden>",
      "bssid": "aa:bb:cc:dd:ee:ff",
      "frequency_mhz": 2437,
      "channel": 6,
      "rssi_dbm": -78,
      "signal_quality": "weak",
      "security": "open"
    }
  ]
}
```
Sorted strongest signal first. `security` is one of `WPA3`, `WPA2`,
`WPA`, `WEP`, `open`, or `unknown` (capabilities field absent/unparseable).
`channel` is derived from frequency and may be `null` for frequencies
outside the recognized 2.4/5/6 GHz ranges.

## Platform notes
- **Location must be enabled.** Android requires `ACCESS_FINE_LOCATION`
  to return Wi-Fi scan results; this is an OS-level privacy restriction,
  not something this framework controls. If location is off, Android
  returns an explicit error which this module surfaces as
  `{"status": "error", "reason": "..."}` rather than an empty list.
- **Stale results possible.** `termux-wifi-scaninfo` returns Android's
  *last completed* scan, not a fresh one - results can be several minutes
  old if nothing has triggered a rescan recently (see
  termux/termux-api#678 upstream). No workaround is implemented here.
- **Field names may need adjustment on real devices.** As with
  `context_detector`'s `termux_api_wifi_info`, the exact JSON keys
  Termux:API returns have drifted across versions in the past
  (`dhcp_server` absence was one example). This module reads `rssi`/`level`
  and `frequency_mhz`/`frequency` defensively but has not yet been
  validated against a real `termux-wifi-scaninfo` payload - treat the
  first field-test run as a validation step, same as other Termux:API
  modules were.

## Dependencies
`termux-api` (`pkg install termux-api`) + the Termux:API companion app.
