#! python3  # noqa: E265

"""
Functions used to manage QGIS Projects: read, extract, get properties.
"""

# Standard library
import os
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

# PyQGIS
from qgis.core import (
    QgsApplication,
    QgsFileDownloader,
    QgsMessageLog,
    QgsReadWriteContext,
)
from qgis.PyQt import QtXml
from qgis.PyQt.QtCore import (
    QDir,
    QEventLoop,
    QFile,
    QFileInfo,
    QIODevice,
    QTemporaryDir,
    QUrl,
)
from qgis.utils import iface

# project
from menu_from_project.__about__ import __title__, __title_clean__
from menu_from_project.datamodel.project import Project
from menu_from_project.logic.cache_manager import CacheManager
from menu_from_project.logic.tools import guess_type_from_uri
from menu_from_project.logic.xml_utils import getFirstChildByTagNameValue

# ############################################################################
# ########## Globals ###############
# ##################################


cache_folder = Path.home() / f".cache/QGIS/{__title_clean__}"
cache_folder.mkdir(exist_ok=True, parents=True)


# ############################################################################
# ########## Functions #############
# ##################################


def is_absolute(doc: QtXml.QDomDocument) -> bool:
    """Return true if the given XML document is using absolute path.

    :param doc: The QGIS project as XML document.
    :type doc: QDomDocument
    """
    absolute = False
    try:
        props = doc.elementsByTagName("properties")
        if props.count() == 1:
            node = props.at(0)
            pathNode = node.namedItem("Paths")
            absNode = pathNode.namedItem("Absolute")
            absolute = "true" == absNode.firstChild().toText().data()
    except Exception:
        pass

    return absolute


def project_trusted(doc):
    """Return if the project is trusted.

    :param doc: The QGIS project as XML document. Default to None.
    :type doc: QDomDocument

    :return: True of False.
    :rtype: bool
    """
    tags = doc.elementsByTagName("qgis")
    if tags.count():
        node = tags.at(0)
        trust_node = node.namedItem("trust")
        return trust_node.toElement().attribute("active") == "1"

    return False


def create_map_layer_dict(doc: QtXml.QDomDocument) -> Dict[str, QtXml.QDomNode]:
    """Create dict key : layer id, value : layer node

    :param doc: input qgis project xml document
    :type doc: QtXml.QDomDocument
    :return: dict of layer id to layer node
    :rtype: Dict[str, QtXml.QDomNode]
    """
    r = {}
    nodes = doc.documentElement().elementsByTagName("maplayer")
    for node in (nodes.at(i) for i in range(nodes.size())):
        nd = node.namedItem("id")
        if nd:
            r[nd.firstChild().toText().data()] = node

    return r


def get_project_title(doc: QtXml.QDomDocument) -> str:
    """Return the project title defined in the XML document.
    :param doc: The QGIS project as XML document. Default to None.
    :type doc: QDomDocument
    :return: The title or None.
    :rtype: string
    """
    tags = doc.elementsByTagName("qgis")
    if tags.count():
        node = tags.at(0)
        title_node = node.namedItem("title")
        return title_node.firstChild().toText().data()

    return None


@lru_cache()
def read_from_file(uri: str) -> QtXml.QDomDocument:
    """Read a QGIS project (.qgs and .qgz) from a file path and returns d

    :param uri: path to the file
    :type uri: str

    :return: a tuple with XML document and the filepath.
    :rtype: Tuple[QtXml.QDomDocument, str]
    """
    doc = QtXml.QDomDocument()
    file = QFile(uri)
    if (
        file.exists()
        and file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text)
        and QFileInfo(file).suffix() == "qgs"
    ):
        doc.setContent(file)

    elif file.exists() and (QFileInfo(file).suffix() == "qgz"):
        temporary_unzip = QTemporaryDir()
        temporary_unzip.setAutoRemove(False)
        with zipfile.ZipFile(uri, "r") as zip_ref:
            zip_ref.extractall(temporary_unzip.path())

        project_filename = QDir(temporary_unzip.path()).entryList(["*.qgs"])[0]
        project_path = os.path.join(temporary_unzip.path(), project_filename)
        xml = QFile(project_path)
        if xml.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
            doc.setContent(xml)

    return doc


def read_from_database(
    uri: str, project_registry, download_folder: Path
) -> Tuple[QtXml.QDomDocument, str]:
    """Read a QGIS project stored into a (PostgreSQL) database.

    :param uri: connection string to QGIS project stored into a database.
    :type uri: str

    :return: a tuple with XML document and the filepath.
    :rtype: Tuple[QtXml.QDomDocument, str]
    """
    # uri PG
    project_storage = project_registry.projectStorageFromUri(uri)
    _, metadata = project_storage.readProjectStorageMetadata(uri)

    project_file = download_folder / f"{metadata.name}.qgz"
    temporary_zip = QFile(str(project_file))
    temporary_zip.open(QIODevice.OpenModeFlag.WriteOnly)

    project_storage.readProject(uri, temporary_zip, QgsReadWriteContext())
    temporary_zip.close()

    doc = read_from_file(str(project_file))
    return doc, str(project_file)


def downloadError(errorMessages):
    for err in errorMessages:
        QgsMessageLog.logMessage(
            "Download error. " + str(err), "Layers menu from project", notifyUser=True
        )


@lru_cache()
def read_from_http(uri: str, download_folder: Path):
    """Read a QGIS project stored into on a remote web server accessible through HTTP.

    :param uri: web URL to the QGIS project
    :type uri: str

    :return: a tuple with XML document and the filepath.
    :rtype: Tuple[QtXml.QDomDocument, str]
    """
    # get filename from URL parts
    parsed = urlparse(uri)
    if not parsed.path.rpartition("/")[2].endswith((".qgs", ".qgz")):
        raise ValueError(
            "URI doesn't ends with QGIS project extension (.qgs or .qgz): {}".format(
                uri
            )
        )
    cached_filepath = download_folder / parsed.path.rpartition("/")[2]

    # download it
    loop = QEventLoop()
    project_download = QgsFileDownloader(
        url=QUrl(uri), outputFileName=str(cached_filepath), delayStart=True
    )
    project_download.downloadExited.connect(loop.quit)
    project_download.downloadError.connect(downloadError)
    project_download.startDownload()
    loop.exec()

    return read_from_file(str(cached_filepath)), str(cached_filepath)


class QgsDomManager:
    """Manager to access qgs xml document for different type of uri:
    - file
    - postgres
    - url
    Read xml document are stored in a dict.
    """

    def __init__(self, project: Optional[Dict[str, str]] = None) -> None:
        self.docs = dict()
        self.project_registry = QgsApplication.projectStorageRegistry()
        self.project = project
        self.cache_manager = CacheManager(iface)

    # TODO: until a log manager is implemented
    @staticmethod
    def log(message, application=__title__, indent=0):
        indent_chars = " .. " * indent
        QgsMessageLog.logMessage(
            f"{indent_chars}{message}", application, notifyUser=True
        )

    def cache_clear(self) -> None:
        """Clear cache of QtXml.QDomDocument for uri"""
        self.docs = dict()

    def set_project(self, project: Optional[Project]) -> None:
        """Define project used to check cache in project cache directory

        :param project: project information
        :type project: Optional[Project]
        """
        self.project = project

    def check_if_project_valid(self, project: Project) -> bool:
        """Check if project is valid by getting qgs xml doc

        :param project: project to check
        :type project: Project
        :return: True if project is valid, False otherwise
        :rtype: bool
        """
        valid = False
        try:
            doc, _ = self.getQgsDoc(project.file)
            valid = not doc.isNull()
        except Exception as err:
            self.log(
                "Error during project reading file '{}': {}".format(project.file, err)
            )
        return valid

    def _get_download_folder(self) -> Path:
        """Get download folder for url and postgres uri
        If a project was defined, project cache download dir is used

        :return: path to download folder
        :rtype: Path
        """
        if self.project:
            return self.cache_manager.get_project_download_dir(self.project)
        return cache_folder

    def getQgsDoc(self, uri: str) -> Tuple[QtXml.QDomDocument, str]:
        """Return the XML document and the path from an URI.

        The URI can be a filepath or stored in database.

        :param uri: The URI to fetch.
        :type uri: str

        :return: Tuple with XML document and the filepath.
        :rtype: (QDomDocument, str)
        """
        # determine storage type: file, database or http
        qgs_storage_type = guess_type_from_uri(uri)

        # check if docs is already here
        if uri in self.docs:
            return self.docs[uri], uri

        if qgs_storage_type == "file":
            doc = read_from_file(uri)
            project_path = uri
        elif qgs_storage_type == "database":
            doc, project_path = read_from_database(
                uri, self.project_registry, self._get_download_folder()
            )
        elif qgs_storage_type == "http":
            doc, project_path = read_from_http(uri, self._get_download_folder())
        else:
            QgsMessageLog.logMessage(
                f"Unrecognized project type: {uri}", __title__, notifyUser=True
            )

        # store doc into the plugin registry
        self.docs[uri] = doc

        return doc, project_path

    def getMapLayerDomFromQgs(
        self, fileName: str, layerId: str
    ) -> Optional[QtXml.QDomNode]:
        """Return the maplayer node in a project filepath given a maplayer ID.

        :param fileName: The project filepath on the filesystem.
        :type fileName: basestring

        :param layerId: The layer ID to look for in the project.
        :type layerId: basestring

        :return: The XML node of the layer.
        :rtype: QDomNode
        """
        doc, _ = self.getQgsDoc(fileName)
        return getFirstChildByTagNameValue(
            doc.documentElement(), "maplayer", "id", layerId
        )
