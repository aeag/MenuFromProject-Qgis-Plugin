# Standard library
import os
import re
from typing import Dict, List, Optional, Tuple

from qgis.core import (
    QgsApplication,
    QgsLayerTreeGroup,
    QgsMapLayer,
    QgsMessageLog,
    QgsProject,
    QgsRasterLayer,
    QgsReadWriteContext,
    QgsRelation,
    QgsVectorLayer,
    QgsVectorTileLayer,
)
from qgis.PyQt import QtXml
from qgis.PyQt.QtCore import QCoreApplication, QFileInfo, Qt, QUuid
from qgis.utils import iface, plugins

# project
from menu_from_project.__about__ import __title__
from menu_from_project.datamodel.project_config import MenuLayerConfig
from menu_from_project.logic.project_read import define_name_and_version_from_layer_name
from menu_from_project.logic.qgs_manager import (
    QgsDomManager,
    is_absolute,
    project_trusted,
)
from menu_from_project.logic.xml_utils import getFirstChildByTagNameValue

# PyQGIS
from menu_from_project.toolbelt.preferences import PlgOptionsManager


class LayerLoad:

    def __init__(self) -> None:
        self.canvas = iface.mapCanvas()
        self.plg_settings = PlgOptionsManager()
        self.qgs_dom_manager = QgsDomManager()
        self.mapLayerIds = {}

    # TODO: until a log manager is implemented
    @staticmethod
    def log(message, application=__title__, indent=0):
        indent_chars = " .. " * indent
        QgsMessageLog.logMessage(
            f"{indent_chars}{message}", application, notifyUser=True
        )

    @staticmethod
    def tr(message):
        return QCoreApplication.translate("MenuFromProject", message)

    def addLayer(
        self,
        uri: str,
        doc: QtXml.QDomDocument,
        layerId: str,
        group: Optional[QgsLayerTreeGroup] = None,
        visible: bool = False,
        expanded: bool = False,
        parentsLoop: Dict[str, str] = {},
        loop: int = 0,
    ) -> Tuple[Optional[QgsMapLayer], Optional[List[Dict[str, str]]]]:
        """Add layer to current QgsProject.

         Parse Qgis xml document to get layer information and add to QgsProject.
         If layer has any relations and link layer option is enabled, a list of relation dict is defined

        :param uri: path to QgsProject file. Needed for relative project path resolve
        :type uri: str
        :param doc: The QGIS project as XML document.
        :type doc: QtXml.QDomDocument
        :param layerId: id of layer (from XML document)
        :type layerId: str
        :param group: layer tree group where the layer must be added, defaults to None
        :type group: Optional[QgsLayerTreeGroup], optional
        :param visible: layer visibility in layer tree, defaults to False
        :type visible: bool, optional
        :param expanded: layer expanded state in layer tree, defaults to False
        :type expanded: bool, optional
        :param parentsLoop: dict of layer id for built relation, needed to avoid multiple creation of relations, defaults to {}
        :type parentsLoop: Dict[str, str], optional
        :param loop: integer to have indent when displaying log in case of relation build errors, defaults to 0
        :type loop: int, optional
        :return: created QgsMapLayer, list of relation dict
        :rtype: Tuple[Optional[QgsMapLayer], Optional[List[Dict[str, str]]]]
        """
        theLayer = None

        settings = self.plg_settings.get_plg_settings()

        # is project in relative path ?
        absolute = is_absolute(doc)
        trusted = project_trusted(doc)

        node = getFirstChildByTagNameValue(
            doc.documentElement(), "maplayer", "id", layerId
        )
        if node:
            node = node.cloneNode()

            idNode = node.namedItem("id")
            layerType = node.toElement().attribute("type", "vector")
            # give it a new id (for multiple import)
            newLayerId = "L%s" % re.sub("[{}-]", "", QUuid.createUuid().toString())
            self.mapLayerIds[newLayerId] = layerId

            try:
                idNode.firstChild().toText().setData(newLayerId)
            except Exception:
                pass

            # Update name node to remove syntaxic type on name
            nameNode = node.namedItem("layername")
            name, version = define_name_and_version_from_layer_name(
                nameNode.firstChild().toText().data()
            )
            name = f"{name} {version}" if version else name
            nameNode.firstChild().toText().setData(name)

            # if relative path, adapt datasource
            if not absolute:
                try:
                    datasourceNode = node.namedItem("datasource")
                    ds = datasourceNode.firstChild().toText().data()
                    providerNode = node.namedItem("provider")
                    provider = providerNode.firstChild().toText().data()

                    if provider in ["ogr", "gdal"] and (ds.find(".") == 0):
                        projectpath = QFileInfo(uri).path()
                        newlayerpath = projectpath + "/" + ds
                        datasourceNode.firstChild().toText().setData(newlayerpath)
                except Exception:
                    pass

            # is relations exists ?
            relationsToBuild = []
            if settings.optionOpenLinks:
                relationsToBuild = self.buildRelations(
                    uri, doc, layerId, newLayerId, group, parentsLoop, loop
                )

            # read modified layer node
            newLayer = None
            if settings.optionCreateGroup and group is not None:
                if layerType == "raster":
                    theLayer = QgsRasterLayer()
                elif layerType == "vector-tile":
                    theLayer = QgsVectorTileLayer()
                else:
                    theLayer = QgsVectorLayer()
                    theLayer.setReadExtentFromXml(trusted)

                theLayer.readLayerXml(node.toElement(), QgsReadWriteContext())

                # Special process if the plugin "DB Style Manager" is installed
                flag = "use_db_style_manager_in_custom_menu" in os.environ
                if flag and "db-style-manager" in plugins:
                    try:
                        plugins["db-style-manager"].load_style_from_database(theLayer)
                    except Exception:
                        self.log(
                            "DB-Style-Manager failed to load the style.",
                            indent=loop,
                        )

                # needed
                newLayer = QgsProject.instance().addMapLayer(theLayer, False)
                if newLayer is not None:
                    # add to group
                    treeNode = group.insertLayer(0, newLayer)
                    treeNode.setExpanded(expanded)
                    treeNode.setItemVisibilityChecked(visible)
            else:
                # create layer
                ok = QgsProject.instance().readLayer(node)
                if ok:
                    newLayer = QgsProject.instance().mapLayer(newLayerId)

            return newLayer, relationsToBuild

        else:
            self.log(
                "Layer {} not found. Can't add layer to QGIS.".format(layerId),
                indent=loop,
            )

        return None, None

    def getRelations(self, doc: QtXml.QDomDocument) -> List[Dict[str, str]]:
        """Load available relation from a QgsProject xml document.
        These informations are used to create QgsRelation in project after layer load

        <relations>
            <relation strength="Association" referencedLayer="layerid" id="refid" name="fk_region" referencingLayer="layerid">
                <fieldRef referencedField="insee_region" referencingField="insee_region"/>
            </relation>
        </relations>

        :param doc: The QGIS project as XML document.
        :type doc: QtXml.QDomDocument
        :return: list of all available relation dict
        :rtype: List[Dict[str, str]]
        """
        relations = []
        try:
            nodes = doc.elementsByTagName("relations")
            relsNode = nodes.at(0)

            relNodes = relsNode.toElement().elementsByTagName("relation")
            for relNode in (relNodes.at(i) for i in range(relNodes.size())):
                fieldNodes = relNode.toElement().elementsByTagName("fieldRef")
                fieldNode = fieldNodes.at(0)

                if fieldNode:
                    relation = {}
                    for attr in [
                        "strength",
                        "referencedLayer",
                        "id",
                        "name",
                        "referencingLayer",
                    ]:
                        relation[attr] = relNode.toElement().attribute(attr)

                    for attr in [
                        "referencedField",
                        "referencingField",
                    ]:
                        relation[attr] = fieldNode.toElement().attribute(attr)

                    if relation["referencedLayer"] != "":
                        relations.append(relation)
        except Exception as e:
            for m in e.args:
                self.log(m)

        return relations

    def getRelationsForLayer(
        self,
        relations: List[Dict[str, str]],
        source: Optional[str] = None,
        target: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Return relations dict list filtered from referencedLayer and/or referencingLayer.

        :param relations: input relations dict list
        :type relations: List[Dict[str, str]]
        :param source: layer id for referencedLayer, defaults to None
        :type source: Optional[str], optional
        :param target: layer id for referencingLayer, defaults to None
        :type target: Optional[str], optional
        :return: _description_
        :rtype: List[Dict[str, str]]
        """

        r = []
        try:
            for relation in relations:
                if source is not None and source == relation["referencedLayer"]:
                    r.append(relation)

                if target is not None and target == relation["referencingLayer"]:
                    r.append(relation)
        except Exception as e:
            for m in e.args:
                self.log(m)

        return r

    def fixForm(
        self,
        doc: QtXml.QDomDocument,
        newLayerId: str,
        oldRelationId: str,
        newRelationId: str,
    ) -> None:
        """Rebuilds the form when relations are defined in it

        Principle: reading the source XML document, updating identifiers, updating editFormConfig

        :param doc: The QGIS project as XML document.
        :type doc: QtXml.QDomDocument
        :param newLayerId: id of created new layer
        :type newLayerId: str
        :param oldRelationId: id of old relation
        :type oldRelationId: str
        :param newRelationId: id of new relation
        :type newRelationId: str
        """
        theLayer = QgsProject.instance().mapLayer(newLayerId)
        oldLayerId = self.mapLayerIds[newLayerId]

        layerNode = getFirstChildByTagNameValue(
            doc.documentElement(), "maplayer", "id", oldLayerId
        )
        if not layerNode:
            self.log("{} not found for form relation fix".format(oldLayerId))

        nodes = layerNode.toElement().elementsByTagName("attributeEditorForm")
        if nodes.count() == 0:
            return
        aefNode = nodes.at(0)

        nodes = aefNode.toElement().elementsByTagName("attributeEditorRelation")
        for nodeIdx in range(nodes.length()):
            aerNode = nodes.at(nodeIdx)
            rid = aerNode.toElement().attribute("relation")
            if rid == oldRelationId:
                aerNode.toElement().setAttribute("relation", newRelationId)

                nodes = aefNode.toElement().elementsByTagName("widgets")
                widgets = nodes.at(0)
                widgets.toElement().setAttribute("name", newRelationId)

                editFormConfig = theLayer.editFormConfig()
                rootContainer = editFormConfig.invisibleRootContainer()
                rootContainer.clear()
                editFormConfig.clearTabs()
                editFormConfig.readXml(layerNode, QgsReadWriteContext())
                theLayer.setEditFormConfig(editFormConfig)

    def buildProjectRelation(
        self, doc: QtXml.QDomDocument, relDict: Dict[str, str]
    ) -> None:
        """Build project relation and add it to QgsProject

        :param doc: The QGIS project as XML document.
        :type doc: QtXml.QDomDocument
        :param relDict: relation dictionnary
        :type relDict: Dict[str, str]
        """

        try:
            REL_STRENGTH = {
                "Association": QgsRelation.RelationStrength.Association,
                "Composition": QgsRelation.RelationStrength.Composition,
            }
            relMan = QgsProject.instance().relationManager()

            rel = QgsRelation()
            rel.addFieldPair(relDict["referencingField"], relDict["referencedField"])
            oldRelationId = relDict["id"]
            newRelationId = "R%s" % re.sub("[{}-]", "", QUuid.createUuid().toString())
            rel.setId(newRelationId)
            rel.setName(relDict["name"])
            rel.setReferencedLayer(relDict["referencedLayer"])
            rel.setReferencingLayer(relDict["referencingLayer"])
            rel.setStrength(REL_STRENGTH[relDict["strength"]])
            rel.updateRelationStatus()

            if rel.isValid():
                relMan.addRelation(rel)

                # Adapter le formulaire de la couche referencedLayer
                try:
                    self.fixForm(
                        doc,
                        relDict["referencedLayer"],
                        oldRelationId,
                        newRelationId,
                    )
                except Exception:
                    self.log(
                        "Form not fixed for layer {}".format(relDict["referencedLayer"])
                    )

            else:
                self.log(
                    "Invalid relation {} : {}".format(rel.id(), rel.validationError())
                )
        except Exception as e:
            for m in e.args:
                self.log(m)

    def buildRelations(
        self,
        uri: str,
        doc: QtXml.QDomDocument,
        oldLayerId: str,
        newLayerId: str,
        group: Optional[QgsLayerTreeGroup],
        parentsLoop: Dict[str, str],
        loop: int,
    ) -> List[Dict[str, str]]:
        """Identify the relations to be created (later, after source layer creation)

        Based on those of the source project, adapted to the new identifiers of the layers

        :param uri: path to QgsProject file. Needed for relative project path resolve
        :type uri: str
        :param doc:  The QGIS project as XML document.
        :type doc: QtXml.QDomDocument
        :param oldLayerId: id of layer from XML document
        :type oldLayerId: str
        :param newLayerId: id of created layer
        :type newLayerId: str
        :param group: layer tree group where the layer must be added
        :type group: Optional[QgsLayerTreeGroup]
        :param parentsLoop: dict of layer id for built relation, needed to avoid multiple creation of relations
        :type parentsLoop: Dict[str, str]
        :param loop: integer to have indent when displaying log in case of relation build errors
        :type loop: int
        :return: list of relation dict to create
        :rtype: List[Dict[str, str]]
        """
        relationsToBuild, targetRelations = [], []

        relations = self.getRelations(doc)
        relsTarget = self.getRelationsForLayer(relations, source=oldLayerId)
        # relsSource = self.getRelationsForLayer(relations, target=oldLayerId)

        if len(relsTarget) > 0:
            for relDict in relsTarget:
                if relDict["referencingLayer"] in parentsLoop:
                    # La couche cible a déjà été ajoutée (boucle infinie)
                    # on se contente de référencer celle-ci
                    relDict["referencedLayer"] = newLayerId
                    relDict["referencingLayer"] = parentsLoop[
                        relDict["referencingLayer"]
                    ]
                    relationsToBuild.append(relDict)
                else:
                    # la couche cible n'a pas été ajoutée
                    parentsLoop.update({oldLayerId: newLayerId})

                    targetLayer, targetRelations = self.addLayer(
                        uri,
                        doc,
                        relDict["referencingLayer"],
                        group,
                        False,
                        False,
                        parentsLoop,
                        loop + 1,
                    )
                    if targetLayer is not None:
                        relDict["referencedLayer"] = newLayerId
                        relDict["referencingLayer"] = targetLayer.id()
                        relationsToBuild.append(relDict)

        return targetRelations + relationsToBuild

    def load_layer_list(
        self, layer_config_list: List[MenuLayerConfig], group_name: str
    ) -> None:
        """Load a list of layer to current QgsProject

        :param layer_config_list: menu layer configuration list
        :type layer_config_list: List[MenuLayerConfig]
        :param group_name: group name in case of create group option
        :type group_name: str
        """
        for layer_config in layer_config_list:
            self.load_layer(layer_config=layer_config, group_name=group_name)

    def load_layer(self, layer_config: MenuLayerConfig, group_name: str) -> None:
        """Load layer to current QgsProject

        :param layer_config: configuration of layer to load
        :type layer_config: MenuLayerConfig
        :param group_name: group name in case of create group option
        :type group_name: str
        """
        self.canvas.freeze(True)
        self.canvas.setRenderFlag(False)
        group = None
        QgsApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.mapLayerIds = {}

        settings = self.plg_settings.get_plg_settings()

        try:
            if settings.optionCreateGroup:
                group = QgsProject.instance().layerTreeRoot().findGroup(group_name)
                if group is None:
                    group = (
                        QgsProject.instance().layerTreeRoot().insertGroup(0, group_name)
                    )
            doc, _ = self.qgs_dom_manager.getQgsDoc(layer_config.filename)

            # Loading layer
            layer, relationsToBuild = self.addLayer(
                layer_config.filename,
                doc,
                layer_config.layer_id,
                group,
                layer_config.visible,
                layer_config.expanded,
                {},
                0,
            )
            for relDict in relationsToBuild:
                self.buildProjectRelation(doc, relDict)

            # is joined layers exists ?
            if settings.optionOpenLinks and layer and isinstance(layer, QgsVectorLayer):
                for j in layer.vectorJoins():
                    try:
                        joinLayer, joinRelations = self.addLayer(
                            layer_config.filename, doc, j.joinLayerId(), group
                        )
                        for relDict in joinRelations:
                            self.buildProjectRelation(doc, relDict)

                        if joinLayer:
                            j.setJoinLayerId(joinLayer.id())
                            j.setJoinLayer(joinLayer)
                            layer.addJoin(j)
                    except Exception:
                        self.log("Joined layer {} not added.".format(j.joinLayerId()))
                        pass
        except Exception as e:
            # fixme fileName is not defined
            # self.log(
            #     'Menu from layer: Invalid ' + (fileName if fileName is not None else ""))
            for m in e.args:
                self.log(m)

        finally:
            self.canvas.freeze(False)
            self.canvas.setRenderFlag(True)
            self.canvas.refresh()
            QgsApplication.restoreOverrideCursor()
