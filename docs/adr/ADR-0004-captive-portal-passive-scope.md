# ADR-0004: La détection de portail captif reste `passive_local`, malgré la requête réseau sortante

## Statut
Accepté — 2026-07-10

## Contexte
Toutes les autres vérifications de `context_detector` classées `passive_local`
ne font que lire l'état local de l'appareil (interfaces, routes, cache
Termux:API) — aucune ne contacte un hôte distant. La détection de portail
captif est différente par nature : la seule façon fiable de savoir si on
est bloqué derrière une page de connexion est d'émettre une requête HTTP
sortante vers un endpoint de test et d'observer si la réponse est celle
attendue ou si elle a été interceptée/redirigée.

Se pose la question : cette action franchit-elle la frontière vers
`active_probe` (qui exige une cible dans un scope autorisé) ?

## Décision
Non — la détection de portail captif reste sous `passive_local`, à
condition stricte de respecter ces critères :

1. **La cible est un endpoint public de vérification de connectivité bien
   connu** (ex: `connectivitycheck.gstatic.com/generate_204`,
   `captive.apple.com`), pas un hôte du réseau local ni une cible fournie
   par l'opérateur ou par un autre module.
2. **La requête est un GET simple, sans charge utile, sans tentative
   d'énumération ou de découverte** — c'est une vérification d'état de
   connectivité, pas de la reconnaissance.
3. **C'est un comportement que l'appareil effectue déjà par défaut** : tout
   smartphone Android/iOS envoie ce type de requête automatiquement à
   chaque changement de réseau pour afficher l'icône "Wi-Fi sans internet"
   / portail captif. Le framework ne fait qu'exposer une information que
   le système d'exploitation calcule déjà en permanence.

Si un module futur avait besoin de contacter un hôte *du réseau local*
(qu'il s'agisse d'un routeur, d'un pair, ou de tout autre appareil), cette
règle ne s'appliquerait plus : ce serait `active_probe`, avec vérification
de scope, même pour un simple ping.

## Conséquences
- Le champ `captive_portal` (`true`/`false`/`null`) est disponible sur tous
  les profils, y compris `safe`, sans confirmation d'autorisation.
- Le endpoint de test est codé en dur dans le module (pas configurable par
  l'opérateur au niveau du profil), précisément pour garantir que le
  critère n°1 ci-dessus reste vrai à chaque exécution — un endpoint
  configurable ouvrirait la porte à un contournement de la portée
  `passive_local`.
- Si l'appareil est hors-ligne ou si le DNS échoue, le module retourne
  `captive_portal: null` (indéterminé) plutôt que de faire échouer
  l'exécution — l'absence de connectivité n'est pas une erreur du module.
