# ADR-0002: `active_probe` exige toujours un scope explicitement autorisé

## Statut
Accepté — 2026-07-10

## Contexte
Un profil qui "autorise" la capacité `active_probe` (ex: `home_lab`,
`research`, `authorized_client`) ne doit pas être interprété comme
"autorise le scan de n'importe quelle cible". Le risque identifié : si
l'autorisation de capacité suffisait à elle seule, passer en profil
`home_lab` puis fournir accidentellement une cible hors du réseau
personnel (ex: une IP publique) déclencherait un scan non autorisé.

## Décision
`PolicyEngine.authorize()` applique une double vérification pour
`ACTIVE_PROBE` :
1. Le profil actif doit lister `active_probe` dans `allow_capabilities`.
2. **Et**, indépendamment, la cible demandée doit être contenue dans un
   scope de `authorized_scopes` — qu'il soit pré-déclaré dans le fichier
   du profil (cas `home_lab`, `research`) ou ajouté explicitement à
   l'exécution via `PolicyEngine.authorize_scope()` / `ctk --authorize`
   (cas typique `authorized_client`, où aucun scope n'est pré-déclaré par
   design).

Cette vérification de scope est faite via `ipaddress.ip_network`, avec
repli sur comparaison de chaîne exacte pour les cibles non-IP (noms
d'hôte), pour rester utilisable sur des cibles nommées.

## Conséquences
- Le profil `authorized_client` est volontairement livré sans aucun scope
  pré-approuvé : chaque mission doit être confirmée séparément, ce qui
  crée une trace explicite dans l'historique de commandes de la session.
- Les profils `home_lab`/`research` restent pratiques au quotidien (pas de
  confirmation à chaque commande) tout en gardant un plafond défini par
  les plages déclarées dans leur fichier YAML.
- Limite acceptée : les plages RFC1918 par défaut de `home_lab` supposent
  que l'opérateur est effectivement sur son propre réseau domestique.
  C'est documenté dans `home_lab.yaml` avec une invitation explicite à
  restreindre ces plages à son sous-réseau réel si besoin.
