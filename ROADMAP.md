# Roadmap

## V0.1 — Fondations (cette itération)
- Séparation Engine / Execution Policy avec profils modulaires
- Contrat de module unique + registre
- Module passif de référence : `context_detector`
- Module actif de référence : `port_scanner`
- Suite de tests couvrant le moteur de politique et les deux modules
- Documentation : architecture, 3 ADR, audit initial

## V0.2 — Contexte réseau enrichi (livré, versions 0.2/0.2.1/0.3/0.4)
- Fallback Termux:API (Wi-Fi puis cellulaire) quand netlink est bloqué
  par Android
- Détection de portail captif dans `context_detector`
- [reste ouvert] Heuristiques Wi-Fi personnel vs public
- [reste ouvert] Commande `ctk profiles` pour lister les profils sans
  ouvrir les YAML
- [reste ouvert] Script d'installation Termux

## V0.3 — Reporting (livré, versions 0.5/0.6)
- Module `reporting` : agrégation Markdown des résultats de plusieurs
  modules exécutés dans une session (via un journal de session local)
- CLI : `ctk session path` / `ctk session clear`, `ctk run reporting --output`
- Export HTML autonome (CSS inline, format mobile-friendly)

## V0.4 — Découverte passive du réseau local
- Module `host_discovery` basé sur le cache ARP/voisinage
  (`passive_observe`), sans émission de sonde

## V0.5 — Élargissement des modules actifs
- Détection de service/version dans `port_scanner`
- Clarification de capability pour le ping-sweep (ADR dédié si
  `passive_observe` vs `active_probe` reste ambigu selon la méthode)

## Non planifié / hors périmètre assumé
- Tout module d'exploitation ou d'attaque de identifiants
  (`ACTIVE_INTRUSIVE` reste hard-denied, voir ADR-0001)

## Envisagé, non engagé
- Interface graphique (Termux:Widget, app Android native, ou interface
  web locale servie depuis l'appareil) au-dessus du CLI existant — le CLI
  restera la source de vérité fonctionnelle ; une GUI serait une couche
  de présentation, pas une réécriture de l'Engine/Execution Policy.
