Oui. Voilà le brief que je te recommande pour un projet open source sérieux, moderne et vraiment “fini” dans son cadrage.

## Nom du repo

**`gitblend`**

### Description courte

**Native Git & GitHub workflows inside Blender for versioning, backup, review, and sharing of `.blend` projects.**

### Tagline

**Version your Blender projects like code, without leaving Blender.**

Le nom est simple, mémorisable, lisible sur GitHub, et il dit immédiatement ce que fait l’extension.

---

## Positionnement du projet

`gitblend` est une extension Blender open source qui apporte une vraie couche de versioning et de collaboration Git/GitHub dans Blender, pensée pour des projets `.blend` et leurs assets associés. Le projet ne doit pas essayer de “remplacer GitHub”, ni de faire croire que les merges binaires sont magiques. Il doit assumer que Blender manipule surtout des fichiers binaires et construire une UX fiable autour de snapshots, historique, branches, sync et partage. GitHub bloque les fichiers de plus de 100 MiB, et Git LFS existe précisément pour gérer ce type de contenu en stockant des pointeurs dans le repo à la place des gros fichiers. ([GitHub Docs][1])

Le projet doit être conçu comme une **extension Blender moderne**. Aujourd’hui, le packaging d’extensions Blender repose sur un archive `.zip` contenant un `blender_manifest.toml`, et Blender fournit aussi des commandes CLI officielles pour **build**, **validate** et même générer un index de repository d’extensions. Blender supporte aussi l’inclusion de **Python wheels** pour créer des extensions Python auto-contenues. ([Documentation Blender][2])

---

## But du projet

Le but n’est pas juste “faire des commits depuis Blender”.

Le vrai but est :

**Permettre à un artiste, un tech artist, un freelance ou une petite équipe de versionner, sauvegarder, restaurer, synchroniser et partager proprement un projet Blender complet directement depuis Blender, avec une UX adaptée aux fichiers binaires et aux assets externes.**

En pratique, `gitblend` doit résoudre 6 problèmes :

1. sauvegarder des états fiables d’un projet Blender ;
2. voir rapidement ce qui a changé ;
3. revenir à une version précédente sans se battre avec Git en ligne de commande ;
4. synchroniser avec GitHub ;
5. gérer correctement les gros fichiers via Git LFS ;
6. partager un projet avec des conventions saines de structure et de dépendances.

---

## Ce que doit être la v1.0

La v1.0 ne doit pas être “un MVP”. Elle doit être une extension aboutie avec un périmètre clair.

Elle doit être :

- robuste sur Windows, macOS et Linux ;
- utilisable par des non-développeurs ;
- packagée comme une vraie extension Blender moderne ;
- testée sur plusieurs versions Blender supportées ;
- documentée comme un vrai projet open source ;
- distribuable en zip installable directement dans Blender. Blender prend en charge l’installation d’extensions à partir d’un package `.zip`, et l’écosystème d’extensions officiel repose précisément sur ce mode de distribution. ([Documentation Blender][3])

---

## Features produit

Je séparerais les features en “core”, “GitHub native” et “protection du projet”.

### 1. Core project versioning

C’est le cœur du produit.

- Initialiser un repo Git depuis Blender.
- Détecter automatiquement le dossier projet à partir du `.blend`.
- Afficher le statut du working tree.
- Sauvegarder le `.blend` avant commit.
- Commit avec message manuel ou généré.
- Historique visuel des commits.
- Checkout d’un commit, branche ou tag.
- Revert d’un fichier ou d’un projet.
- Diff “métier” simplifié : au minimum liste des fichiers modifiés, renommés, supprimés.
- Création et changement de branches.
- Merge assisté avec UX claire en cas de conflit.
- Mode “safe restore” qui duplique le fichier courant avant rollback.

### 2. GitHub integration

Là, l’idée est de couvrir les workflows utiles, pas de cloner toute l’UI GitHub.

- Connexion GitHub via token ou device flow.
- Création d’un repo distant depuis Blender.
- Lier un repo local à GitHub.
- Push / pull / fetch.
- Voir les branches distantes.
- Publier une branche.
- Créer une Pull Request.
- Voir l’état d’une PR.
- Ouvrir rapidement le repo, le commit ou la PR dans le navigateur.
- Gérer releases/tags pour publier des versions du projet.

GitHub recommande les **fine-grained personal access tokens** quand c’est possible pour l’usage personnel de l’API, et documente aussi le **device flow** pour les applications “headless” de type CLI, ce qui colle très bien au contexte Blender. ([GitHub Docs][4])

### 3. Protection du projet Blender

C’est là que l’addon devient réellement bon.

- Détection des chemins absolus problématiques.
- Audit des textures manquantes.
- Audit des linked libraries et assets externes.
- Vérification avant commit : “ton projet n’est pas portable”.
- Proposition d’un `.gitignore` adapté Blender.
- Proposition d’un `.gitattributes` avec Git LFS.
- Setup automatique Git LFS pour `.blend`, `.fbx`, `.usd`, `.abc`, `.exr`, grosses textures, caches.
- Vérification de taille avant push.
- Détection des fichiers qui dépassent les limites GitHub standards.

GitHub documente que les gros fichiers doivent être suivis via Git LFS, que `git lfs track` modifie `.gitattributes`, et recommande de commit ce fichier dans le repo. GitHub bloque aussi les fichiers de plus de 100 MiB. ([GitHub Docs][5])

### 4. UX pensée Blender

- Panel dédié dans le Sidebar (`N-panel`) dans le 3D View et entrée dans le menu File.
- Notifications propres et non intrusives.
- Logs lisibles.
- États explicites : dirty, ahead, behind, conflicted, missing LFS, detached HEAD.
- Background tasks pour les opérations longues.
- Prévisualisation des changements avant commit.
- Historique avec auteur, date, branche, hash court.
- Boutons “Open in File Browser” et “Open on GitHub”.
- Préférences globales de l’addon : chemin de git, activation LFS, auth, comportement de save.

---

## Ce que l’addon ne doit pas promettre

Ça, c’est important pour éviter un mauvais produit.

- Pas de “merge intelligent de `.blend`”.
- Pas de promesse de collaboration temps réel.
- Pas de diff interne complet de scènes Blender au niveau sémantique dans la v1.
- Pas de remplacement total de Git CLI.
- Pas de sync silencieuse qui modifie le projet sans confirmation.

Le bon ton produit, c’est : **fiable, explicite, sûr**.

---

## Architecture recommandée

Il faut absolument éviter un addon “tout dans `__init__.py`”.

Je te conseille cette architecture :

```text
gitblend/
  blender_manifest.toml
  __init__.py
  registration.py

  ui/
    panels.py
    lists.py
    menus.py
    dialogs.py
    icons.py

  operators/
    project.py
    status.py
    commit.py
    history.py
    branch.py
    sync.py
    lfs.py
    github.py
    restore.py
    diagnostics.py

  domain/
    models.py
    enums.py
    errors.py
    result.py

  services/
    git_service.py
    github_service.py
    lfs_service.py
    blender_project_service.py
    diagnostics_service.py
    snapshot_service.py

  infrastructure/
    subprocess_runner.py
    auth_store.py
    file_system.py
    parser_git_status.py
    parser_git_log.py

  bpy_adapters/
    context.py
    paths.py
    reports.py
    jobs.py

  tests/
    unit/
    integration/
    fixtures/

  resources/
    templates/
      gitignore
      gitattributes
    icons/

  docs/
    architecture.md
    contributing.md
    security.md
    release.md
```

La règle de base : **toute la logique métier doit être testable sans Blender**. `bpy` doit être limité à la couche UI, aux opérateurs et à quelques adaptateurs. Si tu fais ça, tu pourras tester 80 % du projet avec `pytest` sans lancer Blender.

---

## Bonnes pratiques de dev pour un addon Blender

Blender attend des extensions/add-ons Python structurés proprement, avec manifeste moderne, et les dépendances externes doivent être embarquées proprement, idéalement via wheels. Pour une extension moderne, il faut partir sur `blender_manifest.toml`, pas sur une logique historique bricolée autour de `bl_info` uniquement. Blender documente aussi que les dépendances Python peuvent être distribuées sous forme de wheels intégrées à l’extension. ([Documentation Blender][2])

Mes règles de dev seraient celles-ci :

- Un opérateur Blender = une action utilisateur claire.
- Pas de logique Git importante directement dans les opérateurs.
- Pas de `subprocess` dispersés partout.
- Une seule couche de services qui encapsule Git/GitHub/LFS.
- Tous les chemins passent par une couche filesystem.
- Tous les messages utilisateurs passent par une couche de reporting uniforme.
- Les erreurs doivent être classées : user error, config error, auth error, repo error, network error, corruption risk.
- Toute opération destructive doit demander confirmation.
- Toute action de restore doit faire une sauvegarde de sécurité.
- Toute feature GitHub doit fonctionner même si GitHub n’est pas configuré : le local-first reste prioritaire.

---

## Choix technique recommandé

### Langage

Python, naturellement. Blender extensions/add-ons se développent en Python via l’API officielle. ([Documentation Blender][6])

### Gestion d’environnement

`uv`

`uv` est aujourd’hui un très bon choix pour ce repo : projet géré via `pyproject.toml`, lockfile `uv.lock`, `uv run`, `uv sync`, `uv lock`, et intégration officielle dans GitHub Actions via `astral-sh/setup-uv`. ([Astral Docs][7])

### Dépendances

Le moins possible. Plus l’extension dépend d’un écosystème externe, plus le packaging Blender devient pénible. Blender supporte les Python wheels pour les extensions auto-contenues, donc si tu as besoin d’une dépendance Python externe, bundle-la proprement plutôt que d’exiger une installation système. ([Documentation Blender][8])

### Git backend

Utiliser **le binaire `git` local** via `subprocess`, pas une réimplémentation maison.

Pourquoi :

- comportement identique aux usages réels ;
- compatibilité avec Git LFS ;
- simplicité de debug ;
- pas de dette énorme autour des edge cases Git.

### GitHub backend

Deux couches :

- une couche locale Git pour les opérations repo ;
- une couche GitHub REST pour les métadonnées utiles : création de repo, PR, infos de branche, liens, releases.

GitHub expose bien des endpoints REST pour les contenus, les branches, les commits et les pull requests. ([GitHub Docs][9])

---

## Authentification

Pour un addon fini, je ferais ça :

- **mode simple** : PAT fine-grained ;
- **mode avancé** : device flow GitHub.

Le PAT est plus simple à implémenter et GitHub recommande, si possible, les fine-grained PAT plutôt que les classic PAT pour l’usage personnel. Le device flow est très adapté aux applications sans navigateur intégré classique, ce que GitHub documente explicitement. ([GitHub Docs][4])

Stockage du secret :

- jamais dans le `.blend`,
- jamais dans un fichier du projet,
- idéalement dans le keychain système quand possible,
- sinon dans les préférences Blender avec chiffrement minimal + avertissement clair.

---

## Structure `pyproject.toml` et usage de uv

Le repo doit être un vrai projet Python géré par `uv`, avec dépendances runtime et dev séparées.

Je te conseille :

- runtime deps : minimum absolu ;
- dev deps : `ruff`, `mypy`, `pytest`, éventuellement `pytest-cov`, `pre-commit` ;
- commandes via `uv run`.

`uv` supporte le workflow projet standard autour de `pyproject.toml`, du lockfile `uv.lock`, de `uv sync`, `uv run` et `uv lock`, et fournit aussi une intégration officielle avec pre-commit. ([Astral Docs][7])

Je définirais ces scripts logiques :

- `uv run ruff check .`
- `uv run ruff format .`
- `uv run mypy gitblend`
- `uv run pytest`
- `uv run python tools/package_extension.py`
- `uv run python tools/dev_install.py`

---

## Linters et qualité

Je te recommande ce stack, sans hésiter.

### Ruff

Pour lint + format.

Ruff est un linter et formatter Python très rapide, et son linter couvre le terrain de Flake8 + beaucoup de plugins populaires, tandis que son formatter peut servir de remplacement pratique à Black. ([Astral Docs][10])

### mypy

Pour le typage statique.

Mypy est un type checker statique Python. Sur un addon Blender, ça aide énormément à contenir la dette sur les services, les modèles et les résultats d’opérations Git/GitHub. ([mypy.readthedocs.io][11])

### pytest

Pour les tests unitaires et d’intégration hors Blender.

Pytest reste le meilleur choix pratique ici, avec découverte standard des tests, fixtures et config simple au niveau du repo. ([docs.pytest.org][12])

### pre-commit

Pour imposer la qualité avant chaque commit.

`pre-commit` gère très bien les hooks multi-langages, et uv fournit en plus une intégration officielle pour garder le lockfile cohérent. ([pre-commit.com][13])

### Ce que je mettrais dans pre-commit

- ruff check
- ruff format --check
- mypy sur le cœur Python
- fin de fichier newline
- trailing whitespace
- validation YAML/TOML
- hook `uv-lock` si tu veux garder `uv.lock` toujours cohérent. ([Astral Docs][14])

---

## Stratégie de tests

Le projet doit avoir 4 niveaux de tests.

### 1. Unit tests

Pour tout le domaine et les services purs.

Exemples :

- parseur de `git status --porcelain`
- mapping des erreurs subprocess
- génération `.gitattributes`
- audit de projet
- logique de commit message
- résolution des chemins

### 2. Integration tests Git

Sans Blender.

Tu crées des repos temporaires avec `pytest` et tu testes :

- init
- commit
- branches
- merge simple
- conflits
- Git LFS si disponible dans l’environnement

### 3. Blender smoke tests

Tests minimaux lançant Blender en mode headless pour vérifier :

- import de l’extension,
- register/unregister,
- chargement des panels et opérateurs principaux,
- absence d’erreurs fatales.

Blender documente la création et la validation d’extensions par ligne de commande, donc ça doit faire partie du pipeline. ([Documentation Blender][15])

### 4. Packaging tests

Le zip final doit être :

- buildable,
- validable,
- installable.

---

## CI GitHub Actions à mettre en place

GitHub Actions est parfaitement adapté à ce repo, et `uv` a une intégration officielle via `astral-sh/setup-uv`, qui peut aussi persister le cache. GitHub rappelle aussi que les runners hébergés repartent d’un environnement propre à chaque job, donc le cache compte pour accélérer les builds. ([Astral Docs][16])

Je mettrais **6 workflows**.

### 1. `ci.yml`

Déclenché sur push + pull_request.

Jobs :

- checkout
- setup Python
- setup uv
- `uv sync`
- ruff check
- ruff format --check
- mypy
- pytest
- upload des rapports si besoin

### 2. `package.yml`

Déclenché sur push tags + manual dispatch.

Jobs :

- build de l’extension zip
- validation via CLI Blender
- upload artifact
- création de release GitHub
- attach du zip final

Blender fournit officiellement les commandes `extension build` et `extension validate`, donc il faut s’en servir dans la CI, pas faire un packaging artisanal opaque. ([Documentation Blender][15])

### 3. `blender-matrix.yml`

Déclenché sur PR importantes.

Matrix :

- Blender 4.2 LTS
- Blender 4.5 LTS ou version supportée choisie
- OS : Ubuntu / Windows / macOS si tu veux être sérieux

Le but est de détecter les écarts de comportement UI/path/process.

### 4. `security.yml`

- dependency review sur PR
- CodeQL en setup par défaut ou avancé selon ton envie

GitHub documente le **dependency review action** pour bloquer l’introduction de dépendances vulnérables dans les PR, et **CodeQL** pour le code scanning. ([GitHub Docs][17])

### 5. `dependabot.yml`

Je l’activerais pour :

- GitHub Actions
- écosystème Python

GitHub documente à la fois le support des écosystèmes et la mise à jour automatique des GitHub Actions via Dependabot. ([GitHub Docs][18])

### 6. `docs.yml`

- build de la doc
- vérification des liens
- éventuellement publication GitHub Pages

---

## Pipeline CI conseillé en clair

Ton pipeline idéal doit ressembler à ça :

1. PR ouverte
2. lint + format check
3. mypy
4. unit/integration tests
5. dependency review
6. build extension zip
7. validate extension zip
8. smoke test Blender
9. merge autorisé seulement si tout est vert

Et sur tag :

1. build
2. validate
3. changelog
4. GitHub release
5. artifact zip signé si tu veux pousser le sérieux

---

## Packaging Blender moderne

Comme c’est un addon moderne, il doit être packagé comme une **extension Blender** avec `blender_manifest.toml`. Blender documente explicitement ce manifeste, le build/validate CLI et le support des wheels Python embarquées. ([Documentation Blender][2])

Donc :

- manifeste propre ;
- versioning sémantique ;
- metadata complètes ;
- dépendances externes packagées proprement ;
- zip final installable sans étape manuelle tordue.

---

## Bonnes pratiques Git/GitHub spécifiques au projet

Je ferais ces choix par défaut :

- branche par défaut : `main`
- protection de branche activée
- PR requises pour les changements non triviaux
- labels : `bug`, `enhancement`, `good first issue`, `help wanted`, `blender-ui`, `git-core`, `github-api`, `lfs`, `docs`
- Conventional Commits si tu veux des changelogs auto
- CODEOWNERS si le projet prend de l’ampleur

GitHub documente les règles de protection de branches pour exiger des checks avant push/merge. ([GitHub Docs][19])

---

## Open source : licence et gouvernance

Je te conseille :

- **Licence** : GPL-3.0-or-later
- **Pourquoi** : cohérent avec l’écosystème Blender et simple pour un addon Blender open source.

Si tu veux viser proprement l’écosystème d’extensions Blender, garde en tête que la doc Blender pour les extensions demande GPL v3 ou ultérieure pour les add-ons sur la plateforme officielle. ([Documentation Blender][20])

Je mettrais aussi :

- `README.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- templates d’issues et PR
- `CHANGELOG.md`

---

## README idéal

Le README doit vendre le projet en 20 secondes.

Structure :

- tagline
- screenshot / gif
- pourquoi ça existe
- features
- installation
- quick start
- Git LFS note
- supported platforms
- limitations assumées
- development with uv
- contributing
- roadmap

---

## Limites assumées à documenter noir sur blanc

Ça renforcera la confiance.

- Les `.blend` restent des binaires.
- Les conflits complexes ne peuvent pas être fusionnés intelligemment.
- Git LFS est fortement recommandé pour les gros assets.
- Certaines features GitHub nécessitent Internet et une authentification.
- Certaines intégrations peuvent dépendre de la présence de `git` et `git-lfs` sur la machine.

GitHub documente bien que Git LFS est un outil séparé à installer, et que le mécanisme repose sur des pointeurs au lieu du contenu direct dans Git. ([GitHub Docs][21])

---

## Définition d’un “addon complet fini” pour ce projet

Pour moi, `gitblend` mérite le statut “complet” quand il coche tout ça :

- installation zip sans friction ;
- support Blender moderne ;
- local Git workflow complet ;
- GitHub auth simple et fiable ;
- Git LFS guidé et intégré ;
- audit de portabilité de projet ;
- UI propre ;
- docs solides ;
- CI sérieuse ;
- tests utiles ;
- releases versionnées ;
- sécurité minimale correcte ;
- limitations bien documentées.

Là, tu n’as pas juste un addon. Tu as un vrai projet open source crédible.

---

## Recommandation finale, très claire

Oui, tu peux le faire.

Et même, je pense que tu peux faire un très bon addon open source si tu respectes trois règles :

1. **local-first** : Git local avant GitHub ;
2. **binary-aware** : assumer les contraintes `.blend` + LFS ;
3. **testable core** : sortir la logique métier de `bpy`.

Le meilleur nom de repo pour partir simple et propre : **`gitblend`**.

La meilleure baseline :
**“Git and GitHub workflows for Blender projects.”**

La meilleure stack :
**Python + Blender API + subprocess Git + GitHub REST + uv + Ruff + mypy + pytest + pre-commit + GitHub Actions.**

La meilleure ambition v1.0 :
**faire de Blender un bon client Git pour des projets artistiques, sans mentir sur les limites du binaire.**

Je peux maintenant te générer le squelette complet du repo, avec `pyproject.toml`, `blender_manifest.toml`, arborescence, fichiers CI GitHub Actions et conventions de code.

[1]: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github?utm_source=chatgpt.com "About large files on GitHub"
[2]: https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html?utm_source=chatgpt.com "How to Create Extensions - Blender 5.1 Manual"
[3]: https://docs.blender.org/manual/en/latest/editors/preferences/extensions.html?utm_source=chatgpt.com "Get Extensions - Blender 5.1 Manual"
[4]: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github?utm_source=chatgpt.com "About authentication to GitHub"
[5]: https://docs.github.com/en/repositories/working-with-files/managing-large-files/configuring-git-large-file-storage?utm_source=chatgpt.com "Configuring Git Large File Storage"
[6]: https://docs.blender.org/manual/en/latest/advanced/scripting/addon_tutorial.html?utm_source=chatgpt.com "Add-on Tutorial - Blender 5.1 Manual"
[7]: https://docs.astral.sh/uv/guides/projects/?utm_source=chatgpt.com "Working on projects | uv - Astral Docs"
[8]: https://docs.blender.org/manual/en/latest/advanced/extensions/python_wheels.html?utm_source=chatgpt.com "Python Wheels - Blender 5.1 Manual"
[9]: https://docs.github.com/rest/repos/contents?utm_source=chatgpt.com "REST API endpoints for repository contents"
[10]: https://docs.astral.sh/ruff/?utm_source=chatgpt.com "Ruff - Astral Docs"
[11]: https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"
[12]: https://docs.pytest.org/?utm_source=chatgpt.com "pytest documentation"
[13]: https://pre-commit.com/?utm_source=chatgpt.com "pre-commit"
[14]: https://docs.astral.sh/uv/guides/integration/pre-commit/?utm_source=chatgpt.com "Using uv with pre-commit - Astral Docs"
[15]: https://docs.blender.org/manual/en/latest/advanced/command_line/extension_arguments.html?utm_source=chatgpt.com "Extensions Command Line Arguments - Blender 5.1 Manual"
[16]: https://docs.astral.sh/uv/guides/integration/github/?utm_source=chatgpt.com "Using uv in GitHub Actions - Astral Docs"
[17]: https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/configuring-the-dependency-review-action?utm_source=chatgpt.com "Configuring the dependency review action"
[18]: https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories?utm_source=chatgpt.com "Dependabot supported ecosystems and repositories"
[19]: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches?utm_source=chatgpt.com "About protected branches"
[20]: https://docs.blender.org/manual/ja/5.1/editors/preferences/extensions.html?utm_source=chatgpt.com "Get Extensions - Blender 5.1 Manual"
[21]: https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage?utm_source=chatgpt.com "Installing Git Large File Storage"
