# Architecture — CyberToolkit Mobile Framework

## Vue d'ensemble

```
                     ┌───────────────────────┐
                     │          CLI          │  cli/ctk.py
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   Execution Policy     │  engine/policy/
                     │   (profiles + scopes)  │
                     └───────────┬───────────┘
                                 │ authorize(request) -> decision
                                 ▼
        ┌────────────────────────────────────────────┐
        │              PolicyClient (per module)      │  engine/core/policy_client.py
        └───────────┬──────────────────┬──────────────┘
                     ▼                  ▼
         ┌───────────────────┐  ┌───────────────────┐
         │ context_detector   │  │  port_scanner      │   engine/modules/*/module.py
         │ (passive_local)     │  │  (active_probe)    │
         └───────────────────┘  └───────────────────┘
```

## Principe directeur : Engine / Execution Policy

Le moteur d'analyse (les modules) ne contient **aucune** logique de
sécurité. Chaque module déclare simplement, avant d'agir, quelle
*capability* il a besoin d'exercer et sur quelle cible (`target=None` pour
une action strictement locale à l'appareil). Cette demande passe par un
`PolicyClient` propre au module, qui la transmet au `PolicyEngine`.

Le `PolicyEngine` est le seul composant qui connaît :
- le profil actif (`safe`, `home_lab`, `authorized_client`, `research`,
  `developer`, ou un profil `custom` défini par l'opérateur),
- les scopes explicitement autorisés pour la session,
- les règles absolues (ex: `ACTIVE_INTRUSIVE` toujours refusé).

Voir `docs/adr/ADR-0001-engine-policy-separation.md` pour la justification
complète de ce choix.

## Modèle de capacités (Capability)

| Capability | Sens | Requiert un scope autorisé ? |
|---|---|---|
| `passive_local` | Lecture d'informations locales à l'appareil (interfaces, routes...). Aucun paquet envoyé à un tiers. | Non |
| `passive_observe` | Observation passive d'un état déjà présent sur le segment local (ex: cache ARP). Aucun paquet de sonde envoyé. | Non (réservé pour usage futur) |
| `active_probe` | Envoi de paquets vers une cible/sous-réseau (scan de ports, ping sweep...). | **Oui, systématiquement** |
| `active_intrusive` | Exploitation, attaque de identifiants, ou toute action visant l'accès plutôt que l'observation. | N/A — jamais accordée, sur aucun profil |

Le détail des règles de résolution `authorize()` est dans
`engine/policy/policy_engine.py` (fortement commenté) et testé dans
`tests/test_policy_engine.py`.

## Profils d'Execution Policy

Fichiers YAML dans `engine/policy/profiles/`. Chaque profil déclare
`allow_capabilities` (quelles classes d'action sont possibles) et
`authorized_scopes` (quelles cibles sont pré-approuvées, le cas échéant).

| Profil | Usage prévu | Scopes pré-approuvés |
|---|---|---|
| `safe` (défaut) | N'importe quel réseau, y compris public | Aucun (pas nécessaire, aucune action active) |
| `home_lab` | Réseau personnel possédé par l'opérateur | Plages RFC1918 par défaut (à ajuster) |
| `authorized_client` | Mission cliente sous autorisation signée | Aucun par défaut — confirmation explicite obligatoire par mission (`--authorize`) |
| `research` | Développement du framework contre un lab local | `127.0.0.0/8` + sous-réseau de lab d'exemple |
| `developer` | Contribution au code du framework | Aucune capacité active — utiliser les tests avec mocks |
| `custom` (template) | Cas d'usage spécifique de l'opérateur | À définir en copiant `custom.yaml.example` |

Ajouter un profil = ajouter un fichier YAML. Aucune modification de code
n'est nécessaire pour cela — c'est le point central de la modularité
requise pour ce projet.

## Contrat des modules

Tout module hérite de `engine.core.module_base.Module` et implémente
`run(**kwargs) -> dict`, avec une convention de sortie uniforme :

```json
{"status": "ok" | "denied" | "error", ...}
```

Un module ne doit jamais :
- importer `engine.policy.policy_engine` directement,
- contenir une logique du type "si réseau public alors...",
- décider lui-même si une cible est autorisée.

Il doit systématiquement passer par `self.policy.request(capability,
target=...)` avant toute action et respecter la décision reçue.

Chaque module possède :
- `module.py` — l'implémentation,
- `SPEC.md` — capacité requise, entrées/sorties, dépendances, limites connues,
- `tests/` — tests unitaires avec mocks (aucun appel réseau réel dans les
  tests).

## CLI

`cli/ctk.py` est un point d'entrée fin : il charge le profil demandé
(`--profile`, défaut `safe`), applique d'éventuelles autorisations de scope
passées en argument (`--authorize`), instancie le module demandé via le
registre (`engine/core/registry.py`), et affiche le résultat en JSON. Le
code de sortie est `1` si le résultat est `denied`, ce qui permet un
scripting Termux simple (`ctk run port_scanner --target X || echo "not authorized"`).

## Extensibilité prévue

- **Nouveaux modules** : ajouter un dossier sous `engine/modules/`,
  implémenter `Module`, l'enregistrer dans `registry.py`, documenter via
  `SPEC.md`, tester.
- **Nouveaux profils** : ajouter un fichier YAML, aucune modification de
  code.
- **Reporting** (prévu en roadmap) : consommera les sorties JSON
  uniformes des modules sans connaître leurs détails internes.
- **Découverte automatique de modules** : envisagée si le nombre de
  modules rend le registre statique peu pratique — décision à documenter
  dans un ADR dédié plutôt qu'à faire implicitement (voir note dans
  `registry.py`).
