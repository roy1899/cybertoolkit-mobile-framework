# ADR-0005: L'inventaire des réseaux Wi-Fi visibles est `passive_observe`, pas `passive_local`

## Statut
Accepté — 2026-07-10

## Contexte
`context_detector` (`passive_local`) répond à "sur quel réseau suis-je ?".
Une nouvelle demande porte sur "quels réseaux sont visibles autour de
moi ?" — via `termux-wifi-scaninfo`, qui restitue le dernier scan Wi-Fi
effectué par Android (SSID, BSSID, RSSI, fréquence, type de chiffrement
annoncé dans la balise). Aucun paquet n'est envoyé à ces réseaux, aucune
tentative d'association ou d'accès n'est faite — l'opérateur ne fait que
lire ce qu'Android a déjà capté passivement.

Se pose la question : est-ce `passive_local` (comme le reste de
`context_detector`) ou une autre capability ?

## Décision
C'est `passive_observe`, pas `passive_local`. Distinction posée :

- `passive_local` = état de l'appareil et de *sa* connexion actuelle
  (interfaces, route par défaut, réseau auquel je suis attaché).
- `passive_observe` = état de l'environnement *autour* de l'appareil,
  au-delà de sa propre connexion — y compris des réseaux que l'opérateur
  n'a pas rejoints et ne possède pas forcément.

Conséquence pratique : ce nouveau module (`wifi_scan`) n'est **pas**
accessible sous le profil `safe` par défaut — il nécessite `home_lab`,
`authorized_client`, ou `research` (les seuls profils qui accordent déjà
`passive_observe`). C'est un choix délibéré : même si l'action elle-même
ne touche aucun tiers, révéler la liste des réseaux environnants
(y compris ceux de voisins ou de tiers non consultés) ne doit pas être le
comportement par défaut le plus permissif du framework.

## Portée explicite de ce que révèle ce module
- SSID, BSSID, force du signal (RSSI), fréquence/canal, type de
  chiffrement annoncé (WPA2/WPA3/WEP/ouvert) — toutes des informations
  diffusées publiquement par les points d'accès eux-mêmes dans leurs
  trames de balise (beacon frames), captées par n'importe quel appareil à
  portée sans action spécifique.
- Ce module ne teste, n'exploite, ni ne devine aucun mot de passe. Le
  "type de chiffrement" est l'annonce du point d'accès, pas une évaluation
  de sa robustesse réelle. Ce n'est pas un scanner de vulnérabilités.

## Conséquences
- Nécessite `ACCESS_FINE_LOCATION` côté Android (restriction du système
  d'exploitation, pas du framework) : si la localisation est désactivée,
  Android retourne une erreur explicite que le module remonte telle
  quelle plutôt que de la masquer.
- Si une future évolution voulait ajouter une évaluation de sécurité
  réelle (ex: détection de vulnérabilités WPS, chiffrement faible connu),
  cela sortirait du périmètre `passive_observe` tel que défini ici et
  mériterait son propre ADR.
