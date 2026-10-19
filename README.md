# ExcellentCrates Legacy Converter

Convertisseur local pour migrer les fichiers YAML de l'ancien plugin ExcellentCrates vers la structure d'objets de la nouvelle version.

Ce projet est indépendant et n'est pas affilié aux développeurs d'ExcellentCrates.

## Utilisation

Prérequis : Python 3.10 ou plus récent.

```powershell
py -m pip install -r requirements.txt
py src\converter.py "C:\chemin\ExcellentCrates-old.zip"
```

Le programme crée `excellentcrates [converted]` dans le dossier courant. Un second argument permet de choisir la destination. Celle-ci doit être vide pour éviter tout écrasement. Sous Windows, `convert.bat` peut aussi être lancé avec les mêmes arguments.

Pour associer un ancien monde à un identifiant précis :

```powershell
py src\converter.py "C:\chemin\ExcellentCrates-old.zip" "excellentcrates [converted]" --world-map survie5=minecraft:monde1
```

Le format de sortie comprend `objects/key/`, `objects/reward/<crate_id>/` et `objects/crate/`, ainsi qu'un manifeste et un rapport de conversion. L'ordre conseillé dans le manifeste est clés, récompenses, puis caisses.

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

Les bases `data.db`, menus personnalisés, langues, configurations globales, logs, coûts en monnaie et certaines permissions avancées ne sont pas migrés. Les structures de jalons et les données NBT d'objets peuvent varier selon la version d'ExcellentCrates, Minecraft ou les extensions installées. Vérifiez les fichiers générés sur un serveur de test avant utilisation.

## Contributions

Les rapports de bugs et pull requests sont les bienvenus. Consultez [CONTRIBUTING.md](CONTRIBUTING.md) et anonymisez toute configuration avant de la partager.

## Licence

Distribué sous licence [MIT](LICENSE).
