# Using this plugin with QGIS Deployment Toolbelt (QDT)

If you want to use this plugin with Q[GIS Deployment Toolbelt (QDT)](https://qgis-deployment.github.io/qgis-deployment-toolbelt-cli/), you can add the following snippet to your `profile.json` file, under the `plugins` attribute:

```json
    {
      "name": "Layers menu from project",
      "folder_name": "menu_from_project",
      "official_repository": true,
      "plugin_id": 43,
      "version": "2.2.1"
    }
```

Remember to replace the `version` attribute with the version you want to install.
