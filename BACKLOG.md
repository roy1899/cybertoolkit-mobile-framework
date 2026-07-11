# Backlog

Convention : chaque item référence le module ou composant concerné.
Statut : `done` / `next` / `planned`.

## Fondations (Core)
- [done] Séparation Engine / Execution Policy (`engine/policy/`, ADR-0001)
- [done] Contrat de module unique (`engine/core/module_base.py`, ADR-0003)
- [done] Registre de modules statique (`engine/core/registry.py`)
- [done] CLI (`cli/ctk.py`) avec sélection de profil et confirmation de scope
- [planned] Fichier de configuration utilisateur (`~/.config/ctk/config.yaml`)
  pour fixer un profil par défaut par machine, au lieu de `safe` en dur

## Execution Policy
- [done] Profils `safe`, `home_lab`, `authorized_client`, `research`, `developer`
- [done] Template `custom.yaml.example`
- [planned] Commande `ctk profiles` pour lister les profils disponibles avec
  leur description et leurs capacités (actuellement il faut ouvrir les YAML)
- [planned] Journalisation locale des autorisations de scope accordées
  pendant une session (`ctk --authorize`), pour garder une trace des
  missions `authorized_client`

## Module: context_detector
- [done] Détection interfaces / route par défaut / IPv6 global / VPN générique
- [done] Fallback Termux:API quand l'accès netlink est bloqué par Android
  (cas réel rencontré en test terrain sur appareil non-rooté) — voir
  CHANGELOG 0.2
- [done] Détection de portail captif via requête GET vers un endpoint
  public fixe (`generate_204`), toujours classée `passive_local` — voir
  ADR-0004. CHANGELOG 0.3.
- [done] Extension du fallback Termux:API à la détection cellulaire
  (`termux-telephony-cellinfo`) — voir CHANGELOG 0.4. Pas d'IP/passerelle
  disponible sur ce chemin, seulement le type de cellule et l'état
  d'enregistrement.
- [planned] USB tether via Termux:API reste non couvert (pas de commande
  Termux:API dédiée identifiée à ce jour) — sur netlink bloqué + partage
  de connexion USB actif, le résultat reste "unavailable" ou "unknown"
  selon si le Wi-Fi/cellulaire sont aussi inactifs
- [planned] Distinction plus fine Wi-Fi personnel vs Wi-Fi public via
  heuristiques complémentaires (SSID connu, nombre de clients visibles en
  DHCP local, etc.)
- [planned] Identification du protocole VPN (WireGuard vs OpenVPN vs
  IPsec) au lieu d'un simple booléen

## Module: port_scanner
- [done] Scan de ports via nmap, gated par `active_probe` + scope
- [next] Détection de service/version (`nmap -sV`) en option
- [planned] Mode ping-sweep séparé (`passive_observe` si basé sur
  ARP/mDNS déjà présent sur le segment, `active_probe` si ICMP actif —
  nécessite une clarification de capability, voir note ADR à rédiger)

## Nouveau module: reporting
- [done] Agrégation des résultats JSON de plusieurs modules en un rapport
  Markdown lisible sur mobile — voir CHANGELOG 0.5
- [done] Export HTML autonome (un seul fichier, CSS inline, pas de
  dépendances externes, viewport mobile) — voir CHANGELOG 0.6
- [planned] Rotation/purge automatique du journal de session au-delà
  d'une certaine taille (pas un problème à l'usage actuel, mais à
  surveiller)

## Nouveau module: host_discovery (passif)
- [done] Lecture du cache ARP/voisinage local (`passive_observe`) pour
  lister les hôtes déjà visibles sur le segment sans émettre de sonde —
  voir CHANGELOG 0.9. Pas de fallback Termux:API disponible (contrairement
  à Wi-Fi/cellulaire) : rapporte honnêtement "indéterminé" sur Android non
  rooté plutôt que de simuler un résultat.

## Nouveau module: wifi_scan (passif)
- [done] Inventaire des réseaux Wi-Fi visibles à proximité (SSID, BSSID,
  RSSI, canal, type de chiffrement annoncé), classé `passive_observe`
  (ADR-0005), non disponible sous `safe` par défaut. Intégré au rapport
  (`reporting`). CHANGELOG 0.8.
- [next] Valider les noms de champs réels de `termux-wifi-scaninfo` sur
  device (rssi vs level, frequency vs frequency_mhz) — écrit
  défensivement mais pas encore confirmé face à un vrai payload, comme
  pour `context_detector` en son temps
- [planned] Rafraîchir le scan avant lecture (`termux-wifi-scaninfo` lit
  le dernier scan Android, potentiellement vieux de plusieurs minutes —
  pas de commande Termux:API dédiée pour déclencher un scan à la demande
  à ce jour, voir termux/termux-api#678)

## Qualité / process
- [done] Suite de tests pytest dès la V0.1 (moteur de politique, client de
  politique, 2 modules de référence)
- [done] Validation de `port_scanner` sur appareil réel (2026-07-11)
- [done] README : étapes d'installation complètes + section Dépannage
- [next] Test d'installation "à froid" (README suivi du début à la fin
  sur un Termux fraîchement installé, sans aucune commande tapée en
  amont) — vérifier qu'aucune étape implicite n'a été oubliée
- [next] Validation sur un second appareil Android (fabricant/version
  différents du device de développement actuel) pour confirmer que les
  comportements observés (noms de champs Termux:API, restrictions
  netlink...) ne sont pas spécifiques à un seul device
- [next] CI minimale (lint + tests) — à définir selon ce que Termux/GitHub
  Actions permettent réellement d'exécuter
- [planned] Script d'installation Termux (`scripts/install_termux.sh`) qui
  vérifie/installe `iproute2`, `nmap`, `curl`, `jq`, `python`, `termux-api`
- [planned] Guide "Getting started" orienté terrain (utilisateur terrain) séparé
  de la documentation orientée architecture (contributeurs)
