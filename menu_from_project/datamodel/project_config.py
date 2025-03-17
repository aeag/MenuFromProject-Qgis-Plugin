# standard
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# PyQGIS
from qgis.core import QgsMapLayerType, QgsWkbTypes


@dataclass
class MenuLayerConfig:
    """Class to store configuration for layer menu creation."""

    name: str
    layer_id: str
    filename: str
    visible: bool
    expanded: bool
    embedded: str
    is_spatial: bool
    layer_type: Optional[QgsMapLayerType]
    metadata_abstract: str
    metadata_title: str
    layer_notes: str
    abstract: str
    title: str
    geometry_type: Optional[QgsWkbTypes.GeometryType] = None
    version: str = ""
    format: str = ""


@dataclass
class MenuGroupConfig:
    """Class to store configuration for group menu creation."""

    name: str
    filename: str
    childs: List[Any]  # List of Union[MenuLayerConfig,MenuGroupConfig]
    embedded: bool

    @staticmethod
    def sort_layer_list_by_version(
        layer_name_list: List[MenuLayerConfig],
    ) -> Dict[str, List[MenuLayerConfig]]:
        """Sort a layer name list by version and create a dict with key version and value layer configuration list

        :param layer_name_list: layer config list
        :type layer_name_list: List[MenuLayerConfig]

        :return: dict of layer list by version
        :rtype: Dict[str, List[MenuLayerConfig]]
        """
        layer_dict = {}
        for layer in layer_name_list:
            if layer.version in layer_dict:
                layer_dict[layer.version].append(layer)
            else:
                layer_dict[layer.version] = [layer]
        return layer_dict

    def get_layer_configs_from_name(self, name: str) -> List[MenuLayerConfig]:
        """Get layer configurations by name

        :param name: layer name
        :type name: str

        :return: list of layer configuration
        :rtype: List[MenuLayerConfig]
        """
        return [
            layer
            for layer in self.childs
            if isinstance(layer, MenuLayerConfig) and layer.name == name
        ]

    @classmethod
    def from_dict(cls, data: dict) -> "MenuGroupConfig":
        """Convert dictionary data into MenuGroupConfig object.

        :param data: input data , typiclly loaded from a JSON file.
        :type data: dict

        :return: MenuGroupConfig dataclass instanciated
        :rtype: MenuGroupConfig
        """
        childs = []
        for child in data["childs"]:
            if "childs" in child:
                childs.append(cls.from_dict(child))
            else:
                childs.append(MenuLayerConfig(**child))
        res = cls(
            name=data["name"],
            filename=data["filename"],
            embedded=data["embedded"],
            childs=childs,
        )
        return res


@dataclass
class MenuProjectConfig:
    """Class to store configuration for project menu creation."""

    project_name: str
    filename: str
    uri: str
    root_group: MenuGroupConfig

    @classmethod
    def from_dict(cls, data: dict) -> "MenuProjectConfig":
        """Convert dictionary data into MenuProjectConfig object.

        :param data: input data , typiclly loaded from a JSON file.
        :type data: dict

        :return: MenuProjectConfig dataclass instanciated
        :rtype: MenuProjectConfig
        """

        res = cls(
            filename=data["filename"],
            uri=data["uri"],
            project_name=data["project_name"],
            root_group=MenuGroupConfig.from_dict(data["root_group"]),
        )
        return res
