# standard
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# PyQGIS
from qgis.core import (
    QgsDataSourceUri,
    QgsMapLayerType,
    QgsMessageLog,
    QgsProviderRegistry,
    QgsWkbTypes,
)
from qgis.PyQt import QtXml
from qgis.PyQt.QtCore import QFileInfo

# project
from menu_from_project.__about__ import __title__
from menu_from_project.datamodel.project import Project
from menu_from_project.datamodel.project_config import (
    MenuGroupConfig,
    MenuLayerConfig,
    MenuProjectConfig,
)
from menu_from_project.logic.qgs_manager import (
    QgsDomManager,
    create_map_layer_dict,
    get_project_title,
    is_absolute,
)
from menu_from_project.logic.xml_utils import getFirstChildByAttrValue

# Regular expression to get part before $ and the version after
PATTERN_VERSION = re.compile(r"^(.*?)\s*\$(.+)$")

# Regular expression to get extension list
PATTERN_NAME_EXTENSION = re.compile(r"^(.*?)\s+\(\*([^\)]+)\)$")

LMFP_FORMAT_KEYWORD = "LMFP_FORMAT"


def extract_filter_data(text: str) -> Optional[Tuple[str, List[str]]]:
    """Extract filter data to get provider name and extension list

    :param text: filter text
    :type text: str
    :return: provider name and usable extensions
    :rtype: Optional[Tuple[str, List[str]]]
    """
    match = re.match(PATTERN_NAME_EXTENSION, text)
    if match:
        field = match.group(1).strip()
        extensions = [ext.strip() for ext in match.group(2).split()]
        return field, extensions
    return None


def init_extension_list_from_file_filters(
    file_filter: str,
) -> List[Tuple[str, List[str]]]:
    """Init extension list for provider name from a file filter

    :param file_filter: file filter text
    :type file_filter: str
    :return: list of provider name and usable extensions
    :rtype: List[Tuple[str, List[str]]]
    """
    # Get list of file filters
    file_filters = file_filter.split(";;")
    result = []
    for i, filters in enumerate(file_filters):
        # Don't use first 2 elements that are for All available files and All supported file
        if i > 1:
            res = extract_filter_data(filters)
            if res:
                result.append((res[0], res[1]))
    return result


def init_ogr_extension_list() -> List[Tuple[str, List[str]]]:
    """Define OGR extension list from predifined value are provider registry values

    :return: list of provider name and usable extensions
    :rtype: List[Tuple[str, List[str]]]
    """
    # We define provider name to avoid use of exotic names
    result = [("GeoJSON", [".json", ".geojson", ".JSON", ".GEOJSON"])]

    result += init_extension_list_from_file_filters(
        QgsProviderRegistry.instance().fileVectorFilters()
    )
    return result


def init_gdal_extension_list() -> List[Tuple[str, List[str]]]:
    """Define GDAL extension list from predifined value are provider registry values

    :return: list of provider name and usable extension
    :rtype: List[Tuple[str, List[str]]]
    """

    # We define provider name to avoid use of exotic names
    result = [("GeoTIFF", [".tiff", ".tif"])]
    result += init_extension_list_from_file_filters(
        QgsProviderRegistry.instance().fileRasterFilters()
    )
    return result


OGR_EXTENSION_LIST = init_ogr_extension_list()
GDAL_EXTENSION_LIST = init_gdal_extension_list()


def get_embedded_project_from_layer_tree(
    node: QtXml.QDomNode, init_filename: str, absolute_project: bool
) -> str:
    """Get embedded project path from layer tree and his parent

    :param layer_tree: layer tree to inspect
    :type layer_tree: QgsLayerTreeNode
    :param project: project where layer tree is used
    :type project: QgsProject
    :return: path to embedded project
    :rtype: str
    """
    element = node.toElement()
    customproperties_nd = element.elementsByTagName("customproperties")
    if customproperties_nd.size() > 0:
        eFileNd = getFirstChildByAttrValue(
            customproperties_nd.at(0), "property", "key", "embedded_project"
        ) or getFirstChildByAttrValue(
            customproperties_nd.at(0), "Option", "name", "embedded_project"
        )
        filename = ""
        if eFileNd:
            # get project file name
            embeddedFile = eFileNd.toElement().attribute("value")
            if not absolute_project and (embeddedFile.find(".") == 0):
                filename = QFileInfo(init_filename).path() + "/" + embeddedFile
            else:
                filename = QFileInfo(embeddedFile).absoluteFilePath()
        else:
            layer_id = element.attribute("id")

            QgsMessageLog.logMessage(
                f"Menu from layer: Embeded project not found for {layer_id}",
                __title__,
                notifyUser=True,
            )
            filename = ""
    if filename == "" and not node.parentNode().isNull():
        return get_embedded_project_from_layer_tree(
            node.parentNode(),
            init_filename=init_filename,
            absolute_project=absolute_project,
        )

    return filename


def read_embedded_properties(
    node: QtXml.QDomNode, init_filename: str, absolute_project: bool
) -> Tuple[bool, str]:
    """Read embedded properties from a QgsLayerTreeNode in a QgsProject

    :param layer_tree: layer tree to inspect
    :type layer_tree: QgsLayerTreeNode
    :param project: project where layer tree is used
    :type project: QgsProject
    :return: Boolean indicating if the layer tree is embedded and the filename of the project used
    :rtype: Tuple[bool, str]
    """
    element = node.toElement()

    embedded = False
    filename = init_filename

    customproperties_nd = element.elementsByTagName("customproperties")
    if customproperties_nd.size() > 0:
        embedNd = getFirstChildByAttrValue(
            customproperties_nd.at(0), "property", "key", "embedded"
        ) or getFirstChildByAttrValue(
            customproperties_nd.at(0), "Option", "name", "embedded"
        )

        if embedNd and embedNd.toElement().attribute("value") == "1":
            embedded = True
            filename = get_embedded_project_from_layer_tree(
                node=node,
                init_filename=init_filename,
                absolute_project=absolute_project,
            )

    return embedded, filename


def get_layer_type_from_geometry_str(
    geometry_type_str: str,
) -> Tuple[Optional[QgsMapLayerType], Optional[QgsWkbTypes.GeometryType], bool]:
    """Get layer type from geometry str

    :param geometry_type_str: geometry str in xml node
    :type geometry_type_str: str
    :return: layer_type, geometry_type, is_spatial
    :rtype: Tuple[Optional[QgsMapLayerType], Optional[QgsWkbTypes.GeometryType], bool]
    """
    geometry_type_str = geometry_type_str.lower()
    if geometry_type_str == "raster":
        return QgsMapLayerType.RasterLayer, None, True
    elif geometry_type_str == "mesh":
        return QgsMapLayerType.MeshLayer, None, True
    elif geometry_type_str == "vector-tile":
        return QgsMapLayerType.VectorTileLayer, None, True
    elif geometry_type_str == "point-cloud":
        return QgsMapLayerType.PointCloudLayer, None, True
    elif geometry_type_str == "point":
        return QgsMapLayerType.VectorLayer, QgsWkbTypes.GeometryType.PointGeometry, True
    elif geometry_type_str == "line":
        return QgsMapLayerType.VectorLayer, QgsWkbTypes.GeometryType.LineGeometry, True
    elif geometry_type_str == "polygon":
        return (
            QgsMapLayerType.VectorLayer,
            QgsWkbTypes.GeometryType.PolygonGeometry,
            True,
        )
    elif geometry_type_str == "no geometry":
        return None, None, False
    return None, None, False


def define_name_and_version_from_layer_name(layername: str) -> Tuple[str, str]:
    """Define name and version from layer name

    :param layername: layer name
    :type layername: str
    :return: name,version
    :rtype: Tuple[str, str]
    """

    # Recherche de la version
    match = re.search(PATTERN_VERSION, layername)
    if match:
        name = match.group(1)  # Tout ce qui est avant le $
        version = match.group(2)  # Le champ de version après le $
    else:
        version = ""
        name = layername

    return name, version


def define_provider_name_from_extension_list(
    provider: str, datasource: str, extension_list: List[Tuple[str, List[str]]]
) -> str:
    """Define a provider from datasource and extension list

    :param provider: input provider
    :type provider: str
    :param datasource: datasource
    :type datasource: str
    :param extension_list: extension dict
    :type extension_list: List[Tuple[str, List[str]]]
    :return: provider name from extension dict if datasource extension is found, otherwise input provider
    :rtype: str
    """
    result = provider
    for provider_name, extensions in extension_list:
        for extension in extensions:
            if datasource.count(extension):
                return provider_name
    return result


def define_provider_name_wms_datasource(provider: str, datasource: str) -> str:
    """Define provider name from wms datasource
    Check for type parameter or tileMatrixSet/tileDimensions for WMTS

    :param provider: input provider name
    :type provider: str
    :param datasource: datasource uri
    :type datasource: str
    :return: provider name from datasource uri if rule apply, otherwise input provider
    :rtype: str
    """
    uri = QgsDataSourceUri()
    uri.setEncodedUri(datasource)
    if uri.hasParam("type"):
        return uri.param("type")
    if uri.hasParam("tileMatrixSet"):
        return "WMTS"
    if uri.hasParam("tileDimensions"):
        return "WMTS"
    return provider


def define_provider_name_from_metadata(md: QtXml.QDomNode, provider: str) -> str:
    """Define provider name from metadata if available

    :param md: metadata dom node
    :type md: QtXml.QDomNode
    :param provider: initial provider
    :type provider: str
    :return: provider name from metadata if available otherwise input provider name
    :rtype: str
    """
    keywords = md.toElement().elementsByTagName("keywords")
    for i in range(0, keywords.size()):
        value = keywords.at(i)
        element = value.toElement()
        vocabulary = element.attribute("vocabulary")
        if vocabulary == LMFP_FORMAT_KEYWORD:
            keyword = element.elementsByTagName("keyword")
            if keyword.size() > 0:
                return keyword.at(0).toElement().text()
    return provider


def get_layer_menu_config(
    node: QtXml.QDomNode,
    maplayer_dict: Dict[str, QtXml.QDomNode],
    qgs_dom_manager: QgsDomManager,
    init_filename: str,
    absolute_project: bool,
) -> Optional[MenuLayerConfig]:
    """Get layer menu configuration from a xml node

    :param node: xml node
    :type node: QtXml.QDomNode
    :param maplayer_dict: dict of maplayer nodes
    :type maplayer_dict: Dict[str, QtXml.QDomNode]
    :param qgs_dom_manager: manager to get qgs doc for embedded project
    :type qgs_dom_manager: QgsDomManager
    :param init_filename: _description_
    :param init_filename: initial filename of project
    :type init_filename: str
    :param absolute_project: True if project is absolute, False otherwise
    :type absolute_project: bool
    :return: layer menu configuration
    :rtype: Optional[MenuLayerConfig]
    """

    embedded, filename = read_embedded_properties(
        node=node, init_filename=init_filename, absolute_project=absolute_project
    )

    element = node.toElement()
    layer_id = element.attribute("id")

    if embedded:
        ml = qgs_dom_manager.getMapLayerDomFromQgs(filename, layer_id)
    elif layer_id in maplayer_dict:
        ml = maplayer_dict[layer_id]
    else:
        ml = None

    if not ml:
        QgsMessageLog.logMessage(
            f"Menu from layer: Can't find layer {layer_id} in qgs project. Layer won't be added to project.",
            __title__,
            notifyUser=True,
        )
        return None
    # Metadata infos
    md = ml.namedItem("resourceMetadata")
    metadata_title = md.namedItem("title").firstChild().toText().data()
    metadata_abstract = md.namedItem("abstract").firstChild().toText().data()

    # Layer info
    title = ml.namedItem("title").firstChild().toText().data()
    abstract = ml.namedItem("abstract").firstChild().toText().data()

    # Layer notes
    layer_notes = ""
    elt_note = ml.namedItem("userNotes")
    if elt_note.toElement().hasAttribute("value"):
        layer_notes = elt_note.toElement().attribute("value")

    # Geometry and layer type
    ml_elem = ml.toElement()
    geometry_type_str = ml_elem.attribute("geometry")
    if geometry_type_str == "":
        # A TMS has not a geometry attribute.
        # Let's read the "type"
        geometry_type_str = ml_elem.attribute("type")
    layer_type, geometry_type, is_spatial = get_layer_type_from_geometry_str(
        geometry_type_str
    )

    name = element.attribute("name")
    name, version = define_name_and_version_from_layer_name(name)

    providerNode = ml.namedItem("provider")
    provider = providerNode.firstChild().toText().data()

    datasourceNode = ml.namedItem("datasource")
    ds = datasourceNode.firstChild().toText().data()
    if provider == "ogr":
        provider = define_provider_name_from_extension_list(
            provider, ds, OGR_EXTENSION_LIST
        )
    elif provider == "gdal":
        provider = define_provider_name_from_extension_list(
            provider, ds, GDAL_EXTENSION_LIST
        )
    elif provider == "wms":
        provider = define_provider_name_wms_datasource(provider, ds)

    provider = define_provider_name_from_metadata(md, provider)

    return MenuLayerConfig(
        name=name,
        layer_id=layer_id,
        filename=filename,
        visible=element.attribute("checked", "") == "Qt::Checked",
        expanded=element.attribute("expanded", "0") == "1",
        embedded=embedded,
        layer_type=layer_type,
        metadata_abstract=metadata_abstract,
        metadata_title=metadata_title,
        abstract=abstract,
        is_spatial=is_spatial,
        title=title,
        geometry_type=geometry_type,
        layer_notes=layer_notes,
        version=version,
        format=provider,
    )


def get_embedded_group_config(
    filename: str, group_name: str, qgs_dom_manager: QgsDomManager
) -> Optional[MenuGroupConfig]:
    """Get group menu configuration for an embedded group name

    :param filename: embedded filename
    :type filename: str
    :param group_name: embedded group name
    :type group_name: str
    :param qgs_dom_manager: manager to get qgs doc for embedded project
    :type qgs_dom_manager: QgsDomManager
    :return: Optional menu group configuration
    :rtype: Optional[MenuGroupConfig]
    """
    doc, _ = qgs_dom_manager.getQgsDoc(filename)
    # Get layer tree root
    layer_tree_roots = doc.elementsByTagName("layer-tree-group")
    if layer_tree_roots.length() > 0:
        if node := layer_tree_roots.item(0):
            # Get all layer / group in tree
            childrens = node.childNodes()
            for i in range(0, childrens.size()):
                child = childrens.at(i)
                element = child.toElement()
                name = element.attribute("name")
                # Get only group with same name
                if child.nodeName() == "layer-tree-group" and name == group_name:
                    # Create dict of maplayer nodes
                    maplayer_dict = create_map_layer_dict(doc)

                    return get_group_menu_config(
                        node=child,
                        maplayer_dict=maplayer_dict,
                        qgs_dom_manager=qgs_dom_manager,
                        init_filename=filename,
                        absolute_project=is_absolute(doc=doc),
                    )

    return None


def get_group_menu_config(
    node: QtXml.QDomNode,
    maplayer_dict: Dict[str, QtXml.QDomNode],
    qgs_dom_manager: QgsDomManager,
    init_filename: str,
    absolute_project: bool,
) -> MenuGroupConfig:
    """Get group menu configuration from a xml node

    :param node: xml node
    :type node: QtXml.QDomNode
    :param maplayer_dict: dict of maplayer nodes
    :type maplayer_dict: Dict[str, QtXml.QDomNode]
    :param qgs_dom_manager: manager to get qgs doc for embedded project
    :type qgs_dom_manager: QgsDomManager
    :param init_filename: initial filename of project
    :type init_filename: str
    :param absolute_project: True if project is absolute, False otherwise
    :type absolute_project: bool
    :return: group menu configuration
    :rtype: MenuGroupConfig
    """

    element = node.toElement()
    name = element.attribute("name")

    embedded, filename = read_embedded_properties(
        node=node, init_filename=init_filename, absolute_project=absolute_project
    )

    childs = []

    # If embedded group, add all layer and subgroup from the group of same name
    if embedded:
        embedded_group = get_embedded_group_config(
            filename=filename, group_name=name, qgs_dom_manager=qgs_dom_manager
        )
        if embedded_group:
            childs += embedded_group.childs

    childrens = node.childNodes()

    for i in range(0, childrens.size()):
        child = childrens.at(i)
        if child.nodeName() == "layer-tree-group":
            childs.append(
                get_group_menu_config(
                    node=child,
                    maplayer_dict=maplayer_dict,
                    qgs_dom_manager=qgs_dom_manager,
                    init_filename=init_filename,
                    absolute_project=absolute_project,
                )
            )
        elif child.nodeName() == "layer-tree-layer":
            layer_config = get_layer_menu_config(
                node=child,
                maplayer_dict=maplayer_dict,
                qgs_dom_manager=qgs_dom_manager,
                init_filename=init_filename,
                absolute_project=absolute_project,
            )
            if layer_config:
                childs.append(layer_config)

    return MenuGroupConfig(
        name=name, embedded=embedded, filename=filename, childs=childs
    )


def get_project_menu_config(
    project: Project,
    qgs_dom_manager: QgsDomManager,
) -> Optional[MenuProjectConfig]:
    """Get project menu configuration for a project

    :param project: dict of information about the project
    :type project: Project
    :param qgs_dom_manager: manager to get qgs doc for project
    :type qgs_dom_manager: QgsDomManager
    :return: Optional menu project configuration
    :rtype: Optional[MenuProjectConfig]
    """
    try:
        # Get path to QgsProject file, local / downloaded / from postgres database
        uri = project.file
        qgs_dom_manager.set_project(project)
        doc, filename = qgs_dom_manager.getQgsDoc(uri)

        # Define project name
        name = project.name
        if name == "":
            name = get_project_title(doc)
        if name == "":
            name = Path(filename).stem

        # Get layer tree root
        layer_tree_roots = doc.elementsByTagName("layer-tree-group")
        if layer_tree_roots.length() > 0:
            if node := layer_tree_roots.item(0):
                # Create dict of maplayer nodes
                maplayer_dict = create_map_layer_dict(doc)
                # Parse node for group and layers
                menu_project_config = MenuProjectConfig(
                    project_name=name,
                    filename=filename,
                    uri=uri,
                    root_group=get_group_menu_config(
                        node=node,
                        maplayer_dict=maplayer_dict,
                        qgs_dom_manager=qgs_dom_manager,
                        init_filename=filename,
                        absolute_project=is_absolute(doc),
                    ),
                )

                qgs_dom_manager.set_project(None)
                return menu_project_config
    except Exception as e:
        QgsMessageLog.logMessage(
            f"Menu from layer: Can't parse qgs project for {project.name} : {e}",
            __title__,
            notifyUser=True,
        )
    return None
