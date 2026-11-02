#! python3

# Standard library
from functools import lru_cache
from typing import Optional

# PyQGIS
from qgis.core import QgsApplication, QgsLayerItem, QgsMapLayerType, QgsWkbTypes
from qgis.PyQt.QtGui import QIcon

# project
from menu_from_project.__about__ import DIR_PLUGIN_ROOT

# ############################################################################
# ########## Classes ###############
# ##################################


@lru_cache
def guess_type_from_uri(qgs_uri: str) -> str:
    """Return project storage type based on the QGS URI.

    :param qgs_uri: QGS project URI (filepath, url or connection string)
    :type qgs_uri: str

    :return: storage type: "database", "file" or "http"
    :rtype: str
    """
    if qgs_uri.startswith("postgresql"):
        return "database"
    elif qgs_uri.startswith("http"):
        return "http"
    else:
        return "file"


@lru_cache
def icon_per_storage_type(type_storage: str) -> str:
    """Returns the icon for a storage type,

    :param type_storage: [description]
    :type type_storage: str

    :return: icon path
    :rtype: str
    """
    if type_storage == "file":
        return QgsApplication.iconPath("mIconQgsProjectFile.svg")
    elif type_storage == "database":
        return QgsApplication.iconPath("mIconPostgis.svg")
    elif type_storage == "http":
        return str(DIR_PLUGIN_ROOT / "resources/globe.svg")
    else:
        return QgsApplication.iconPath("mIconQgsProjectFile.svg")


@lru_cache
def icon_per_layer_type(
    is_spatial: bool,
    layer_type: QgsMapLayerType,
    geometry_type: Optional[QgsWkbTypes.GeometryType],
) -> QIcon:
    """Return a icon from a layer type

    :param is_spatial: true if layer is spatial, false otherwise
    :type is_spatial: bool
    :param layer_type: layer type
    :type layer_type: QgsMapLayerType
    :param geometry_type: geometry type if layer is a QgsVectorLayer
    :type geometry_type: Optional[QgsWkbTypes.GeometryType]
    :return: icon for layer
    :rtype: QIcon
    """
    if not is_spatial:
        return QgsLayerItem.iconTable()
    if layer_type == QgsMapLayerType.RasterLayer:
        return QgsLayerItem.iconRaster()
    elif layer_type == QgsMapLayerType.MeshLayer:
        return QgsLayerItem.iconMesh()
    elif layer_type == QgsMapLayerType.VectorTileLayer:
        return QgsLayerItem.iconVectorTile()
    elif layer_type == QgsMapLayerType.PointCloudLayer:
        return QgsLayerItem.iconPointCloud()
    elif layer_type == QgsMapLayerType.VectorLayer:
        if geometry_type == QgsWkbTypes.GeometryType.PointGeometry:
            return QgsLayerItem.iconPoint()
        elif geometry_type == QgsWkbTypes.GeometryType.LineGeometry:
            return QgsLayerItem.iconLine()
        elif geometry_type == QgsWkbTypes.GeometryType.PolygonGeometry:
            return QgsLayerItem.iconPolygon()
        return QgsLayerItem.iconPoint()
    return QgsLayerItem.iconDefault()
