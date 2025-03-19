# Déployer ce plugin avec QGIS Deployment Toolbelt (QDT)

Si vous souhaitez déployer ce plugin avec [QGIS Deployment Toolbelt (QDT)](https://qgis-deployment.github.io/qgis-deployment-toolbelt-cli/), vous pouvez ajouter l'extrait de configuration suivant dans le fichier `profile.json` à la suite des autres plugins à déployer :

```json
    {
      "name": "Layers menu from project",
      "folder_name": "menu_from_project",
      "official_repository": true,
      "plugin_id": 43,
      "version": "2.4.1"
    }
```

N'oubliez pas de replacer la valeur de l'attribut `version` avec le numéro de la version que vous souhaitez déployer.
