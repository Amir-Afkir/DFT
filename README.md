# DFT - Dépannage Fuite Toiture

Site vitrine final statique pour DFT / Dépannage Fuite Toiture.

## Structure

```text
dft-site/
  assets/
    images/
      hero-intervention.jpg
      hero-intervention.webp
      controle-etancheite-toiture.jpg
      controle-etancheite-toiture.webp
      inspection-zone-difficile.jpg
      inspection-zone-difficile.webp
      releve-diagnostic-infiltration.webp
      controle-zone-infiltration.webp
      intervention-toiture-camion-dft.webp
      toiture-ancienne-cour.webp
      toiture-ancienne-lucarne.webp
      toitures-anciennes-centre-ville.webp
      noue-zinc-toiture-tuiles-detail.webp
      noue-zinc-toiture-tuiles-vue-large.webp
      noue-zinc-tuiles-canal-toiture.webp
      perforation-noue-zinc-recherche-fuite.webp
      toiture-tuiles-anciennes-gouttiere-zinc.webp
      tuile-faitage-cassee-toiture.webp
      toiture-terrasse.jpg
      toiture-terrasse.webp
      infiltration-plafond.jpg
      infiltration-plafond.webp
      infiltration-fenetre.jpg
      infiltration-fenetre.webp
      degat-interieur.jpg
      degat-interieur.webp
    logo/
      logo-dft.png
  index.html
  robots.txt
  sitemap.xml
  README.md
```

## Mapping des fichiers source

- `archive/5ème photo.jpg` -> `assets/images/hero-intervention.jpg`
- `archive/3ème photo profil.jpg` -> `assets/images/controle-etancheite-toiture.jpg`
- `archive/2ème photo profil.jpg` -> `assets/images/inspection-zone-difficile.jpg`
- `archive/4ème photo.jpg` -> `assets/images/toiture-terrasse.jpg`
- `archive/1er photo profil google.jpg` -> `assets/images/infiltration-plafond.jpg`
- `archive/6ème photo.jpg` -> `assets/images/infiltration-fenetre.jpg`
- `archive/5ème photo.jpg` -> `assets/images/degat-interieur.jpg`
- `archive/unused-assets/*` -> images terrain WebP renommées selon leur usage marketing : intervention, diagnostic, défaut de noue zinc, toiture ancienne.
- `archive/Logo DFT.png` -> `assets/logo/logo-dft.png`

Les fichiers HTML concurrents et les notes papier sont conservés dans `archive/`.

## Choix de contenu

- Base visuelle retenue : `archive/gemini-code-1778516314661.html`, pour son approche plus premium, éditoriale et asymétrique.
- Base structurelle retenue : `archive/index (1).html`, pour sa navigation, ses sections complètes, ses avis explicitement marqués comme exemples et son meilleur socle d’accessibilité.
- Contenus terrain intégrés après confirmation : recherche de fuite, intervention d’urgence, mise hors d’eau, réparation toiture, rapport d’intervention et contrats d’entretien.
- Promesses encadrées : disponibilité `24h/24` et `7j/7` affichée, sans délai horaire garanti. Les avis clients réels restent absents tant qu’ils ne sont pas fournis ou vérifiés.
- Les noms de matériel et de marques techniques ne sont plus affichés dans le contenu public du site.

## Optimisations

- Les photos restent conservées en JPG, mais le site charge les versions WebP locales pour améliorer le poids mobile.
- Les contenus WebP distincts sont utilisés dans `index.html` avec une hiérarchie : hero, symptômes, diagnostic, causes fréquentes, lecture globale, toiture terrasse.
- Les images hors hero sont en `loading="lazy"`, avec `width`, `height`, `decoding="async"` et des ratios CSS contrôlés.
- `robots.txt`, `sitemap.xml`, canonical et métas OpenGraph/Twitter utilisent `https://dft45.net/` comme domaine cible. À ajuster si le domaine final change.
- Le logo a été réduit à une taille plus adaptée à son usage dans l’interface.

## Demande de diagnostic

- Les CTA `Demander un diagnostic` ouvrent un flow en 2 étapes.
- Sur desktop et tablette, le formulaire est intégré dans la section `#diagnostic`.
- Sur mobile, le même formulaire est déplacé dans une bottom sheet pour réduire la friction.
- Le formulaire est prêt pour Netlify Forms grâce à `data-netlify="true"` et au champ caché `form-name`.
- Pour Formspree, ajouter l’URL Formspree dans l’attribut `action` du formulaire.
- Pour un backend futur, conserver les champs `situation`, `address`, `first_name`, `last_name`, `phone`, `email`, `message` et `privacy`.

## Ouvrir le site

Ouvrir directement `index.html` dans un navigateur.
