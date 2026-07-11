# Project Status

**Version** : 1.0.3
**Statut** : Fondations et modules core livrés, testés (77 tests), et
validés sur appareil réel (Android/Termux). `port_scanner` (module
actif) validé sur appareil réel le 2026-07-11.

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
| `engine/modules/context_detector/` (contexte réseau, portail captif) | ✅ testé sur device |
| `engine/modules/wifi_scan/` (réseaux Wi-Fi visibles) | ✅ testé sur device |
| `engine/modules/host_discovery/` (cache ARP local) | ✅ (limitation Android connue, voir plus bas) |
| `engine/modules/port_scanner/` (scan actif autorisé) | ✅ testé sur device |
| `engine/modules/reporting/` (rapport Markdown/HTML) | ✅ testé sur device |
| `cli/ctk.py` | ✅ testé sur device |
| Tests (77, tous modules) | ✅ |
| Documentation (architecture, 5 ADR, specs par module, dépannage) | ✅ |

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

## Préparation à un usage par des tiers

Le code, l'architecture et la documentation sont solides, mais la
validation terrain reste limitée à un seul appareil (celui de l'auteur).
Avant de considérer le projet pleinement prêt pour un tiers inconnu sur
un appareil quelconque :
- [fait] Valider `port_scanner` sur appareil réel
- [fait] Compléter le README (étapes d'installation manquantes, section
  dépannage)
- [à faire] Test d'installation "à froid" en suivant le README du début
  à la fin sur un Termux fraîchement installé
- [à faire] Validation sur un second appareil Android (fabricant/version
  différents) pour confirmer la portabilité au-delà d'un seul device

## Installation (Termux)

```bash
termux-change-repo
pkg install python iproute2 nmap curl jq git termux-api
termux-setup-storage
pip install -r requirements.txt
python -m pytest -q
```

Voir `README.md` pour l'usage complet, y compris le workflow de
démonstration client (`--profile authorized_client --authorize <IP>`) et
la section Dépannage.
