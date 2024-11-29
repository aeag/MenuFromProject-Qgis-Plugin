# standard
from dataclasses import dataclass
from typing import Any, List, Optional

# PyQGIS
from qgis.core import QgsMapLayerType, QgsWkbTypes


@dataclass
class MenuLayerConfig:
    """Class to store configuration for layer menu creation"""

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
    """Class to store configuration for group menu creation"""

    name: str
    filename: str
    childs: List[Any]  # List of Union[MenuLayerConfig,MenuGroupConfig]
    embedded: bool

    @classmethod
    def from_json(cls, data):
        childs = []
        for child in data["childs"]:
            if "childs" in child:
                childs.append(cls.from_json(child))
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
    """Class to store configuration for project menu creation"""

    project_name: str
    filename: str
    uri: str
    root_group: MenuGroupConfig

    @classmethod
    def from_json(cls, data):
        """
        Define User from json data

        Args:
            data: json data

        Returns: User

        """
        res = cls(
            filename=data["filename"],
            uri=data["uri"],
            project_name=data["project_name"],
            root_group=MenuGroupConfig.from_json(data["root_group"]),
        )
        return res
