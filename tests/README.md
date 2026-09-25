# Régression du formulaire de diagnostic — UX v2

Le champ Netlify Forms `address` conserve son nom et reçoit uniquement l’adresse complète sélectionnée : numéro, rue, code postal et commune. La validation est revérifiée avant l’envoi final.

## Parcours

- La saisie peut commencer par une rue. Le service IGN `/geocodage/completion/` propose des rues ; choisir une rue prépare la saisie du numéro au début du champ, sans valider l’adresse.
- Avec un numéro en tête, `/geocodage/search?type=housenumber&autocomplete=true` fournit les composants structurés de l’adresse BAN. Le géocodage dispose déjà d’une autocomplétion intégrée ; il reste utilisé pour les adresses numérotées plutôt que de déduire un numéro d’un libellé.
- Une ville, un code postal ou une date dans un nom de rue ne constituent jamais un numéro de maison. Les résultats d’un autre numéro sont éliminés ; un suffixe explicitement saisi (bis, ter, lettre) est conservé.
- La recherche est favorisée autour d’Orléans et les résultats du Loiret sont prioritaires par défaut. Un code postal ou une commune explicitement saisis ont priorité. Aucun accès GPS ni blocage strict du reste de la France.
- La première suggestion est surlignée : Entrée la confirme. Tab, blur et défilement tactile ne valident rien. Les flèches font défiler la liste sans déplacer la page.
- Jusqu’à 7 suggestions affichées. Temporisation de 250 ms, annulation des requêtes obsolètes, délai maximal de 8 s, cache positif en mémoire uniquement (30 recherches, 2 minutes), vidé à la réinitialisation. Rien n’est conservé dans localStorage ni envoyé à un service analytics.
- Les adresses enregistrées du navigateur sont autorisées, mais doivent toujours être confirmées dans les suggestions. Les erreurs ne s’affichent plus en rouge pendant une correction en cours.
- En cas de panne ou d’adresse absente/sans numéro, le bouton de nouvelle tentative et/ou le téléphone DFT restent proposés, sans accepter une adresse incomplète.

## Tests

```sh
python3 -m pip install playwright==1.57.0
python3 -m playwright install --with-deps chromium webkit
python3 tests/address_autocomplete.py
```

23 scénarios sur Chromium et WebKit, en 1440 × 900, 390 × 844 et 320 × 640 (138 cas). Ils couvrent les parcours clavier/tactile, rues avant numéro, préférence Loiret et commune explicite, suffixes, mauvais numéros, remplissage natif, composition clavier, cache/reset, réponses tardives/malformées, délai dépassé, panne/nouvelle tentative, rendu sûr de l’API et contenu réellement transmis au formulaire.

Les appels API sont simulés dans les tests pour les rendre reproductibles ; aucun formulaire réel n’est envoyé. Le contrôle du contrat IGN réel est séparé dans le workflow de validation sur la branche de travail. Résultats et captures : `tests/address-results.json` et `tests/screenshots/` (non versionnés). Les essais émulent le tactile et les formats mobiles : ils ne remplacent pas une vérification avec le clavier virtuel et VoiceOver/TalkBack sur appareils physiques.

## Références du contrat

- https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/autocompletion/
- https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/geocodage/

## Limite

Le site reste statique : validation côté navigateur, pas une protection contre un POST forgé. Un contrôle serveur serait nécessaire contre un contournement volontaire. La présence dans la BAN ne prouve pas que le visiteur habite sur place. Les adresses légitimes absentes de la BAN ou sans numéro nécessitent encore un contact téléphonique.
