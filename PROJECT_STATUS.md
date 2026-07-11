# Project Status

**Version** : 0.9
**Statut** : Fondations et modules core livrés, testés (77 tests), et
validés sur appareil réel (Android/Termux).

## Résumé

Framework Android/Termux d'analyse réseau, construit autour d'une
séparation stricte entre l'Engine (modules d'analyse) et l'Execution
Policy (autorisation, profils, scopes). Voir `docs/ARCHITECTURE.md` pour
le détail.

## Composants livrés

| Composant | État |
|---|---|
| `engine/policy/` (PolicyEngine, 6 profils) | ✅ |
| `engine/core/` (Module, PolicyClient, registry, session log) | ✅ |
| `engine/modules/context_detector/` (contexte réseau, portail captif) | ✅ |
| `engine/modules/wifi_scan/` (réseaux Wi-Fi visibles) | ✅ |
| `engine/modules/host_discovery/` (cache ARP local) | ✅ |
| `engine/modules/port_scanner/` (scan actif autorisé) | ✅ |
| `engine/modules/reporting/` (rapport Markdown/HTML) | ✅ |
| `cli/ctk.py` | ✅ |
| Tests (77, tous modules) | ✅ |
| Documentation (architecture, 5 ADR, specs par module) | ✅ |

## Limitations connues (plateforme Android)

- `context_detector` et `host_discovery` dépendent de `ip` (iproute2),
  dont l'accès direct (netlink) est bloqué par Android sur la plupart des
  téléphones non rootés. `context_detector` a un repli automatique via
  Termux:API (Wi-Fi puis cellulaire) ; `host_discovery` n'a actuellement
  aucun repli équivalent et rapporte honnêtement une absence de données
  plutôt que d'en simuler.
- `wifi_scan` et `host_discovery` nécessitent le profil `home_lab`,
  `authorized_client`, ou `research` (capacité `passive_observe`) — non
  disponibles sous le profil `safe` par défaut, par choix architectural
  (voir ADR-0005).

## Installation (Termux)

```bash
pkg install python iproute2 nmap curl jq git termux-api
pip install -r requirements.txt
python -m pytest -q
```

Voir `README.md` pour l'usage complet, y compris le workflow de
démonstration client (`--profile authorized_client --authorize <IP>`).
