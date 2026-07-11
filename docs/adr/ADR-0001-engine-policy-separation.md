# ADR-0001: Séparer strictement l'Engine et l'Execution Policy

## Statut
Accepté — 2026-07-10

## Contexte
Le framework doit pouvoir analyser des réseaux dans des contextes très
variés (domicile, Wi-Fi public, hôtel, coworking, réseau client, partage
de connexion, VPN) tout en minimisant les manipulations manuelles de
l'opérateur. Sans garde-fou architectural, ces deux objectifs entrent en
tension : automatiser trop agressivement l'adaptation au contexte pourrait
finir par automatiser aussi la décision d'agir sur un réseau que
l'opérateur ne possède pas et n'est pas autorisé à tester — ce qui est
illégal dans la plupart des juridictions et contraire à l'usage prévu du
framework (outil professionnel, réseaux autorisés uniquement).

## Décision
Le framework sépare strictement deux responsabilités :

1. **Engine** (modules d'analyse) — implémente toutes les capacités
   d'analyse prévues, sans aucune connaissance des règles de sécurité.
2. **Execution Policy** — seul composant habilité à décider si une action
   donnée (capability + cible) est autorisée, en fonction d'un profil
   configurable et de scopes explicitement confirmés.

Règles absolues, non contournables par configuration :
- `Capability.ACTIVE_INTRUSIVE` (exploitation, attaque de identifiants...)
  est refusée par le moteur de politique pour tous les profils, y compris
  tout profil `custom` créé ultérieurement. Ce framework n'implémente pas
  et n'a pas vocation à implémenter d'outillage d'exploitation.
- `Capability.ACTIVE_PROBE` (scan actif) exige toujours une cible incluse
  dans un scope explicitement autorisé — que ce scope soit pré-déclaré
  dans un profil (`home_lab`, `research`) ou confirmé à l'exécution
  (`authorized_client`, via `--authorize`).
- `Capability.PASSIVE_LOCAL` ne touche jamais un autre hôte et est
  autorisée sur tous les profils, y compris `safe` — c'est ce qui permet
  la détection de contexte "partout, sans friction" sans compromettre la
  sécurité.

## Conséquences
- Chaque module doit passer par `PolicyClient.request(...)` avant toute
  action ; c'est vérifié par convention de code et par les tests (chaque
  module a un test qui vérifie le comportement de refus).
- L'ajout d'un nouveau profil ne nécessite aucune modification de code
  (fichier YAML uniquement).
- Un audit de sécurité du framework peut se concentrer uniquement sur
  `engine/policy/` plutôt que sur l'ensemble du code des modules.
- Limite acceptée : cette architecture ne protège pas contre un module
  malveillant qui ignorerait délibérément la réponse du policy engine.
  Elle protège contre l'erreur et la dérive de configuration, pas contre
  un module écrit avec l'intention explicite de contourner la politique.
  Toute contribution de module doit être relue en gardant ce point en tête.
