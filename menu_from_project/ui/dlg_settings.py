#! python3  # noqa: E265

"""
Dialog for setting up the plugin.
"""

# Standard library

# PyQGIS
from functools import partial

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

# project
from menu_from_project.__about__ import (
    DIR_PLUGIN_ROOT,
    __icon_path__,
    __title__,
    __uri_homepage__,
    __version__,
)

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
        self.setWindowTitle(
            self.windowTitle() + " - {} v{}".format(__title__, __version__)
        )
        self.setWindowIcon(
            QIcon(f"{__icon_path__.resolve()}"),
        )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self.wdg_config.apply
        )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Help).clicked.connect(
            partial(
                QDesktopServices.openUrl,
                QUrl(__uri_homepage__),
            )
        )

    def accept(self):
        self.wdg_config.apply()
        super().accept()
