# ADR-0003: Contrat d'interface unique pour les modules d'analyse

## Statut
Accepté — 2026-07-10

## Contexte
Ce projet vise une plateforme évolutive où chaque fonctionnalité
est un module indépendant, testable isolément et documenté, et préfère
investir dans une architecture solide dès maintenant. Sans contrat
d'interface explicite, des modules développés au fil des itérations
risquent de diverger (formats de sortie différents, gestion d'erreurs
incohérente, logique de sécurité dupliquée dans chaque module).

## Décision
Tout module hérite de `engine.core.module_base.Module` (classe abstraite)
et respecte :

- Attributs de classe `name` (identifiant unique utilisé par le CLI et le
  registre) et `description`.
- Constructeur recevant uniquement un `PolicyClient` — aucune dépendance
  directe au `PolicyEngine`.
- Méthode `run(**kwargs) -> dict` retournant systématiquement une clé
  `status` valant `"ok"`, `"denied"`, ou `"error"`.
- Toute action nécessitant une capability doit passer par
  `self.policy.request(capability, target=...)` avant d'agir.

Chaque module vit dans `engine/modules/<nom>/` avec trois éléments
obligatoires : `module.py`, `SPEC.md`, `tests/`.

L'enregistrement des modules reste volontairement statique
(`engine/core/registry.py`, un dict explicite) plutôt qu'auto-découvert
par scan de répertoire, pour garder la liste des modules actifs visible en
un seul endroit et revue à chaque pull request. Si le nombre de modules
rend cela pénible, la bascule vers une auto-découverte doit faire l'objet
d'un nouvel ADR plutôt que d'un changement silencieux.

## Conséquences
- Le CLI, et tout futur module de reporting, peuvent traiter n'importe
  quel résultat de module de manière uniforme.
- Ajouter un module ne nécessite de modifier que deux fichiers existants :
  `engine/core/registry.py` (une ligne) et le cas échéant le CLI si le
  module a des arguments spécifiques.
- Les tests de module peuvent systématiquement mocker `PolicyClient`
  plutôt que le `PolicyEngine` complet, ce qui simplifie l'écriture de
  tests pour les futurs contributeurs.
