"""
/***************************************************************************
Name            : menu_from_project plugin
Description          : Build layers shortcut menu based on QGIS project
Date                 :  10/11/2011
copyright            : (C) 2011 by Agence de l'Eau Adour Garonne
email                : xavier.culos@eau-adour-garonne.fr
***************************************************************************/

/***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************/

"""

# Standard library
import os
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from qgis.core import QgsApplication, QgsMessageLog, QgsSettings, QgsTask
from qgis.PyQt.QtCore import QCoreApplication, QFileInfo, QLocale, Qt, QTranslator, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QFont, QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu

# project
from menu_from_project.__about__ import (
    DIR_PLUGIN_ROOT,
    __icon_path__,
    __title__,
    __uri_homepage__,
)

# PyQGIS
from menu_from_project.datamodel.project import Project
from menu_from_project.datamodel.project_config import (
    MenuGroupConfig,
    MenuLayerConfig,
    MenuProjectConfig,
)
from menu_from_project.logic.cache_manager import CacheManager
from menu_from_project.logic.layer_load import LayerLoad
from menu_from_project.logic.project_read import get_project_menu_config
from menu_from_project.logic.qgs_manager import (
    QgsDomManager,
    read_from_file,
    read_from_http,
)
from menu_from_project.logic.tools import icon_per_layer_type
from menu_from_project.toolbelt.preferences import PlgOptionsManager
from menu_from_project.ui.dlg_settings import MenuConfDialog
from menu_from_project.ui.menu_layer_data_item_provider import MenuLayerProvider
from menu_from_project.ui.wdg_settings import PlgOptionsFactory

# ############################################################################
# ########## Classes ###############
# ##################################


class MenuFromProject:

    def on_initializationCompleted(self):
        # build menu
        self.initMenus()

    def __init__(self, iface):
        self.task = None
        self.path = QFileInfo(os.path.realpath(__file__)).path()

        # initialize the locale
        self.locale: str = QgsSettings().value("locale/userLocale", QLocale().name())[
            0:2
        ]
        locale_path: Path = DIR_PLUGIN_ROOT.joinpath(
            f"resources/i18n/layers_menu_from_project_{self.locale}.qm"
        )
        if locale_path.exists():
            self.translator = QTranslator()
            self.translator.load(str(locale_path.resolve()))
            QCoreApplication.installTranslator(self.translator)

        self.iface = iface
        self.toolBar = None

        self.options_factory = None
        self.settings_dialog = None

        self.qgs_dom_manager = QgsDomManager()
        self.menubarActions = []
        self.layerMenubarActions = []
        self.canvas = self.iface.mapCanvas()

        self.mapLayerIds = {}

        self.plg_settings = PlgOptionsManager()

        self.action_project_configuration = None
        self.action_menu_help = None

        self.registry = QgsApplication.instance().dataItemProviderRegistry()
        self.provider = None

    @staticmethod
    def tr(message):
        return QCoreApplication.translate("MenuFromProject", message)

    # TODO: until a log manager is implemented
    @staticmethod
    def log(message, application=__title__, indent=0):
        indent_chars = " .. " * indent
        QgsMessageLog.logMessage(
            f"{indent_chars}{message}", application, notifyUser=True
        )

    def initMenus(self):
        menuBar = self.iface.editMenu().parentWidget()
        for action in self.menubarActions:
            menuBar.removeAction(action)
            del action

        self.menubarActions = []

        menuBar = self.iface.addLayerMenu()
        for action in self.layerMenubarActions:
            menuBar.removeAction(action)
            del action

        self.layerMenubarActions = []

        self.task = QgsTask.fromFunction(
            self.tr("Load projects menu configuration"),
            self.load_all_project_config,
            on_finished=self.project_config_loaded,
        )

        QgsApplication.taskManager().addTask(self.task)

    def load_all_project_config(
        self, task: QgsTask
    ) -> List[Tuple[Any, MenuProjectConfig]]:
        """Load all project config in a task

        :param task: task where the function is run
        :type task: QgsTask
        :return: list of tuple of project dict and project menu config
        :rtype: List[Tuple[Any, MenuProjectConfig]]
        """
        result = []
        settings = self.plg_settings.get_plg_settings()
        nb_projects = len(settings.projects)
        for i, project in enumerate(settings.projects):
            if not project.valid:
                continue
            task.setProgress(i * 100.0 / nb_projects)
            cache_manager = CacheManager(self.iface)
            # Try to get project configuration from cache
            project_config = cache_manager.get_project_menu_config(project)
            if not project_config:
                # Create project menu configuration from QgsProject
                project_config = get_project_menu_config(project, self.qgs_dom_manager)
                if project_config:
                    # Save in cache
                    cache_manager.save_project_menu_config(project, project_config)
            if project_config:
                result.append((project, project_config))
            else:
                self.log(
                    self.tr(
                        f"Can't define project configuration for project {project.name}"
                    )
                )
        return result

    def project_config_loaded(
        self, exception: Any, project_configs: List[Tuple[Project, MenuProjectConfig]]
    ) -> None:
        """Add menu after project configuration load

        :param exception: possible exception raised during load
        :type exception: Any
        :param project_configs: list of tuple of project dict and project menu config
        :type project_configs: List[Tuple[Any, MenuProjectConfig]]
        """
        QgsApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        if self.provider:
            self.registry.removeProvider(self.provider)
        self.provider = MenuLayerProvider(project_configs)

        previous = None, None
        for project, project_config in project_configs:
            if project.enable:
                # Add to QGIS instance
                previous = self.add_project_config(project, project_config, previous)

        self.registry.addProvider(self.provider)
        QgsApplication.restoreOverrideCursor()

    def add_project_config(
        self,
        project: Project,
        project_config: MenuProjectConfig,
        previous: Tuple[Optional[QMenu], Optional[QMenu]],
    ) -> Tuple[Optional[QMenu], Optional[QMenu]]:
        """Add a project menu configuration to current QGIS instance

        :param menu_name: Name of the menu to create
        :type menu_name: str
        :param project: dict of information about the project
        :type project: Project
        :param project_config: project menu configuration
        :type project_config: MenuProjectConfig
        :param previous: previous created menus
        :type previous: Tuple[Optional[QMenu], Optional[QMenu]]
        :return: created menus
        :rtype: Tuple[Optional[QMenu], Optional[QMenu]]
        """
        project_menu = self.create_project_menu(
            menu_name=project_config.project_name, project=project, previous=previous
        )
        if project_menu[0]:
            self.add_group_childs(project_config.root_group, project_menu[0])
        if project_menu[1]:
            self.add_group_childs(project_config.root_group, project_menu[1])

        return project_menu

    def create_project_menu(
        self,
        menu_name: str,
        project: Project,
        previous: Tuple[Optional[QMenu], Optional[QMenu]],
    ) -> Tuple[Optional[QMenu], Optional[QMenu]]:
        """Create project menus for project locations and add it to QGIS instance

        :param menu_name: Name of the menu to create
        :type menu_name: str
        :param project: dict of information about the project
        :type project: Project
        :param previous: previous created menus
        :type previous: Tuple[Optional[QMenu], Optional[QMenu]]
        :return: created menus
        :rtype: Tuple[Optional[QMenu], Optional[QMenu]]
        """
        location = project.location

        # For merge, only add separator on previous menu
        if location == "merge" and previous:
            if previous[0]:
                previous[0].addSeparator()
            if previous[1]:
                previous[1].addSeparator()
            return previous

        project_menu_layer = None
        if location.count("layer") != 0:
            menu_bar = self.iface.addLayerMenu()
            project_menu_layer = QMenu("&" + menu_name, menu_bar)
            project_menu_layer.setToolTipsVisible(
                self.plg_settings.get_plg_settings().optionTooltip
            )
            project_action = menu_bar.addMenu(project_menu_layer)
            self.layerMenubarActions.append(project_action)

        project_menu_new = None
        if location.count("new") != 0:
            menu_bar = self.iface.editMenu().parentWidget()
            project_menu_new = QMenu("&" + menu_name, menu_bar)
            project_menu_new.setToolTipsVisible(
                self.plg_settings.get_plg_settings().optionTooltip
            )
            project_action = menu_bar.addMenu(project_menu_new)
            self.menubarActions.append(project_action)

        return project_menu_layer, project_menu_new

    def add_group_childs(
        self, group: MenuGroupConfig, grp_menu: QMenu
    ) -> List[MenuLayerConfig]:
        """Add all childs of a group config

        :param uri: initial uri of project (can be from local file / http / postgres)
        :type uri: str
        :param group: group menu configuration
        :type group: MenuGroupConfig
        :param grp_menu: menu for group
        :type grp_menu: QMenu
        :return: list of inserted layer configuration
        :rtype: List[MenuLayerConfig]
        """
        layer_inserted = []
        layer_name_inserted = []
        for child in group.childs:
            if isinstance(child, MenuGroupConfig):
                self.add_group(child, grp_menu)
            elif isinstance(child, MenuLayerConfig):
                # Check if this layer name was already inserted
                if child.name not in layer_name_inserted:
                    layer_name_list = group.get_layer_configs_from_name(child.name)
                    if len(layer_name_list) > 1:
                        # Multiple version of format available, must use a layer dict to create menu
                        layer_dict = MenuGroupConfig.sort_layer_list_by_version(
                            layer_name_list
                        )
                        layer_inserted.append(
                            self.add_layer_dict(
                                child.name, layer_dict, grp_menu, group.name
                            )
                        )
                    else:
                        # Only one version or format
                        self.add_layer(child, grp_menu, group.name, child.name)
                        layer_inserted.append(child)

                    # Indicate that this layer name was added
                    layer_name_inserted.append(child.name)
        return layer_inserted

    def add_group(self, group: MenuGroupConfig, menu: QMenu) -> None:
        """Add group menu configuration to a menu

        :param uri: initial uri of project (can be from local file / http / postgres)
        :type uri: str
        :param group: group menu configuration
        :type group: MenuGroupConfig
        :param menu: input menu
        :type menu: QMenu
        """

        name = group.name

        settings = self.plg_settings.get_plg_settings()

        # Special cases for separator and title
        # "-" => insert a separator
        if name == "-":
            menu.addSeparator()
        # "-*" => insert a title
        elif name.startswith("-"):
            action = QAction(name[1:], self.iface.mainWindow())
            font = QFont()
            font.setBold(True)
            action.setFont(font)
            menu.addAction(action)
        # regular group
        else:
            grp_menu = menu.addMenu("&" + name)
            grp_menu.setToolTipsVisible(settings.optionTooltip)

            layer_inserted = self.add_group_childs(group=group, grp_menu=grp_menu)

            if len(layer_inserted) and settings.optionLoadAll:
                action = QAction(self.tr("Load all"), self.iface.mainWindow())
                font = QFont()
                font.setBold(True)
                action.setFont(font)
                grp_menu.addAction(action)
                action.triggered.connect(
                    lambda checked: LayerLoad().load_layer_list(layer_inserted, name)
                )

    def add_layer_dict(
        self,
        layer_name: str,
        layer_dict: Dict[str, List[MenuLayerConfig]],
        menu: QMenu,
        group_name: str,
    ) -> MenuLayerConfig:
        """Add a layer dict containing all versions and format of a layer

        If several format are availables for a version, a specific menu is created for the version

        Displayed text is adapted depending on the available versions and format.

        :param layer_name: layer name
        :type layer_name: str
        :param layer_dict: layer dict containing all versions and format for layer name
        :type layer_dict: Dict[str, List[MenuLayerConfig]]
        :param menu: menu where the action and submenu must be added
        :type menu: QMenu
        :param group_name: name of the group
        :type group_name: str
        :return: first available layer config for this layer name
        :rtype: MenuLayerConfig
        """
        settings = self.plg_settings.get_plg_settings()
        layer_menu = menu.addMenu(layer_name)
        layer_menu.setToolTipsVisible(settings.optionTooltip)

        first_layer = list(layer_dict.values())[0][0]
        self.add_layer(first_layer, layer_menu, group_name, self.tr("Display layer"))
        all_version_menu = layer_menu.addMenu(self.tr("Versions"))
        all_version_menu.setToolTipsVisible(settings.optionTooltip)

        # Create action or menu for each version
        for version, format_list in layer_dict.items():

            version_label = version if version else self.tr("Latest")
            version_menu = all_version_menu.addMenu(version_label)

            # Create action for each format
            for layer in format_list:
                self.add_layer(layer, version_menu, group_name, layer.format)

        return first_layer

    def add_layer(
        self, layer: MenuLayerConfig, menu: QMenu, group_name: str, action_text: str
    ) -> None:
        """Add layer menu configuration to a menu

        :param uri: initial uri of project (can be from local file / http / postgres)
        :type uri: str
        :param layer: layer menu configuration
        :type layer: MenuLayerConfig
        :param group_name: group name in case of create group option
        :type group_name: str
        :param menu: input menu
        :type menu: QMenu
        """
        settings = self.plg_settings.get_plg_settings()
        action = QAction(action_text, self.iface.mainWindow())

        # add menu item
        action.triggered.connect(
            lambda checked: LayerLoad().load_layer(layer, group_name)
        )
        action.setIcon(
            icon_per_layer_type(layer.is_spatial, layer.layer_type, layer.geometry_type)
        )
        if settings.optionTooltip:
            action.setToolTip(settings.tooltip_for_layer(layer))

        menu.addAction(action)

    def initGui(self):
        settings = self.plg_settings.get_plg_settings()
        if settings.is_setup_visible:
            # settings page within the QGIS preferences menu
            if not self.options_factory:
                self.options_factory = PlgOptionsFactory()
                self.options_factory.settingsApplied.connect(self._apply_settings)
                self.iface.registerOptionsWidgetFactory(self.options_factory)
                # Add search path for plugin
                help_search_paths = QgsSettings().value("help/helpSearchPath")
                if (
                    isinstance(help_search_paths, list)
                    and __uri_homepage__ not in help_search_paths
                ):
                    help_search_paths.append(__uri_homepage__)
                else:
                    help_search_paths = [help_search_paths, __uri_homepage__]
                QgsSettings().setValue("help/helpSearchPath", help_search_paths)

            # menu item - Main
            self.action_project_configuration = QAction(
                QIcon(f"{__icon_path__.resolve()}"),
                self.tr("Projects configuration"),
                self.iface.mainWindow(),
            )

            self.iface.addPluginToMenu(
                "&" + __title__, self.action_project_configuration
            )
            # Add actions to the toolbar
            self.action_project_configuration.triggered.connect(
                self.open_projects_config
            )

            # menu item - Documentation
            self.action_menu_help = QAction(
                QIcon(QgsApplication.iconPath("mActionHelpContents.svg")),
                self.tr("Help"),
                self.iface.mainWindow(),
            )

            self.iface.addPluginToMenu("&" + __title__, self.action_menu_help)
            self.action_menu_help.triggered.connect(
                partial(QDesktopServices.openUrl, QUrl(__uri_homepage__))
            )

        self.iface.initializationCompleted.connect(self._apply_settings)

    def _apply_settings(self) -> None:
        """Apply current settings"""
        # clear web projects cache
        try:
            self.qgs_dom_manager.cache_clear()
            read_from_http.cache_clear()
            read_from_file.cache_clear()
        except Exception:
            pass
        # Rebuild menus and browser
        self.initMenus()

    def unload(self):
        menuBar = self.iface.editMenu().parentWidget()
        for action in self.menubarActions:
            menuBar.removeAction(action)
            del action

        menuBar = self.iface.addLayerMenu()
        for action in self.layerMenubarActions:
            menuBar.removeAction(action)
            del action

        self.menubarActions = []
        self.layerMenubarActions = []

        settings = self.plg_settings.get_plg_settings()
        if settings.is_setup_visible:
            # -- Clean up preferences panel in QGIS settings
            if self.options_factory:
                self.iface.unregisterOptionsWidgetFactory(self.options_factory)
                # pop from help path
                help_search_paths = QgsSettings().value("help/helpSearchPath")
                if (
                    isinstance(help_search_paths, list)
                    and __uri_homepage__ in help_search_paths
                ):
                    help_search_paths.remove(__uri_homepage__)
                QgsSettings().setValue("help/helpSearchPath", help_search_paths)

            self.iface.removePluginMenu(
                "&" + __title__, self.action_project_configuration
            )
            self.iface.removePluginMenu("&" + __title__, self.action_menu_help)
            self.action_project_configuration.triggered.disconnect(
                self.open_projects_config
            )
            self.iface.removePluginMenu(__title__, self.action_menu_help)

        self.iface.initializationCompleted.disconnect(self._apply_settings)

        if self.provider:
            self.registry.removeProvider(self.provider)

        if self.settings_dialog:
            self.settings_dialog.deleteLater()

    def open_projects_config(self):
        if not self.settings_dialog:
            self.settings_dialog = MenuConfDialog(self.iface.mainWindow())
            self.settings_dialog.wdg_config.settingsApplied.connect(
                self._apply_settings
            )
            self.settings_dialog.setModal(False)

        self.settings_dialog.show()
