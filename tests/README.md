# Régression du formulaire de diagnostic

Le champ `address` conserve le nom attendu par Netlify Forms. Il contient l’adresse canonique sélectionnée, avec numéro, rue, code postal et commune.

## Règle de saisie

Seuls les résultats `housenumber` de la Base Adresse Nationale, via le géocodage Géoplateforme IGN, sont proposés. Une ville seule, une rue sans numéro ou du texte non sélectionné ne permettent pas de continuer. Toute modification annule la sélection, et le formulaire vérifie de nouveau l’adresse avant l’envoi final.

L’interface distingue recherche en cours, absence de résultat, indisponibilité et délai dépassé. Les réponses obsolètes sont ignorées. Les adresses sans numéro ou absentes de la base nécessitent un contact téléphonique : le lien DFT reste proposé, sans contourner la règle du formulaire.

## Exécution

Depuis la racine du dépôt, avec Python 3 :

```sh
python3 -m pip install playwright==1.57.0
python3 -m playwright install --with-deps chromium webkit
python3 tests/address_autocomplete.py
```

Les 54 cas couvrent Chromium et WebKit en 1440 × 900, 390 × 844 et 320 × 640 : ville rejetée, sélection clavier et tactile, invalidation après édition, contenu transmis, revalidation à l’envoi, panne et nouvelle tentative, absence de résultat, réponses obsolètes, temporisation, Escape/Tab, changement de format et rendu sûr des textes de l’API. Les appels du géocodeur sont simulés pour rendre la suite reproductible. Aucun formulaire réel n’est envoyé.

Les résultats et captures sont écrits dans `tests/address-results.json` et `tests/screenshots/`.

Validation initiale : 54/54 tests réussis, plus un appel réel du service de géocodage, dans https://github.com/Amir-Afkir/DFT/actions/runs/36158584234 (25 septembre 2026). Le workflow temporaire de préparation et de validation reste uniquement sur la branche de travail ; il ne fait pas partie du site livré.

## Limite

Le site reste statique : il s’agit d’une validation côté navigateur pour guider les visiteurs, pas d’une protection contre une requête POST forgée. Une garantie contre le contournement nécessiterait un contrôle supplémentaire côté serveur. La présence dans la BAN ne prouve pas que le visiteur habite à cette adresse.
