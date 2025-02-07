#! python3  # noqa: E265

"""
    Dialog for setting up the plugin.
"""

# Standard library

# PyQGIS
from functools import partial

from qgis.PyQt import uic
from qgis.PyQt.Qt import QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

# project
from menu_from_project.__about__ import DIR_PLUGIN_ROOT, __uri_homepage__

# ############################################################################
# ########## Globals ###############
# ##################################


# load ui
FORM_CLASS, _ = uic.loadUiType(DIR_PLUGIN_ROOT / "ui/dlg_settings.ui")

# ############################################################################
# ########## Classes ###############
# ##################################


class MenuConfDialog(QDialog, FORM_CLASS):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(
            self.wdg_config.apply
        )

        self.buttonBox.button(QDialogButtonBox.Help).clicked.connect(
            partial(
                QDesktopServices.openUrl,
                QUrl(__uri_homepage__),
            )
        )

    def accept(self):
        self.wdg_config.apply()
        super().accept()
