#! python3  # noqa: E265

"""
    Dialog for setting up the plugin.
"""

# Standard library
import uuid
from functools import partial

# PyQGIS
from qgis.core import QgsApplication, QgsMessageLog
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QHeaderView, QMenu

# project
from menu_from_project.__about__ import DIR_PLUGIN_ROOT, __title__, __version__
from menu_from_project.datamodel.project import Project
from menu_from_project.toolbelt.preferences import (
    SOURCE_MD_LAYER,
    SOURCE_MD_NOTE,
    SOURCE_MD_OGC,
    PlgOptionsManager,
)
from menu_from_project.ui.project_list_model import ProjectListModel

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

        self.plg_settings = PlgOptionsManager()

        self.defaultcursor = self.cursor
        self.setWindowTitle(
            self.windowTitle() + " - {} v{}".format(__title__, __version__)
        )
        self.setWindowIcon(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/gear.svg")),
        )

        settings = self.plg_settings.get_plg_settings()
        self.buttonBox.accepted.connect(self.onAccepted)
        self.btnDelete.clicked.connect(self.onDelete)
        self.btnDelete.setText(None)
        self.btnDelete.setIcon(
            QIcon(QgsApplication.iconPath("mActionDeleteSelected.svg"))
        )
        self.btnUp.clicked.connect(self.onMoveUp)
        self.btnUp.setText(None)
        self.btnUp.setIcon(QIcon(QgsApplication.iconPath("mActionArrowUp.svg")))
        self.btnDown.clicked.connect(self.onMoveDown)
        self.btnDown.setText(None)
        self.btnDown.setIcon(QIcon(QgsApplication.iconPath("mActionArrowDown.svg")))

        # add button
        self.btnAdd.setIcon(QIcon(QgsApplication.iconPath("mActionAdd.svg")))
        self.addMenu = QMenu(self.btnAdd)
        add_option_file = QAction(
            QIcon(QgsApplication.iconPath("mIconFile.svg")),
            self.tr("Add from file"),
            self.addMenu,
        )
        add_option_pgdb = QAction(
            QIcon(QgsApplication.iconPath("mIconPostgis.svg")),
            self.tr("Add from PostgreSQL database"),
            self.addMenu,
        )
        add_option_http = QAction(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/globe.svg")),
            self.tr("Add from URL"),
            self.addMenu,
        )
        add_option_file.triggered.connect(partial(self.onAdd, "file"))
        add_option_http.triggered.connect(partial(self.onAdd, "http"))
        add_option_pgdb.triggered.connect(partial(self.onAdd, "database"))
        self.addMenu.addAction(add_option_file)
        self.addMenu.addAction(add_option_pgdb)
        self.addMenu.addAction(add_option_http)
        self.btnAdd.setMenu(self.addMenu)

        # -- Options
        self.cbxLoadAll.setChecked(settings.optionLoadAll)
        self.cbxLoadAll.setTristate(False)

        self.cbxCreateGroup.setChecked(settings.optionCreateGroup)
        self.cbxCreateGroup.setTristate(False)

        self.cbxShowTooltip.setChecked(settings.optionTooltip)
        self.cbxShowTooltip.setTristate(False)

        self.cbxOpenLinks.setChecked(settings.optionOpenLinks)
        self.cbxOpenLinks.setTristate(False)

        self.sourcesMdText = {
            SOURCE_MD_OGC: self.tr("QGIS Server metadata"),
            SOURCE_MD_LAYER: self.tr("Layer Metadata"),
            SOURCE_MD_NOTE: self.tr("Layer Notes"),
        }
        self.optionSourceMD = settings.optionSourceMD

        self.projetListModel = ProjectListModel(self)
        self.projetListModel.set_project_list(settings.projects)
        self.projectTableView.setModel(self.projetListModel)

        self.projectTableView.selectionModel().selectionChanged.connect(
            self._selected_project_changed
        )
        self.projectTableView.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        self.projectWidget.projectChanged.connect(self._project_changed)
        if len(settings.projects) != 0:
            self.projectTableView.selectRow(0)

    def _selected_project_changed(self) -> None:
        """Update displayed project"""
        selected_index = self.projectTableView.selectionModel().selectedRows()
        if selected_index:
            row = selected_index[0].row()
            project = self.projetListModel.data(
                self.projetListModel.index(row, ProjectListModel.NAME_COL),
                Qt.UserRole,
            )
            self.projectWidget.set_project(project)
            self.projectWidget.enable_merge_option(row != 0)

    def setSourceMdText(self):
        self.mdSource1.setText(self.sourcesMdText[self.optionSourceMD[0]])
        self.mdSource2.setText(self.sourcesMdText[self.optionSourceMD[1]])
        self.mdSource3.setText(self.sourcesMdText[self.optionSourceMD[2]])

    def onAccepted(self):
        settings = self.plg_settings.get_plg_settings()
        settings.projects = []
        for project in self.projetListModel.get_project_list():
            # Only get project with file defined
            if project.file:
                settings.projects.append(project)

        settings.optionTooltip = self.cbxShowTooltip.isChecked()
        settings.optionLoadAll = self.cbxLoadAll.isChecked()
        settings.optionCreateGroup = self.cbxCreateGroup.isChecked()
        settings.optionOpenLinks = self.cbxOpenLinks.isChecked()

        settings.optionSourceMD = self.optionSourceMD

        PlgOptionsManager().save_from_object(settings)

    def onAdd(self, qgs_type_storage: str = "file"):
        """Add a new line to the table.

        :param qgs_type_storage: project storage type, defaults to "file"
        :type qgs_type_storage: str, optional
        """
        project = Project(
            id=str(uuid.uuid4()),
            name="",
            location="new",
            type_storage=qgs_type_storage,
            file="",
        )
        self.projetListModel.insert_project(project)
        self.projectTableView.selectRow(self.projetListModel.rowCount() - 1)
        self.projectTableView.scrollToBottom()

    @staticmethod
    def log(message, application=__title__, indent=0):
        indent_chars = " .. " * indent
        QgsMessageLog.logMessage(
            f"{indent_chars}{message}", application, notifyUser=True
        )

    def onDelete(self):
        """Remove selected lines from the table."""
        selected_index = self.projectTableView.selectionModel().selectedRows()
        if len(selected_index) > 0:
            r = selected_index[0].row()
            self.projetListModel.removeRows(r, 1)

    def onMoveUp(self):
        """Move the selected lines upwards."""
        selected_index = self.projectTableView.selectionModel().selectedRows()
        if len(selected_index) > 0:
            r = selected_index[0].row()
            if r > 0:
                project_a = self.projetListModel.get_row_project(r - 1)
                project_b = self.projetListModel.get_row_project(r)

                if project_b.location == "merge" and r == 1:
                    project_b.location = "new"

                self.projetListModel.set_row_project(r - 1, project_b)
                self.projetListModel.set_row_project(r, project_a)
                self.projectTableView.selectRow(r - 1)

    def onMoveDown(self):
        """Move the selected lines down."""
        selected_index = self.projectTableView.selectionModel().selectedRows()
        if len(selected_index) > 0:
            r = selected_index[0].row()
            nbRows = self.projetListModel.rowCount()
            if r < nbRows - 1:
                project_a = self.projetListModel.get_row_project(r)
                project_b = self.projetListModel.get_row_project(r + 1)

                if project_b.location == "merge" and r == 0:
                    project_b.location = "new"

                self.projetListModel.set_row_project(r, project_b)
                self.projetListModel.set_row_project(r + 1, project_a)
                self.projectTableView.selectRow(r + 1)

    def on_mdSource2_released(self):
        myorder = [1, 0, 2]
        self.optionSourceMD = [self.optionSourceMD[i] for i in myorder]
        self.setSourceMdText()

    def on_mdSource3_released(self):
        myorder = [2, 0, 1]
        self.optionSourceMD = [self.optionSourceMD[i] for i in myorder]
        self.setSourceMdText()

    def _project_changed(self) -> None:
        """Update model when displayed project has changed"""
        selected_index = self.projectTableView.selectionModel().selectedRows()
        if len(selected_index) > 0:
            project = self.projectWidget.get_project()
            self.projetListModel.set_row_project(selected_index[0].row(), project)
