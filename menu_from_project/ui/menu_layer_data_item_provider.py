# Standard library
import os.path
from typing import Dict, List, Tuple

# PyQGIS
from qgis.core import (
    QgsApplication,
    QgsDataCollectionItem,
    QgsDataItem,
    QgsDataItemProvider,
    QgsDataProvider,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QWidget

# project
from menu_from_project.datamodel.project import Project
from menu_from_project.logic.layer_load import LayerLoad
from menu_from_project.logic.project_read import (
    MenuGroupConfig,
    MenuLayerConfig,
    MenuProjectConfig,
)
from menu_from_project.logic.tools import icon_per_layer_type
from menu_from_project.toolbelt.preferences import PlgOptionsManager


class MenuLayerProvider(QgsDataItemProvider):
    """Provider for plugin data item"""

    def __init__(self, project_configs: List[Tuple[Project, MenuProjectConfig]]):
        """Constructor for provider

        :param project_configs: list of project configuration
        :type project_configs: List[MenuProjectConfig]
        """
        QgsDataItemProvider.__init__(self)
        self.project_configs = project_configs

    def name(self) -> str:
        """Human readable name

        :return: name of item
        :rtype: str
        """
        return "Layer from project"

    def capabilities(self) -> int:
        """Returns combination of flags from QgsDataProvider::DataCapabilities.

        :return: item data capabilities
        :rtype: int
        """
        return QgsDataProvider.Net

    def createDataItem(self, path: str, parentItem: QgsDataItem) -> QgsDataItem:
        """Create root collection for provider

        :param path: current path (unused)
        :type path: str
        :param parentItem: parent
        :type parentItem: QgsDataItem
        :return: RootCollection data item
        :rtype: QgsDataItem
        """
        return RootCollection(parent=parentItem, project_configs=self.project_configs)


class RootCollection(QgsDataCollectionItem):
    """QgsDataCollectionItem to add available project as children"""

    def __init__(
        self,
        parent: QgsDataItem,
        project_configs: List[Tuple[Project, MenuProjectConfig]],
    ):
        """_summary_

        :param parent: parent
        :type parent: QgsDataItem
        :param project_configs: list of project configuration
        :type project_configs: List[Tuple[Project, MenuProjectConfig]]
        """
        QgsDataCollectionItem.__init__(self, parent, "MenuLayer", "/MenuLayer")
        # TODO : define icon
        self.project_configs = project_configs

    def createChildren(self) -> List[QgsDataItem]:
        """Create children for each project

        :return: QgsDataItem for each project
        :rtype: List[QgsDataItem]
        """
        children = []
        previous = None
        for project, project_config in self.project_configs:
            if project.location == "merge" and previous:
                pfc = ProjectCollection(
                    parent=previous, project_menu_config=project_config
                )
                previous.merged_project.append(pfc)
            elif project.location == "browser":
                previous = ProjectCollection(
                    parent=self, project_menu_config=project_config
                )
                children.append(previous)
            else:
                previous = None
        return children


class ProjectCollection(QgsDataCollectionItem):
    """QgsDataCollectionItem to add all group and layer available in a project"""

    def __init__(self, parent: QgsDataItem, project_menu_config: MenuProjectConfig):
        """Constructor for a project QgsDataCollectionItem

        :param parent: parent
        :type parent: QgsDataItem
        :param project_menu_config: project configuration
        :type project_menu_config: MenuProjectConfig
        """
        self.path = "/MenuLayer/" + project_menu_config.project_name.lower()
        self.parent = parent
        QgsDataCollectionItem.__init__(
            self, parent, project_menu_config.project_name, self.path
        )
        self.project_menu_config = project_menu_config
        self.setName(project_menu_config.project_name)
        self.setIcon(QIcon(QgsApplication.iconPath("mIconFolderProject.svg")))

        self.merged_project = []

    def createChildren(self) -> List[QgsDataItem]:
        """Create children for all group and layer available in project

        :return: QgsDataItem for each project
        :rtype: List[QgsDataItem]
        """
        root_group = GroupItem(
            parent=self, group_config=self.project_menu_config.root_group
        )
        children = root_group.createChildren()

        for project in self.merged_project:
            children.extend(project.createChildren())

        return children


class GroupItem(QgsDataCollectionItem):
    """QgsDataCollectionItem to add all group and layer available in a group"""

    def __init__(self, parent: QgsDataItem, group_config: MenuGroupConfig):
        """Constructor for a group QgsDataCollectionItem

        :param parent: parent
        :type parent: QgsDataItem
        :param group_config: group configuration
        :type group_config: MenuGroupConfig
        """
        self.path = os.path.join(parent.path, group_config.name)
        self.group_config = group_config
        QgsDataCollectionItem.__init__(self, parent, group_config.name, self.path)
        self.setIcon(QIcon(QgsApplication.iconPath("mIconFolder.svg")))

        self.layer_inserted = []

    def createChildren(self) -> List[QgsDataItem]:
        """Create children for all group and layer available in a group

        :return: QgsDataItem for each project
        :rtype: List[QgsDataItem]
        """
        children = []
        self.layer_inserted = []
        for child in self.group_config.childs:
            if isinstance(child, MenuGroupConfig):
                children.insert(0, GroupItem(parent=self, group_config=child))
            elif isinstance(child, MenuLayerConfig):
                self.layer_inserted.append(child)
                children.insert(
                    0,
                    LayerItem(
                        parent=self,
                        layer_config=child,
                        group_name=self.group_config.name,
                    ),
                )
        return children

    def actions(self, parent: QWidget) -> List[QAction]:
        """Return list of available actions for layer

        :param parent: parent
        :type parent: QWidget
        :return: list of available actions
        :rtype: List[QAction]
        """
        settings = PlgOptionsManager().get_plg_settings()

        if len(self.layer_inserted) != 0 and settings.optionLoadAll:
            ac_show_layer = QAction(self.tr("Load all"), parent)
            ac_show_layer.triggered.connect(self._add_layer_inserted)
            return [ac_show_layer]
        return []

    def _add_layer_inserted(self) -> None:
        """Add inserted layers to current QGIS project"""
        LayerLoad().load_layer_list(self.layer_inserted, self.group_config.name)


def create_add_layer_action(
    layer: MenuLayerConfig, action_text: str, group_name: str, parent: QWidget
) -> QAction:
    action = QAction(action_text, parent)
    action.triggered.connect(lambda checked: LayerLoad().load_layer(layer, group_name))
    settings = PlgOptionsManager().get_plg_settings()

    if settings.optionTooltip:
        action.setToolTip(settings.tooltip_for_layer(layer))

    action.setIcon(
        icon_per_layer_type(
            is_spatial=layer.is_spatial,
            layer_type=layer.layer_type,
            geometry_type=layer.geometry_type,
        )
    )
    return action


class LayerDictItem(QgsDataItem):
    """QgsDataCollectionItem to add all group and layer available in a group"""

    def __init__(
        self,
        parent: QgsDataItem,
        layer_dict: Dict[str, Dict[str, MenuLayerConfig]],
        group_name: str,
    ):
        """Constructor for a group QgsDataCollectionItem

        :param parent: parent
        :type parent: QgsDataItem
        :param group_config: group configuration
        :type group_config: MenuGroupConfig
        """
        self.first_layer = list(list(layer_dict.values())[0].values())[0]
        self.path = os.path.join(parent.path, self.first_layer.name)
        self.layer_dict = layer_dict
        self.group_name = group_name
        QgsDataItem.__init__(
            self, QgsDataItem.Custom, parent, self.first_layer.name, self.path
        )
        self.setState(QgsDataItem.Populated)  # no children

        settings = PlgOptionsManager().get_plg_settings()

        if settings.optionTooltip:
            self.setToolTip(settings.tooltip_for_layer(self.first_layer))
        self.setIcon(
            icon_per_layer_type(
                is_spatial=self.first_layer.is_spatial,
                layer_type=self.first_layer.layer_type,
                geometry_type=self.first_layer.geometry_type,
            )
        )

    def handleDoubleClick(self) -> None:
        """Load layer at double click"""
        LayerLoad().load_layer(self.first_layer, self.group_name)
        return True

    def actions(self, parent: QWidget) -> List[QAction]:
        """Return list of available actions for layer

        :param parent: parent
        :type parent: QWidget
        :return: list of available actions
        :rtype: List[QAction]
        """
        actions = []
        actions.append(
            create_add_layer_action(
                self.first_layer, self.tr("Display layer"), self.group_name, parent
            )
        )

        for version, format_dict in self.layer_dict.items():
            if len(format_dict) > 1:
                ac_version = QAction(version, parent)
                version_menu = QMenu(version, parent)
                ac_version.setMenu(version_menu)
                actions.append(ac_version)
            else:
                version_menu = None
            for format_, layer in format_dict.items():
                if len(format_dict) > 1:
                    action_text = format_
                else:
                    action_text = f"{layer.version} - {layer.format}"
                ac_layer = create_add_layer_action(
                    layer, action_text, self.group_name, parent
                )
                if version_menu:
                    version_menu.addAction(ac_layer)
                else:
                    actions.append(ac_layer)
        return actions


class LayerItem(QgsDataItem):
    """QgsDataItem for layer"""

    def __init__(
        self, parent: QgsDataItem, layer_config: MenuLayerConfig, group_name: str
    ):
        """Constructor for a QgsDataItem to display layer configuration

        :param parent: parent
        :type parent: QgsDataItem
        :param layer_config: layer configuration
        :type layer_config: MenuLayerConfig
        :param group_name: group name
        :type group_name: str
        """
        self.layer_config = layer_config
        self.group_name = group_name
        self.path = os.path.join(parent.path, layer_config.name)
        QgsDataItem.__init__(
            self, QgsDataItem.Custom, parent, layer_config.name, self.path
        )
        self.setState(QgsDataItem.Populated)  # no children

        settings = PlgOptionsManager().get_plg_settings()

        if settings.optionTooltip:
            self.setToolTip(settings.tooltip_for_layer(layer_config))
        self.setIcon(
            icon_per_layer_type(
                is_spatial=self.layer_config.is_spatial,
                layer_type=self.layer_config.layer_type,
                geometry_type=self.layer_config.geometry_type,
            )
        )

    def handleDoubleClick(self) -> None:
        """Load layer at double click"""
        LayerLoad().load_layer(self.layer_config, self.group_name)
        return True

    def actions(self, parent: QWidget) -> List[QAction]:
        """Return list of available actions for layer

        :param parent: parent
        :type parent: QWidget
        :return: list of available actions
        :rtype: List[QAction]
        """
        return [
            create_add_layer_action(
                self.layer_config, self.tr("Display layer"), self.group_name, parent
            )
        ]
