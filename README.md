# ExcellentCrates Legacy Converter

Application Windows pour convertir les anciennes configurations YAML du plugin ExcellentCrates vers le format d'objets de la v7.

Ce projet est indépendant et n'est pas affilié aux développeurs d'ExcellentCrates.

## Utiliser l'application Windows

Téléchargez `ExcellentCrates-Converter.exe` depuis la section [Releases](https://github.com/FurrO2/excellentcrates-converter/releases) et ouvrez-le. Python n'est pas nécessaire.

1. À gauche, choisissez l'archive ZIP complète de l'ancien plugin ou son dossier racine contenant `crates/` et `keys/`.
2. À droite, choisissez l'emplacement du dossier converti.
3. Cliquez sur **Convertir vers v7**.
4. Copiez le contenu de `objects/` dans le dossier `objects/` de votre installation ExcellentCrates v7, généralement `plugins/ExcellentCrates/objects/`. Gardez la structure des sous-dossiers.
5. Consultez `conversion-report.json`, redémarrez le serveur et vérifiez les caisses en jeu.

Faites une sauvegarde des fichiers v7 avant de les remplacer. Le dossier de destination doit être vide; l'application ne remplace pas les données existantes.

## Lancer depuis les sources

Prérequis : Python 3.10 ou plus récent.

```powershell
py -m pip install -r requirements.txt
py src\gui.py
```

Pour l'utilisation en ligne de commande :

```powershell
py src\converter.py "C:\chemin\ExcellentCrates-old.zip"
```

Pour associer un ancien monde à un identifiant précis :

```powershell
py src\converter.py "C:\chemin\ExcellentCrates-old.zip" "excellentcrates [converted]" --world-map survie5=minecraft:monde1
```

Le binaire Windows est construit automatiquement par GitHub Actions. Un tag `v*` publie l'exécutable dans une nouvelle release.

## Données prises en charge

- Caisses, clés, récompenses ITEM et COMMAND, aperçus, poids, effets et cooldowns disponibles dans les fichiers de l'archive.
- Récompenses ITEM : l'aperçu reprend le premier objet de `ItemsData` dans son ordre d'origine.
- Blocs assignés : mondes au format `minecraft:<nom>` et coordonnées conservées.
- Modèles d'hologramme référencés dans l'ancien `config.yml`, copiés dans les caisses avec le décalage vertical augmenté de 0,7.
- Limites globales et individuelles des récompenses avec leurs quantités.
- Jalons référencés par les caisses.
- Animations : les profils hérités sont remplacés par `csgo_animation:default` pour les anciens profils csgo, sinon `simple_roll:default`.

Le fichier `conversion-report.json` répertorie les adaptations ou vérifications manuelles nécessaires.

## Limites

Les bases `data.db`, menus personnalisés, langues, configurations globales, logs, coûts en monnaie et certaines permissions avancées ne sont pas migrés. Les structures de jalons et les données NBT d'objets peuvent varier selon la version d'ExcellentCrates, Minecraft ou les extensions installées. Vérifiez les fichiers générés en jeu avant utilisation.

## Contributions

Les rapports de bugs et pull requests sont les bienvenus. Consultez [CONTRIBUTING.md](CONTRIBUTING.md) et anonymisez toute configuration avant de la partager.

## Licence

Distribué sous licence [MIT](LICENSE).
