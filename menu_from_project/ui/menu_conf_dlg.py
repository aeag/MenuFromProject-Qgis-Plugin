#! python3  # noqa: E265

"""
    Dialog for setting up the plugin.
"""

# Standard library

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

# project
from menu_from_project.__about__ import DIR_PLUGIN_ROOT

# ############################################################################
# ########## Globals ###############
# ##################################


# load ui
FORM_CLASS, _ = uic.loadUiType(DIR_PLUGIN_ROOT / "ui/conf_dialog.ui")

# ############################################################################
# ########## Classes ###############
# ##################################


class MenuConfDialog(QDialog, FORM_CLASS):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setupUi(self)

    def onAccepted(self):
        self.wdg_config.apply()
