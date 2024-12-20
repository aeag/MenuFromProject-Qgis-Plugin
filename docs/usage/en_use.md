# How to use the plugin Layers menu from project

That plugin provides a convenient way to add prestyled and preconfigured frequently used layers using dropdown menus built by simply reading existing QGIS projects (qgs, qgz, postgres, http)

Styling, actions, labeling, metadata, joined layers and relations are reused as defined in source projects.

![dropdown menu en](../static/drop_down_menu_en.png)

When the plugin is configured (choice of a project via the plugin menu), a new menu appears, based on all the layers that contain the original project.

## 1. Set up a classical QGIS project somewhere

Save a project somewhere with some styling, labeling, and so on.

The project might be stored in a PostgreSQL database, or on a web server, which makes it accessible via http. [(see feature-saving-and-loading-projects-in-postgresql-database)](https://qgis.org/en/site/forusers/visualchangelog32/index.html#feature-saving-and-loading-projects-in-postgresql-database). You need to copy/paste the project URI (Project properties -> General) into the field.

...and QGZ [(see feature-new-zipped-project-file-format-qgz)](https://qgis.org/en/site/forusers/visualchangelog30/index.html#feature-new-zipped-project-file-format-qgz).

If you want some hierarchical menu, just use groups and sub groups in layer's panel, they will be reused to build the same hierarchical menu.

```{tip}
Create an empty group named "-" to build a separator line in dropdown menu
```

```{note}
If you want users to access that project, save it to a shared network place, better read only fo users except for the project administrator. Using a version control system could be a very good idea here.
```

![Mapping configuration <--> created menu](../static/mapping.png)

----

## 2. Configure the plugin to read those projects

1. Go to menu / Plugins / Layer menu from project :

    ![Open plugin configuration window](../static/config_window_access_en.png)

1. The plugin's configuration dialog appears:

    ![configuration window](../static/config_window_en.png)

1. Press `+` button to add a .qgs, .qgz project to the list (or paste a PostgreSQL URI, a HTTP URL).
1. You can change the alias that will be the menu name in QGIS

The name will become the title of the menu.

The menu can be placed either in the main menu bar, or in the "layer / add layer" sub-menu, or in QGIS browser (since version 2.3.0). Since version 1.1 it can also be merged with the previous project in the same menu/browser.

For QGIS browser, layers and group can only be displayed alphabetically. Order from project won't be kept and in case of merge, the layers and group will be mixed.

### Options

#### Show title and abstract in tooltip

This is a convenient way to show some metadata to end users before they add it o the working session even if they don't know that metadata are available in layer properties

#### Load all layers item

Adds an entry at the end of every menu's node that allow user to load all menu items at once. Very useful when you want to load all topo maps for every zoom level for instance.

![Option - Add all](../static/add_all_option_en.png)

#### Create Group

Layer will be added inside a group, taking the name of the menu node.

![Option - Create group](../static/add_group_option_en.png)

#### Also load linked layers

If relations or joins are defined, the opening of a layer will be accompanied by the opening of the associated child layers.

#### Hide configuration dialog

You can hide the administration dialog of the plugin by adding a `menu_from_project/is_setup_visible` to `false` in the QGIS INI file. This is useful when you deploy QGIS within an organization:

```ini
[...]
menu_from_project/is_setup_visible=false
[...]
```
