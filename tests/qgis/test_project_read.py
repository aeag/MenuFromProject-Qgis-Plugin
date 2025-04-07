"""
Usage from the repo root folder:

.. code-block:: bash

    # for whole tests
    python -m unittest tests.qgis.test_project_read
    # for specific test
    python -m unittest tests.qgis.test_project_read.TestProjectMenuConfig.test_get_project_menu_config
"""

# standard library

from pathlib import Path

from qgis.core import QgsMapLayerType, QgsWkbTypes

# PyQGIS
from qgis.testing import unittest

from menu_from_project.datamodel.project import Project
from menu_from_project.datamodel.project_config import (
    MenuGroupConfig,
    MenuLayerConfig,
    MenuProjectConfig,
)
from menu_from_project.logic.project_read import get_project_menu_config
from menu_from_project.logic.qgs_manager import QgsDomManager

# ############################################################################
# ########## Classes #############
# ################################


class TestProjectMenuConfig(unittest.TestCase):
    def test_get_project_menu_config(self):
        """Read a sample project and check returned informations"""

        qgs_dom_manager = QgsDomManager()
        filename = str(Path(__file__).parent / ".." / "projects" / "aeag-tiny.qgz")

        project = Project(
            name="test_import",
            location="layer",
            file=filename,
            type_storage="file",
            id="unique_id",
        )

        result = get_project_menu_config(
            project=project, qgs_dom_manager=qgs_dom_manager
        )

        expected = MenuProjectConfig(
            project_name=project.name,
            filename=filename,
            uri=project.file,
            root_group=MenuGroupConfig(
                name="",
                filename=filename,
                childs=[
                    MenuLayerConfig(
                        name="Sites de mesure qualit\u00e9 (cours d'eau)",
                        layer_id="L8150cde67501427eade1e787479c2f70",
                        filename=filename,
                        visible=True,
                        expanded=True,
                        embedded=False,
                        is_spatial=True,
                        layer_type=QgsMapLayerType.VectorLayer,
                        metadata_abstract="La couche 'Stations de mesure de la qualit\u00e9 des cours d'eau' localise l'ensemble des stations appartenant \u00e0 des r\u00e9seaux de mesure de la qualit\u00e9 des eaux de surface : r\u00e9seaux nationaux (ie. RNB, RCB, R\u00e9seau Hydrobiologique et Piscicole), mais aussi r\u00e9seaux d\u00e9partementaux et locaux.",
                        metadata_title="Stations de mesure qualit\u00e9 (cours d'eau)",
                        layer_notes='<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">\n<html><head><meta name="qrichtext" content="1" /><style type="text/css">\np, li { white-space: pre-wrap; }\n</style></head><body style=" font-family:\'MS Shell Dlg 2\'; font-size:10pt; font-weight:400; font-style:normal;">\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">La couche \'Stations de mesure de la qualit\u00e9 des cours d\'eau\' localise l\'ensemble des stations appartenant \u00e0 des r\u00e9seaux de mesure de la qualit\u00e9 des eaux de surface : r\u00e9seaux nationaux (ie. RNB, RCB, R\u00e9seau Hydrobiologique et Piscicole), mais aussi r\u00e9seaux d\u00e9partementaux et locaux.</p>\n<p align="center" style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><img src="data:image/20425.JPG;base64,/\n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" width="51" height="45" /></p></body></html>',
                        abstract="La couche 'Stations de mesure de la qualit\u00e9 des cours d'eau' localise l'ensemble des stations appartenant \u00e0 des r\u00e9seaux de mesure de la qualit\u00e9 des eaux de surface : r\u00e9seaux nationaux (ie. RNB, RCB, R\u00e9seau Hydrobiologique et Piscicole), mais aussi r\u00e9seaux d\u00e9partementaux et locaux.",
                        title="Stations de mesure qualit\u00e9 (cours d'eau)",
                        geometry_type=QgsWkbTypes.GeometryType.PointGeometry,
                        format="WFS",
                    ),
                    MenuLayerConfig(
                        name="Cours d'eau",
                        layer_id="L35ecffe715c74f15bec52340aa3c9e3f",
                        filename=filename,
                        visible=True,
                        expanded=False,
                        embedded=False,
                        is_spatial=True,
                        layer_type=QgsMapLayerType.RasterLayer,
                        metadata_abstract="BD Carthage est la base de donn\u00e9e qui constitue le r\u00e9f\u00e9rentiel hydrographique fran\u00e7ais. C'est cette base qui d\u00e9crit, codifie et normalise les cours d'eau, les bassins versants, lacs et autres entit\u00e9s hydrographiques de surface en France. Les mises \u00e0 jour sont annuelles, centralis\u00e9es par chaque agence de l'eau, et confi\u00e9es \u00e0 l'IGN pour int\u00e9gration. ",
                        metadata_title="Cours d'eau (BD Carthage)",
                        layer_notes="",
                        abstract="",
                        title="",
                        geometry_type=None,
                        format="wms",
                    ),
                    MenuLayerConfig(
                        name="Bassin Hydrographique",
                        layer_id="Lbd28399787e349488c2f7bb0298b370d",
                        filename=filename,
                        visible=True,
                        expanded=False,
                        embedded=False,
                        is_spatial=True,
                        layer_type=QgsMapLayerType.RasterLayer,
                        metadata_abstract="BD Carthage est la base de donn\u00e9e qui constitue le r\u00e9f\u00e9rentiel hydrographique fran\u00e7ais. C'est cette base qui d\u00e9crit, codifie et normalise les cours d'eau, les bassins versants, lacs et autres entit\u00e9s hydrographiques de surface en France. Les mises \u00e0 jour sont annuelles, centralis\u00e9es par chaque agence de l'eau, et confi\u00e9es \u00e0 l'IGN pour int\u00e9gration. ",
                        metadata_title="Bassin hydrographique (BD Carthage)",
                        layer_notes="",
                        abstract="",
                        title="",
                        geometry_type=None,
                        format="wms",
                    ),
                ],
                embedded=False,
            ),
        )

        self.assertEqual(result, expected)


# ############################################################################
# ####### Stand-alone run ########
# ################################
if __name__ == "__main__":
    unittest.main()
