# Audit Initial — CyberToolkit Mobile Framework

Date : 2026-07-10
Auteur : Agent (Lead Software Engineer)

## 1. État du dépôt au démarrage

Le kit fourni (`CyberToolkit_V5.zip`) contenait uniquement de la documentation
de cadrage, sans aucun code :

- `CLAUDE_OPERATING_MANUAL.md`, `README.md`, `BACKLOG.md` (3 lignes),
  `ROADMAP.md` (5 lignes), `PROJECT_STATUS.md`, `CHANGELOG.md`,
  `Overview.docx` — tous très courts.
- `docs/`, `architecture/`, `specs/`, `templates/`, `governance/`,
  `prompts/` — tous vides.

Aucune dette technique à auditer : il s'agit d'un démarrage propre depuis
zéro. Ce document sert donc de point de référence (baseline) plutôt que
d'audit correctif.

## 2. Décision de cadrage prise avant développement

L'objectif produit initial (détection automatique du contexte réseau et
adaptation des modules sur tout type de réseau, y compris Wi-Fi public,
hôtel, coworking) posait un risque : sans garde-fou architectural, un
framework qui minimise l'intervention manuelle de l'opérateur pourrait
aussi minimiser sa décision consciente d'autoriser (ou non) un scan actif
sur un réseau donné.

Décision produit validée avant le développement : séparation stricte entre :

- **Engine** — capable de réaliser toutes les analyses prévues, sans
  connaître de règles de sécurité.
- **Execution Policy** — seul composant habilité à autoriser ou refuser
  une action, via des profils modulaires (`safe`, `home_lab`,
  `authorized_client`, `research`, `developer`, `custom`).

Cette séparation est actée dans `docs/adr/ADR-0001-engine-policy-separation.md`
et implémentée dès la V0.1 (voir §4).

## 3. Forces

- Vision produit claire et cohérente (device Android/Termux comme
  plateforme d'analyse mobile).
- Contraintes techniques réalistes pour l'environnement cible (Bash,
  Python, Termux API, Nmap, curl, jq — outils déjà présents ou installables
  facilement sur Termux).
- Le projet a une exigence explicite de qualité architecturale
  ("investir dans une architecture solide plutôt que développer vite"),
  ce qui autorise à poser des fondations modulaires dès la V0.1 plutôt que
  de bricoler un MVP monolithique.

## 4. Faiblesses identifiées et actions prises

| Faiblesse constatée | Action |
|---|---|
| Aucune séparation entre "ce qu'un module peut faire" et "ce qui est autorisé" | Introduction de l'Execution Policy engine (`engine/policy/`) et du contrat `PolicyClient` que tout module doit utiliser. |
| Aucun mécanisme empêchant un scan actif non autorisé sur un réseau tiers | `Capability.ACTIVE_PROBE` requiert systématiquement une cible dans un scope explicitement autorisé, quel que soit le profil (voir ADR-0002). |
| Aucune capacité d'exploitation/attaque ne doit jamais exister dans ce framework | `Capability.ACTIVE_INTRUSIVE` est "hard-denied" au niveau du moteur, pour tous les profils, sans chemin de configuration pour l'activer (voir ADR-0001). |
| Backlog/roadmap trop sommaires pour guider un développement autonome multi-itérations | Backlog et roadmap réécrits avec granularité modulaire (voir `BACKLOG.md`, `ROADMAP.md`). |
| Pas de contrat d'interface pour les futurs modules (risque d'implémentations divergentes) | `engine/core/module_base.py` définit l'interface unique `Module.run(**kwargs) -> dict`, avec convention de sortie `status: ok|denied|error`. |
| Pas de tests dès la base du projet | Suite pytest dès la V0.1 (23 tests), couvrant le moteur de politique, le client de politique, et les deux modules de référence. |

## 5. Portée volontairement exclue (hors périmètre)

- Tout module d'exploitation, de brute-force de identifiants, ou de post-
  exploitation. `ACTIVE_INTRUSIVE` reste une capacité définie mais jamais
  accordée — voir ADR-0001 pour revenir sur cette décision si nécessaire.
- Auto-détection de portail captif : notée en backlog, non implémentée en
  V0.1.
- Détection VPN avancée (identification du protocole/fournisseur) : la V0.1
  ne fait que détecter la présence d'une interface tunnel générique.

## 6. Prochaines étapes

Voir `ROADMAP.md` et `BACKLOG.md`. Résumé : consolider le moteur de
contexte (détection portail captif, Wi-Fi vs cellulaire plus fine),
ajouter un module de reporting (agrégation JSON → Markdown/HTML), puis
étoffer les modules d'analyse passive avant d'élargir les modules actifs.
