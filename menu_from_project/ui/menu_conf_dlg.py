#! python3  # noqa: E265

"""
    Dialog for setting up the plugin.
"""

import uuid

# Standard library
from functools import partial

from qgis.core import Qgis, QgsApplication, QgsMessageLog
from qgis.gui import QgsFileWidget, QgsProviderGuiRegistry, QgsSpinBox
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QRect, Qt
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QAction,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QTableWidgetItem,
    QToolButton,
)
from qgis.utils import iface

# project
from menu_from_project.__about__ import DIR_PLUGIN_ROOT, __title__, __version__

# PyQGIS
from menu_from_project.datamodel.project import Project, ProjectCacheConfig
from menu_from_project.logic.cache_manager import CacheManager
from menu_from_project.logic.custom_datatypes import TABLE_COLUMNS_ORDER
from menu_from_project.logic.qgs_manager import QgsDomManager
from menu_from_project.logic.tools import icon_per_storage_type
from menu_from_project.toolbelt.preferences import (
    SOURCE_MD_LAYER,
    SOURCE_MD_NOTE,
    SOURCE_MD_OGC,
    PlgOptionsManager,
)

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
        self.qgs_dom_manager = QgsDomManager()

        self.defaultcursor = self.cursor
        self.setWindowTitle(
            self.windowTitle() + " - {} v{}".format(__title__, __version__)
        )
        self.setWindowIcon(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/gear.svg")),
        )

        # column order reference
        self.cols = TABLE_COLUMNS_ORDER(
            edit=0,
            name=1,
            type_menu_location=3,
            type_storage=2,
            uri=4,
            refresh_days=5,
            enable_cache=6,
            delete_cache=7,
            cache_validation_file=8,
            id=9,
        )

        # menu locations
        self.LOCATIONS = {
            "new": {
                "index": 0,
                "label": QgsApplication.translate("ConfDialog", "New menu", None),
            },
            "layer": {
                "index": 1,
                "label": QgsApplication.translate("ConfDialog", "Add layer menu", None),
            },
            "browser": {
                "index": 2,
                "label": QgsApplication.translate(
                    "ConfDialog", "Add browser menu", None
                ),
            },
            "merge": {
                "index": 3,
                "label": QgsApplication.translate(
                    "ConfDialog", "Merge with previous", None
                ),
            },
        }

        settings = self.plg_settings.get_plg_settings()

        # -- Configured projects (table and related buttons)
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.tableWidget.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft
        )
        self.tableWidget.setRowCount(len(settings.projects))
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

        for idx, project in enumerate(settings.projects):
            self._set_table_widget_row_project(idx, project)

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
            SOURCE_MD_OGC: self.tr("QGis Server metadata"),
            SOURCE_MD_LAYER: self.tr("Layer Metadata"),
            SOURCE_MD_NOTE: self.tr("Layer Notes"),
        }
        self.optionSourceMD = settings.optionSourceMD

        self.tableTunning()

    def _set_table_widget_row_project(self, idx: int, project: Project) -> None:
        """Define table widget content for a specific row for a project

        :param idx: table widget row index
        :type idx: int
        :param project: project
        :type project: Project
        """
        self._set_table_widget_row_item(idx, project.type_storage)

        # project name
        self.tableWidget.cellWidget(idx, self.cols.name).setText(project.name)

        # project menu location
        location_combo = self.tableWidget.cellWidget(idx, self.cols.type_menu_location)
        try:
            location_combo.setCurrentIndex(self.LOCATIONS[project.location]["index"])
        except Exception:
            location_combo.setCurrentIndex(0)

        # project path (guess type stored into data)
        le = self.tableWidget.cellWidget(idx, self.cols.uri)
        le.setText(project.file)
        try:
            le.setStyleSheet("color: {};".format("black" if project.valid else "red"))
        except Exception:
            le.setStyleSheet("color: {};".format("black"))

        # refresh day
        if project.cache_config.refresh_days_period:
            self.tableWidget.cellWidget(idx, self.cols.refresh_days).setValue(
                project.cache_config.refresh_days_period
            )

        # Cache enable
        self.tableWidget.cellWidget(idx, self.cols.enable_cache).setChecked(
            project.cache_config.enable
        )

        # Cache validation file
        self.tableWidget.cellWidget(idx, self.cols.cache_validation_file).setFilePath(
            project.cache_config.cache_validation_uri
        )

        # ID
        self.tableWidget.item(idx, self.cols.id).setText(project.id)

    def setSourceMdText(self):
        self.mdSource1.setText(self.sourcesMdText[self.optionSourceMD[0]])
        self.mdSource2.setText(self.sourcesMdText[self.optionSourceMD[1]])
        self.mdSource3.setText(self.sourcesMdText[self.optionSourceMD[2]])

    def addEditButton(self, row, guess_type):
        """Add edit button, adapted to the type of resource

        :param row: row index.
        :type guess_type: resource type (database, file)

        """
        if guess_type == "file":
            edit_button = self.mk_prj_edit_button()
            self.tableWidget.setCellWidget(row, self.cols.edit, edit_button)
            edit_button.clicked.connect(
                lambda checked, idx=row: self.onFileSearchPressed(row)
            )

        if guess_type == "database":
            edit_button = self.mk_prj_edit_button()
            self.tableWidget.setCellWidget(row, self.cols.edit, edit_button)
            edit_button.clicked.connect(
                lambda checked, idx=row: self.onDbSearchPressed(row)
            )

        if guess_type == "http":
            edit_button = self.mk_prj_edit_button("help")
            self.tableWidget.setCellWidget(row, self.cols.edit, edit_button)
            edit_button.clicked.connect(
                lambda checked, idx=row: self.onHttpSearchPressed(row)
            )

    def onFileSearchPressed(self, row: int):
        """Open file browser to allow user pick a QGIS project file. \
        Trigered when edit button is pressed for a project with type_storage == file.

        :param row: row indice
        :type row: int
        """
        file_widget = self.tableWidget.cellWidget(row, self.cols.uri)

        filePath = QFileDialog.getOpenFileName(
            self,
            QgsApplication.translate(
                "menu_from_project", "Projects configuration", None
            ),
            file_widget.text(),
            QgsApplication.translate(
                "menu_from_project", "QGIS projects (*.qgs *.qgz)", None
            ),
        )

        try:
            if filePath[0]:
                file_widget.setText(filePath[0])

                name_widget = self.tableWidget.cellWidget(row, self.cols.name)
                name = name_widget.text()
                if not name:
                    try:
                        name = filePath[0].split("/")[-1]
                        name = name.split(".")[0]
                    except Exception:
                        name = ""

                    name_widget.setText(name)

        except Exception:
            pass

    def onHttpSearchPressed(self, row: int):
        """no HTTP browser, only help message.

        :param row: row indice
        :type row: int
        """
        iface.messageBar().pushMessage(
            "Message",
            self.tr(
                "No HTTP Browser, simply paste your URL into the 'project' column."
            ),
            level=Qgis.Info,
        )

    def onDbSearchPressed(self, row: int):
        """Open database browser to allow user pick a QGIS project file. \
        Trigered when edit button is pressed for a project with type_storage == database.

        :param row: row indice
        :type row: int
        """
        item = self.tableWidget.item(row, 1)

        pgr = QgsProviderGuiRegistry(QgsApplication.pluginPath())
        pl = pgr.providerList()
        if "postgres" in pgr.providerList():
            psgp = pgr.projectStorageGuiProviders("postgres")
            if len(psgp) > 0:
                uri = psgp[0].showLoadGui()
                try:
                    if uri:
                        file_widget = self.tableWidget.cellWidget(row, self.cols.uri)
                        file_widget.setText(uri)

                        name_widget = self.tableWidget.cellWidget(row, self.cols.name)
                        name = name_widget.text()
                        if not name:
                            try:
                                name = uri.split("project=")[-1]
                                name = name.split(".")[0]
                            except Exception:
                                name = ""

                            name_widget.setText(name)

                except Exception:
                    pass

    def _table_widget_row_project(self, row: int) -> Project:
        """Return project from a table widget row

        :param row: table widget row
        :type row: int
        :return: project in row
        :rtype: Project
        """
        file_widget = self.tableWidget.cellWidget(row, self.cols.uri)
        name_widget = self.tableWidget.cellWidget(row, self.cols.name)
        name = name_widget.text()
        filename = file_widget.text()

        location_widget = self.tableWidget.cellWidget(row, self.cols.type_menu_location)
        location = location_widget.itemData(location_widget.currentIndex())

        cache_config = ProjectCacheConfig(
            refresh_days_period=self.tableWidget.cellWidget(
                row, self.cols.refresh_days
            ).value(),
            enable=self.tableWidget.cellWidget(row, self.cols.enable_cache).isChecked(),
            cache_validation_uri=self.tableWidget.cellWidget(
                row, self.cols.cache_validation_file
            ).filePath(),
        )

        type_storage = self.tableWidget.item(row, self.cols.uri).data(
            Qt.ItemDataRole.UserRole
        )

        return Project(
            file=filename,
            name=name,
            location=location,
            valid=True,
            type_storage=type_storage,
            cache_config=cache_config,
            id=self.tableWidget.item(row, self.cols.id).text(),
        )

    def onAccepted(self):
        settings = self.plg_settings.get_plg_settings()
        settings.projects = []
        for row in range(self.tableWidget.rowCount()):
            project = self._table_widget_row_project(row)
            # Only get project with file defined
            if project.file:
                settings.projects.append(project)

        settings.optionTooltip = self.cbxShowTooltip.isChecked()
        settings.optionLoadAll = self.cbxLoadAll.isChecked()
        settings.optionCreateGroup = self.cbxCreateGroup.isChecked()
        settings.optionOpenLinks = self.cbxOpenLinks.isChecked()

        settings.optionSourceMD = self.optionSourceMD

        PlgOptionsManager().save_from_object(settings)

    def _set_table_widget_row_item(
        self, row: int, qgs_type_storage: str = "file"
    ) -> None:
        """Define widget to use for a row

        :param row: row to define
        :type row: int
        :param qgs_type_storage: type storage for label, defaults to "file"
        :type qgs_type_storage: str, optional
        """
        # edit button
        self.addEditButton(row, qgs_type_storage)

        # project name
        itemName = QTableWidgetItem()
        itemName.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.tableWidget.setItem(row, self.cols.name, itemName)
        name_lineedit = QLineEdit()
        name_lineedit.setPlaceholderText(self.tr("Use project title"))
        self.tableWidget.setCellWidget(row, self.cols.name, name_lineedit)

        # project storage type
        self.tableWidget.setCellWidget(
            row,
            self.cols.type_storage,
            self.mk_prj_storage_icon(qgs_type_storage),
        )

        # menu location
        location_combo = QComboBox()
        for pk in self.LOCATIONS:
            if not (pk == "merge" and row == 0):
                location_combo.addItem(self.LOCATIONS[pk]["label"], pk)

        location_combo.setCurrentIndex(0)
        self.tableWidget.setCellWidget(
            row, self.cols.type_menu_location, location_combo
        )

        # project file path
        itemFile = QTableWidgetItem()
        itemFile.setData(Qt.ItemDataRole.UserRole, qgs_type_storage)
        itemFile.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.tableWidget.setItem(row, self.cols.uri, itemFile)
        filepath_lineedit = QLineEdit()
        filepath_lineedit.textChanged.connect(self.onTextChanged)
        self.tableWidget.setCellWidget(row, self.cols.uri, filepath_lineedit)

        # refresh day
        refresh_day_item = QTableWidgetItem()
        refresh_day_item.setFlags(
            Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        )
        self.tableWidget.setItem(row, self.cols.refresh_days, refresh_day_item)
        spinbox = QgsSpinBox()
        spinbox.setClearValue(-1, self.tr("None"))
        spinbox.setSuffix(self.tr(" days"))
        self.tableWidget.setCellWidget(row, self.cols.refresh_days, spinbox)

        # Cache enable
        enable_cache_item = QTableWidgetItem()
        enable_cache_item.setFlags(
            Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        )
        self.tableWidget.setItem(row, self.cols.enable_cache, enable_cache_item)
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        self.tableWidget.setCellWidget(row, self.cols.enable_cache, checkbox)

        # Cache validation file
        cache_validation_file_item = QTableWidgetItem()
        cache_validation_file_item.setFlags(
            Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        )
        self.tableWidget.setItem(
            row, self.cols.cache_validation_file, cache_validation_file_item
        )
        qgs_file_widget = QgsFileWidget()
        qgs_file_widget.setFilter("*.json")
        self.tableWidget.setCellWidget(
            row, self.cols.cache_validation_file, qgs_file_widget
        )

        # id
        id_item = QTableWidgetItem()
        self.tableWidget.setItem(row, self.cols.id, id_item)

        # delete cache option
        delete_cache_button = QToolButton(self.tableWidget)
        delete_cache_button.setGeometry(QRect(0, 0, 20, 20))
        delete_cache_button.setIcon(
            QIcon(":images/themes/default/console/iconClearConsole.svg")
        )
        delete_cache_button.setToolTip(self.tr("Delete cache for this project"))

        self.tableWidget.setCellWidget(row, self.cols.delete_cache, delete_cache_button)
        delete_cache_button.clicked.connect(
            lambda checked, idx=row: self.on_delete_cache(row)
        )

    def onAdd(self, qgs_type_storage: str = "file"):
        """Add a new line to the table.

        :param qgs_type_storage: project storage type, defaults to "file"
        :type qgs_type_storage: str, optional
        """
        row = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(row + 1)
        self._set_table_widget_row_item(row, qgs_type_storage)

        self.tableWidget.item(row, self.cols.id).setText(str(uuid.uuid4()))

        # apply table styling
        self.tableTunning()

    @staticmethod
    def log(message, application=__title__, indent=0):
        indent_chars = " .. " * indent
        QgsMessageLog.logMessage(
            f"{indent_chars}{message}", application, notifyUser=True
        )

    def onDelete(self):
        """Remove selected lines from the table."""
        sr = self.tableWidget.selectedRanges()
        try:
            self.tableWidget.removeRow(sr[0].topRow())
        except Exception:
            pass

    def onMoveUp(self):
        """Move the selected lines upwards."""
        sr = self.tableWidget.selectedRanges()
        r = sr[0].topRow()
        if r > 0:
            project_a = self._table_widget_row_project(r - 1)
            project_b = self._table_widget_row_project(r)

            if project_b.location == "merge" and r == 1:
                project_b.location = "new"

            self._set_table_widget_row_project(r - 1, project_b)
            self._set_table_widget_row_project(r, project_a)

            # selected row
            self.tableWidget.setCurrentCell(r - 1, 1)

    def onMoveDown(self):
        sr = self.tableWidget.selectedRanges()
        nbRows = self.tableWidget.rowCount()
        r = sr[0].topRow()
        if r < nbRows - 1:
            project_a = self._table_widget_row_project(r)
            project_b = self._table_widget_row_project(r + 1)

            if project_b.location == "merge" and r == 0:
                project_b.location = "new"

            self._set_table_widget_row_project(r, project_b)
            self._set_table_widget_row_project(r + 1, project_a)

            # selected row
            self.tableWidget.setCurrentCell(r + 1, 1)

    def on_delete_cache(self, row: int) -> None:
        project = self._table_widget_row_project(row)
        cache_manager = CacheManager(iface)
        cache_manager.clear_project_cache(project=project)

    def onTextChanged(self, text: str):
        """Read the project using the URI of the project that changed into the table.

        :param text: project path URI
        :type text: str
        """
        file_widget = self.sender()
        try:
            self.qgs_dom_manager.getQgsDoc(text)
            file_widget.setStyleSheet("color: {};".format("black"))
        except Exception as err:
            self.log("Error during project reading: {}".format(err))
            file_widget.setStyleSheet("color: {};".format("red"))

    def on_mdSource2_released(self):
        myorder = [1, 0, 2]
        self.optionSourceMD = [self.optionSourceMD[i] for i in myorder]
        self.setSourceMdText()

    def on_mdSource3_released(self):
        myorder = [2, 0, 1]
        self.optionSourceMD = [self.optionSourceMD[i] for i in myorder]
        self.setSourceMdText()

    def tableTunning(self):
        """Prettify table aspect"""
        # edit button
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            self.cols.edit, QHeaderView.ResizeMode.Fixed
        )
        self.tableWidget.horizontalHeader().resizeSection(self.cols.edit, 20)

        # project name
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            self.cols.name, QHeaderView.ResizeMode.Interactive
        )

        # project type
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            self.cols.type_storage, QHeaderView.ResizeMode.Fixed
        )
        self.tableWidget.horizontalHeader().resizeSection(self.cols.type_storage, 10)

        # project menu location
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            self.cols.type_menu_location, QHeaderView.ResizeMode.Interactive
        )

        # project path
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            self.cols.uri, QHeaderView.ResizeMode.Interactive
        )

        # fit to content
        self.tableWidget.resizeColumnToContents(self.cols.name)
        self.tableWidget.resizeColumnToContents(self.cols.type_menu_location)
        self.tableWidget.resizeColumnToContents(self.cols.uri)
        self.tableWidget.resizeColumnToContents(self.cols.delete_cache)

    # -- Widgets factory ---------------------------------------------------------------
    def mk_prj_edit_button(self, fileName="edit") -> QToolButton:
        """Returns a tool button for the project edition.

        :return: button
        :rtype: QToolButton
        """
        edit_button = QToolButton(self.tableWidget)
        edit_button.setGeometry(QRect(0, 0, 20, 20))
        edit_button.setIcon(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/{}.svg".format(fileName)))
        )
        edit_button.setToolTip(self.tr("Edit this project"))

        return edit_button

    def mk_prj_storage_icon(self, qgs_type_storage: str) -> QLabel:
        """Returns a QLabel with the matching icon for the storage type.

        :param qgs_type_storage: storage type
        :type qgs_type_storage: str
        :return: QLabel to be set in a cellWidget
        :rtype: QLabel
        """
        lbl_location_type = QLabel()
        lbl_location_type.setPixmap(QPixmap(icon_per_storage_type(qgs_type_storage)))
        lbl_location_type.setScaledContents(True)
        lbl_location_type.setMaximumSize(20, 20)
        lbl_location_type.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_location_type.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        lbl_location_type.setToolTip(self.tr(qgs_type_storage))

        return lbl_location_type
