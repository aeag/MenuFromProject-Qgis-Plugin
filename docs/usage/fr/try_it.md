# Essayer le plugin

Voici quelques exemples faciles à utiliser qui servent de référence pour recetter le plugin lors de son développement.

## Exemple de projet distant basique

Prenons l'un des projets QGIS stockés sur le GitHub public du plugin :

```txt
https://github.com/aeag/MenuFromProject-Qgis-Plugin/raw/refs/heads/master/tests/projects/aeag-tiny.qgz
```

Ouvrir l'interface de configuration des projets :

![Ouvrir l'interface de configuration du plugin](../../static/config_window_access_fr.png)

Renseigner les champs comme dans la capture ci-dessous puis cliquer sur `Appliquer` ou `OK`:

![Configuration - Projet distant](../../static/demo_sample_basic_setup.png)

Vérifier le résultat :

- [x] le projet apparaît comme un nouveau menu dans la barre de QGIS :

    ![Nouveau menu dans la barre des menus de QGIS](../../static/demo_sample_basic_result_menu_bar.png)

- [x] un élément dans l'explorateur de QGIS, nommé`LMFP` :

    ![Résultat dans l'explorateur de QGIS](../../static/demo_sample_basic_result_browser.png)

- [x] comme nouvel élément dans le menu `Couche` > `Ajouter une couche`

    ![Résultat dans le menu ajouter une couche](../../static/demo_sample_basic_result_menu_layer_add.png)
