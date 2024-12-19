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
from typing import Any, List, Optional, Tuple

from qgis.core import QgsApplication, QgsMessageLog, QgsSettings, QgsTask
from qgis.PyQt.QtCore import QCoreApplication, QFileInfo, QLocale, Qt, QTranslator, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QFont, QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu

# project
from menu_from_project.__about__ import DIR_PLUGIN_ROOT, __title__, __uri_homepage__

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
from menu_from_project.toolbelt.preferences import (
    SOURCE_MD_LAYER,
    SOURCE_MD_NOTE,
    SOURCE_MD_OGC,
    PlgOptionsManager,
)
from menu_from_project.ui.menu_conf_dlg import MenuConfDialog  # noqa: F4 I001

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

        self.qgs_dom_manager = QgsDomManager()
        self.menubarActions = []
        self.layerMenubarActions = []
        self.canvas = self.iface.mapCanvas()

        self.mapLayerIds = {}

        self.plg_settings = PlgOptionsManager()

        self.action_project_configuration = None
        self.action_menu_help = None

    @staticmethod
    def tr(message):
        return QCoreApplication.translate("MenuFromProject", message)

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
        self, exception: Any, project_configs: List[Tuple[Any, MenuProjectConfig]]
    ) -> None:
        """Add menu after project configuration load

        :param exception: possible exception raised during load
        :type exception: Any
        :param project_configs: list of tuple of project dict and project menu config
        :type project_configs: List[Tuple[Any, MenuProjectConfig]]
        """
        QgsApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        previous = None
        for project, project_config in project_configs:
            # Add to QGIS instance
            previous = self.add_project_config(project, project_config, previous)

        QgsApplication.restoreOverrideCursor()

    def add_project_config(
        self,
        project: Project,
        project_config: MenuProjectConfig,
        previous: Optional[QMenu],
    ) -> QMenu:
        """Add a project menu configuration to current QGIS instance

        :param menu_name: Name of the menu to create
        :type menu_name: str
        :param project: dict of information about the project
        :type project: Project
        :param project_config: project menu configuration
        :type project_config: MenuProjectConfig
        :param previous: previous created menu
        :type previous: Optional[QMenu]
        :return: created menu
        :rtype: QMenu
        """
        project_menu = self.create_project_menu(
            menu_name=project_config.project_name, project=project, previous=previous
        )
        self.add_group_childs(project_config.root_group, project_menu)

        return project_menu

    def create_project_menu(
        self, menu_name: str, project: Project, previous: Optional[QMenu]
    ) -> QMenu:
        """Create project menu and add it to QGIS instance

        :param menu_name: Name of the menu to create
        :type menu_name: str
        :param project: dict of information about the project
        :type project: Project
        :param previous: previous created menu
        :type previous: Optional[QMenu]
        :return: created menu
        :rtype: QMenu
        """
        location = project.location
        if location == "merge" and previous:
            project_menu = previous
            project_menu.addSeparator()
        else:
            if location == "layer":
                menu_bar = self.iface.addLayerMenu()
            if location == "new":
                menu_bar = self.iface.editMenu().parentWidget()

            project_menu = QMenu("&" + menu_name, menu_bar)
            project_menu.setToolTipsVisible(
                self.plg_settings.get_plg_settings().optionTooltip
            )
            project_action = menu_bar.addMenu(project_menu)

            if location == "layer":
                self.layerMenubarActions.append(project_action)
            if location == "new":
                self.menubarActions.append(project_action)
        return project_menu

    def add_group_childs(self, group: MenuGroupConfig, grp_menu: QMenu) -> bool:
        """Add all childs of a group config

        :param uri: initial uri of project (can be from local file / http / postgres)
        :type uri: str
        :param group: group menu configuration
        :type group: MenuGroupConfig
        :param grp_menu: menu for group
        :type grp_menu: QMenu
        :return: True if a layer was inserted, False otherwise
        :rtype: bool
        """
        layer_inserted = False
        for child in group.childs:
            if isinstance(child, MenuGroupConfig):
                self.add_group(child, grp_menu)
            elif isinstance(child, MenuLayerConfig):
                layer_inserted = True
                self.add_layer(child, grp_menu)
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

            if layer_inserted and settings.optionLoadAll:
                action = QAction(self.tr("Load all"), self.iface.mainWindow())
                font = QFont()
                font.setBold(True)
                action.setFont(font)
                grp_menu.addAction(action)
                action.triggered.connect(
                    lambda checked, f=None, w=None, m=grp_menu: LayerLoad().loadLayer(
                        None, f, w, m
                    )
                )

    def add_layer(self, layer: MenuLayerConfig, menu: QMenu) -> None:
        """Add layer menu configuration to a menu

        :param uri: initial uri of project (can be from local file / http / postgres)
        :type uri: str
        :param layer: layer menu configuration
        :type layer: MenuLayerConfig
        :param menu: input menu
        :type menu: QMenu
        """
        settings = self.plg_settings.get_plg_settings()
        action = QAction(layer.name, self.iface.mainWindow())

        # add menu item
        action.triggered.connect(
            lambda checked, uri=layer.filename, f=layer.filename, lid=layer.layer_id, m=menu, v=layer.visible, x=layer.expanded: LayerLoad().loadLayer(
                uri, f, lid, m, v, x
            )
        )
        action.setIcon(
            icon_per_layer_type(layer.is_spatial, layer.layer_type, layer.geometry_type)
        )
        if settings.optionTooltip:
            if settings.optionSourceMD == SOURCE_MD_OGC:
                abstract = layer.abstract or layer.metadata_abstract
                title = layer.title or layer.metadata_title
            else:
                abstract = layer.metadata_abstract or layer.abstract
                title = layer.metadata_title or layer.title

            abstract = ""
            title = ""
            for oSource in settings.optionSourceMD:
                if oSource == SOURCE_MD_OGC:
                    abstract = layer.metadata_abstract if abstract == "" else abstract
                    title = title or layer.metadata_title

                if oSource == SOURCE_MD_LAYER:
                    abstract = layer.abstract if abstract == "" else abstract
                    title = title or layer.title

                if oSource == SOURCE_MD_NOTE:
                    abstract = layer.layer_notes if abstract == "" else abstract

            if (abstract != "") and (title == ""):
                action.setToolTip("<p>{}</p>".format(abstract))
            else:
                if abstract != "" or title != "":
                    action.setToolTip("<b>{}</b><br/>{}".format(title, abstract))
                else:
                    action.setToolTip("")

        menu.addAction(action)

    def initGui(self):
        settings = self.plg_settings.get_plg_settings()
        if settings.is_setup_visible:
            # menu item - Main
            self.action_project_configuration = QAction(
                QIcon(str(DIR_PLUGIN_ROOT / "resources/menu_from_project.png")),
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

        self.iface.initializationCompleted.connect(self.on_initializationCompleted)

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
            self.iface.removePluginMenu(
                "&" + __title__, self.action_project_configuration
            )
            self.iface.removePluginMenu("&" + __title__, self.action_menu_help)
            self.action_project_configuration.triggered.disconnect(
                self.open_projects_config
            )
            self.iface.removePluginMenu(__title__, self.action_menu_help)

        self.iface.initializationCompleted.disconnect(self.on_initializationCompleted)

    def open_projects_config(self):
        dlg = MenuConfDialog(self.iface.mainWindow())
        dlg.setModal(True)

        dlg.show()
        result = dlg.exec()
        del dlg

        if result != 0:
            # clear web projects cache
            try:
                self.qgs_dom_manager.cache_clear()
                read_from_http.cache_clear()
                read_from_file.cache_clear()
            except Exception:
                pass

            # build menus
            self.initMenus()
