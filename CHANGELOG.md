# Changelog

## 1.0.2 — 2026-07-11
### Added
- `docs/TERMUX_DEV_ENVIRONMENT.md`: diagramme Mermaid des familles de
  commandes Termux utilisées sur ce projet, et procédure documentée pour
  obtenir un environnement Linux complet (Ubuntu via `proot-distro`) —
  utile pour des outils sans binaire natif `linux-arm64-android` (ex:
  Claude Code). Documente 3 pièges rencontrés en pratique : erreur
  "Invalid argument" sur les gros binaires (fix `PROOT_NO_SECCOMP=1`),
  isolation du système de fichiers (fix `--bind`), et le `npm` d'Ubuntu
  cassé par défaut (fix : installer Node.js via NodeSource). Inclut
  aussi la limitation réseau connue de `proot-distro` (pas d'interface
  physique réelle), pour éviter qu'un futur contributeur ne tente d'y
  faire tourner `host_discovery`/`context_detector` en pensant contourner
  les restrictions Android natives.

## 1.0.1 — 2026-07-11
### Added
- README: badges (licence, Python, tests, plateforme), aperçu visuel du
  rapport HTML généré (données fictives, généré directement avec le
  moteur de rendu du projet — pas un mockup externe).

## 1.0.0 — 2026-07-11
Première publication propre du dépôt (historique squashé, licence MIT,
aucune donnée personnelle). Voir `PROJECT_STATUS.md` pour l'état complet
des fonctionnalités livrées.

## 0.9.1 — 2026-07-11 (historique de développement, pré-v1.0.0)
### Fixed
- **Privacy**: real home network SSID and access point BSSID (used as
  example values while developing/testing `wifi_scan`/`context_detector`)
  were present in test fixtures and one SPEC.md example, now replaced
  with clearly fake placeholder values (`TestNet-Example`,
  `aa:bb:cc:dd:ee:ff`). These values had already been pushed to the
  public repository; history was rewritten separately to purge them (see
  repository notes) rather than just fixed going forward.
### Changed
- Removed `CLAUDE_OPERATING_MANUAL.md` (internal AI-agent development
  process notes, not relevant to using the framework) and reworded
  "Product Owner" references across docs to neutral project language, for
  a cleaner public-facing repository.
- `PROJECT_STATUS.md` rewritten from scratch — was stale at V0.1 status
  since the initial commit; now reflects the actual V0.9 state.

## 0.9 — 2026-07-10
### Added
- New `host_discovery` module: passively lists hosts already present in
  the device's own ARP/neighbor cache (`ip neigh show`, with `/proc/net/arp`
  as a secondary source). `passive_observe` capability — the canonical
  case that capability class was defined for. Sends no probe packets;
  useful to check whether Wi-Fi client isolation is actually enabled
  (empty result = isolation working, not a failure).
- Documented platform limitation honestly: unlike Wi-Fi/cellular
  detection, there is currently no Termux:API fallback for ARP/neighbor
  data, so most non-rooted Android phones will report an empty result
  with an explanatory `note` rather than working data. Works normally on
  rooted devices and standard Linux.
- `reporting`: new table rendering for `host_discovery` entries (IP, MAC,
  device, state, source).
- README: documented the "self-demonstration" workflow for client-facing
  pitches — using the operator's own second device as an explicitly
  authorized target, so a Wi-Fi security demo never touches a
  non-consenting third party's device. No new code needed for this; it's
  the existing `authorized_client` + `--authorize` mechanism used as
  intended.
- 8 new tests (7 host_discovery, 1 reporting table rendering). 77 tests
  total, up from 69.

## 0.8 — 2026-07-10
### Added
- New `wifi_scan` module: lists nearby visible Wi-Fi networks (SSID,
  BSSID, signal strength/quality, frequency/channel, advertised
  encryption type) via `termux-wifi-scaninfo`. Classified
  `passive_observe`, not `passive_local` (see
  `docs/adr/ADR-0005-wifi-scan-passive-observe.md`) — not available under
  the `safe` profile by default, since it reveals information about
  networks other than the operator's own connection.
- Explicit non-goals documented in SPEC.md: no credential testing, no
  association attempts, no vulnerability assessment - "security" is the
  AP's own beacon announcement (WPA2/WPA3/WEP/open), not an evaluation.
- Surfaces Android's `API_ERROR` (e.g. "Location needs to be enabled")
  as-is rather than masking it as an empty result, since Wi-Fi scan
  results require `ACCESS_FINE_LOCATION` on Android.
- `reporting`: new table rendering for `wifi_scan` entries (SSID, signal,
  RSSI, channel, security, BSSID), in both Markdown and HTML.
- 10 new tests (9 wifi_scan, 1 reporting table rendering). 69 tests
  total, up from 59.
### Known caveat
- Exact Termux:API field names for `termux-wifi-scaninfo` (`rssi` vs
  `level`, `frequency_mhz` vs `frequency`) are handled defensively but
  not yet validated against a real device payload - flagged in backlog
  as the next thing to confirm in field testing, same as happened with
  `context_detector`'s `dhcp_server` field previously.

## 0.7 — 2026-07-10
### Changed
- `reporting`: `context_detector` entries now show the full interface
  list and, when available, complete Termux:API Wi-Fi details (SSID,
  BSSID, frequency, link speed, RSSI, hidden flag) or cellular details
  (cell type) in the curated summary — not just `network_type_guess`.
  Requested after real-world use showed the previous summary was too
  thin for field diagnostics.
- Every report section now includes a collapsible "Raw data" block with
  the complete underlying JSON, so nothing is ever silently dropped from
  the report regardless of how the curated view formats it.
### Added
- New `network_label` field in the reporting module's output: the SSID
  (or network type as fallback) from the most recent `context_detector`
  entry.
- CLI: `ctk run reporting` with no `--output` now auto-generates an HTML
  file named after the detected network and timestamp
  (`cybertoolkit_report_<network>_<date>.html`), sanitized for filesystem
  safety (handles spaces, accents, special characters).
- 12 new tests (6 reporting: enriched details + network label inference;
  6 CLI: filename sanitization + auto-naming behavior). 59 tests total,
  up from 48.

## 0.6 — 2026-07-10
### Added
- `reporting` module now also renders a self-contained HTML report
  (`report_html` field), inline CSS, no external assets, mobile-friendly
  viewport. All embedded content (including scan output) is HTML-escaped.
  Markdown and HTML are rendered from the same intermediate "sections"
  structure so they can't drift out of sync as new module types are
  added.
- CLI: `ctk run reporting --output report.html` writes the HTML version
  (detected by file extension); `.md` or any other extension writes
  Markdown as before.
- 3 new tests (HTML well-formed + escaping, empty-log HTML, markdown/HTML
  parity). 48 tests total, up from 45.

## 0.5 — 2026-07-10
### Added
- New `reporting` module: aggregates the local session log into a
  Markdown report. `passive_local` capability only (reads a local file,
  no network). Known modules (`context_detector`, `port_scanner`) get a
  readable summary; anything else falls back to a generic JSON block so
  nothing is silently dropped.
- New `engine/core/session_log.py`: lightweight JSONL append-only log,
  default path `~/.cache/cybertoolkit/session.jsonl`, overridable via
  `CTK_SESSION_LOG` env var (used by tests to avoid touching a real home
  directory).
- CLI: every `ctk run` now logs its result automatically (skip with
  `--no-log`; the `reporting` module itself is never logged, to avoid a
  report containing an entry for itself). New `ctk session path` / `ctk
  session clear` subcommands. New `run reporting --output <file>` writes
  the Markdown report to a file.
- 13 new tests (5 for session_log, 8 for reporting). 45 tests total, up
  from 32.

## 0.4 — 2026-07-10
### Added
- `context_detector`: Termux:API fallback now also tries cellular
  (`termux-telephony-cellinfo`) when Wi-Fi isn't connected, before giving
  up and reporting `"unavailable"`. Reports `network_type_guess: "cellular"`
  and cell `type`/registration info; no IP or gateway is available through
  this path (Termux:API doesn't expose it for cellular).
### Fixed
- `_termux_api_wifi_fallback` previously returned a "connected: false"
  dict when Wi-Fi wasn't the active connection, which silently prevented
  ever trying the cellular fallback. It now returns `None` in that case
  so the dispatcher moves on to cellular.
- 2 new tests (cellular fallback success, no-registered-cell case). 32
  tests total, up from 30.

## 0.3 — 2026-07-10
### Added
- `context_detector`: captive portal detection (`captive_portal` field:
  `true` / `false` / `null`). Uses a single fixed GET request to a
  well-known public connectivity-check endpoint
  (`connectivitycheck.gstatic.com/generate_204`) — classified `true` on
  redirect or unexpected status/body, `null` when offline/DNS-blocked
  rather than guessing. See `docs/adr/ADR-0004-captive-portal-passive-scope.md`
  for why this stays under `passive_local` despite being the only check
  in this module that sends a packet off-device.
- 4 new tests covering clean/redirect/wrong-status/offline cases, plus a
  `conftest.py` autouse fixture so the existing tests never make a real
  network call by default (30 tests total, up from 26).

## 0.2.1 — 2026-07-10
### Fixed
- `context_detector`: found via on-device testing — real `dhcp_server`
  field is absent from `termux-wifi-connectioninfo` output on at least
  some Android/Termux:API versions. `default_route.gateway` is now `null`
  when unknown, instead of the misleading string `"unknown"`. 26 tests
  total (+1).

## 0.2 — 2026-07-10
### Fixed
- `context_detector`: on stock (non-rooted) Android/Termux, `ip addr`/`ip
  route` fail with a netlink permission error (Android SELinux blocks
  unprivileged `AF_NETLINK` sockets) — confirmed on-device during initial
  field testing. The module now detects this and falls back to
  Termux:API (`termux-wifi-connectioninfo`) automatically. New
  `detection_method` field (`"ip"` | `"termux_api"` | `"unavailable"`)
  reports which path was used; when neither works, the module returns
  `status: "ok"` with a `note` telling the operator what to install,
  instead of returning empty/unknown fields with no explanation.
- 2 new tests covering the fallback and the fully-unavailable case (25
  tests total, up from 23).

## 0.1 — 2026-07-10
### Added
- Architecture Engine / Execution Policy (ADR-0001, ADR-0002, ADR-0003)
- `engine/policy/`: `PolicyEngine`, schéma `Capability`/`AuthorizationRequest`/
  `AuthorizationDecision`, 6 profils (`safe`, `home_lab`, `authorized_client`,
  `research`, `developer`, `custom.yaml.example`)
- `engine/core/`: contrat `Module`, `PolicyClient`, registre de modules
- Module `context_detector` (passif : interfaces, route par défaut, IPv6,
  VPN, heuristique de type de réseau)
- Module `port_scanner` (actif, gated par `active_probe` + scope autorisé)
- CLI `cli/ctk.py` (`list-modules`, `run`, `--profile`, `--authorize`)
- Suite de tests pytest (23 tests) couvrant moteur de politique, client de
  politique, et les deux modules
- Documentation : `docs/AUDIT_INITIAL.md`, `docs/ARCHITECTURE.md`,
  `docs/adr/`, `BACKLOG.md`, `ROADMAP.md` réécrits

## 0.5 (kit initial)
- Kit V5 (documentation de cadrage uniquement, aucun code)
