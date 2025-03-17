#! python3  # noqa: E265

# standard
import os
import platform
import subprocess
from typing import Optional

# PyQGIS
from qgis.core import QgsApplication, QgsMessageLog
from qgis.gui import QgsProviderGuiRegistry
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox, QWidget
from qgis.utils import iface

# project
from menu_from_project.__about__ import __title__
from menu_from_project.datamodel.project import Project, ProjectCacheConfig
from menu_from_project.logic.cache_manager import CacheManager
from menu_from_project.logic.qgs_manager import QgsDomManager
from menu_from_project.logic.tools import icon_per_storage_type


# ############################################################################
# ########## Classes ###############
# ##################################
class ProjectWidget(QWidget):
    """Widget to display project"""

    # Signal to indicate changes in project displayed
    projectChanged = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        uic.loadUi(
            os.path.dirname(os.path.realpath(__file__)) + "/project_widget.ui",
            self,
        )
        self.qgs_dom_manager = QgsDomManager()

        self.qsbx_cache_refresh_interval.setClearValue(-1, self.tr("None"))
        self.qsbx_cache_refresh_interval.setSuffix(self.tr(" days"))
        self.btn_project_path_selection.clicked.connect(self._select_path)

        self.rbn_source_type_file.setIcon(QIcon(icon_per_storage_type("file")))
        self.rbn_source_type_postgresql.setIcon(
            QIcon(icon_per_storage_type("database"))
        )
        self.rbn_source_type_url.setIcon(QIcon(icon_per_storage_type("http")))

        self.btn_cache_clear.setIcon(
            QIcon(":images/themes/default/console/iconClearConsole.svg")
        )
        self.btn_cache_clear.setToolTip(self.tr("Delete cache for this project"))

        self.qfile_cache_validation.setFilter("*.json")

        self.btn_cache_clear.clicked.connect(self._delete_project_cache)
        self.btn_cache_open_folder.clicked.connect(self._open_project_cache_folder)

        self.rbn_merge_with_previous.clicked.connect(self._merge_location_changed)
        self.rbn_create_new.clicked.connect(self._merge_location_changed)

        self._emit_changed_signal = True
        self._connect_update_signal()

    def enable_merge_option(self, enable: bool) -> None:
        """Enable merge option for project configuration

        :param enable: enable merge
        :type enable: bool
        """
        self._emit_changed_signal = False
        self.rbn_merge_with_previous.setEnabled(enable)
        if not enable:
            self.rbn_merge_with_previous.setToolTip(
                self.tr("Project in first position, no project to merge.")
            )
            self.rbn_merge_with_previous.setChecked(False)
        else:
            self.rbn_merge_with_previous.setToolTip("")
        self._emit_changed_signal = True

    def _merge_location_changed(self) -> None:
        """Disable other options if merge location is checked"""
        self.cbx_dest_menu_bar.setEnabled(not self.rbn_merge_with_previous.isChecked())
        self.cbx_dest_layer_menu.setEnabled(
            not self.rbn_merge_with_previous.isChecked()
        )
        self.cbx_dest_browser.setEnabled(not self.rbn_merge_with_previous.isChecked())

    def _project_changed(self) -> None:
        """Slot for projectChanged signal emit if enabled"""
        if self._emit_changed_signal:
            self.projectChanged.emit()

        project = self.get_project()

        if project.valid:
            self.lne_project_path_uri.setStyleSheet("color: {};".format("black"))
        else:
            self.lne_project_path_uri.setStyleSheet("color: {};".format("red"))

        self._update_path_selection_button_from_project(project)

    def _update_path_selection_button_from_project(self, project: Project) -> None:
        """Update path selection button from project configuration

        :param project: project configuration
        :type project: Project
        """
        self.btn_project_path_selection.setVisible(True)
        if project.type_storage == "file":
            self.btn_project_path_selection.setIcon(QIcon())
        elif project.type_storage == "database":
            self.btn_project_path_selection.setIcon(
                QIcon(":images/themes/default/mIconConnect.svg")
            )
        elif project.type_storage == "http":
            self.btn_project_path_selection.setVisible(False)

    def _connect_update_signal(self) -> None:
        """Connect update signal for project"""
        # Type storage update connection
        self.rbn_source_type_file.clicked.connect(self._project_changed)
        self.rbn_source_type_postgresql.clicked.connect(self._project_changed)
        self.rbn_source_type_url.clicked.connect(self._project_changed)

        # Location update connection
        self.rbn_create_new.clicked.connect(self._project_changed)
        self.cbx_dest_layer_menu.clicked.connect(self._project_changed)

        self.cbx_dest_menu_bar.clicked.connect(self._project_changed)
        self.rbn_merge_with_previous.clicked.connect(self._project_changed)
        self.cbx_dest_browser.clicked.connect(self._project_changed)

        # Name/path update connection
        self.lne_configuration_name.textChanged.connect(self._project_changed)
        self.lne_project_path_uri.textChanged.connect(self._project_changed)

        # Cache config update connection
        self.cbx_cache_enable.clicked.connect(self._project_changed)
        self.qsbx_cache_refresh_interval.valueChanged.connect(self._project_changed)
        self.qfile_cache_validation.fileChanged.connect(self._project_changed)

        # Project enable
        self.cbx_project_config_enable.clicked.connect(self._project_changed)

        # Project comment
        self.lne_comment.textChanged.connect(self._project_changed)

    def set_project(self, project: Project) -> None:
        """Define display project.

        :param project: displayed project
        :type project: Project
        """
        # Disable projectChanged signal emit
        self._emit_changed_signal = False

        self.lbl_cache_id_display.setText(project.id)
        self.lne_configuration_name.setText(project.name)
        self.lne_project_path_uri.setText(project.file)

        self.cbx_cache_enable.setChecked(project.cache_config.enable)
        if project.cache_config.refresh_days_period:
            self.qsbx_cache_refresh_interval.setValue(
                project.cache_config.refresh_days_period
            )
        else:
            self.qsbx_cache_refresh_interval.setValue(-1)

        self.qfile_cache_validation.setFilePath(
            project.cache_config.cache_validation_uri
        )

        self.cbx_dest_menu_bar.setChecked(False)
        self.cbx_dest_layer_menu.setChecked(False)
        self.cbx_dest_browser.setChecked(False)

        self.rbn_merge_with_previous.setChecked(project.location == "merge")
        self.rbn_create_new.setChecked(project.location != "merge")

        if project.location.count("new"):
            self.cbx_dest_menu_bar.setChecked(True)
        if project.location.count("layer"):
            self.cbx_dest_layer_menu.setChecked(True)
        if project.location.count("browser"):
            self.cbx_dest_browser.setChecked(True)

        if project.type_storage == "file":
            self.rbn_source_type_file.setChecked(True)
        elif project.type_storage == "database":
            self.rbn_source_type_postgresql.setChecked(True)
        elif project.type_storage == "http":
            self.rbn_source_type_url.setChecked(True)

        self.cbx_project_config_enable.setChecked(project.enable)

        self._update_path_selection_button_from_project(project)

        self.lne_comment.setText(project.comment)

        # Simulate merge location change to update check button
        self._merge_location_changed()

        # Restore projectChanged signal emit
        self._emit_changed_signal = True

    def get_project(self) -> Project:
        """Get displayed project.

        :return: displayed project
        :rtype: Project
        """
        cache_config = ProjectCacheConfig(
            enable=self.cbx_cache_enable.isChecked(),
            refresh_days_period=self.qsbx_cache_refresh_interval.value(),
            cache_validation_uri=self.qfile_cache_validation.filePath(),
        )
        if self.rbn_merge_with_previous.isChecked():
            location = "merge"
        else:
            locations = []
            if self.cbx_dest_menu_bar.isChecked():
                locations.append("new")
            if self.cbx_dest_layer_menu.isChecked():
                locations.append("layer")
            if self.cbx_dest_browser.isChecked():
                locations.append("browser")

            location = ",".join(locations)

        type_storage = "file"
        if self.rbn_source_type_file.isChecked():
            type_storage = "file"
        elif self.rbn_source_type_postgresql.isChecked():
            type_storage = "database"
        elif self.rbn_source_type_url.isChecked():
            type_storage = "http"

        project = Project(
            id=self.lbl_cache_id_display.text(),
            name=self.lne_configuration_name.text(),
            location=location,
            file=self.lne_project_path_uri.text(),
            type_storage=type_storage,
            cache_config=cache_config,
            enable=self.cbx_project_config_enable.isChecked(),
            comment=self.lne_comment.text(),
        )

        project.valid = self.qgs_dom_manager.check_if_project_valid(project)

        return project

    def _select_path(self) -> None:
        """Select project path depending on current type storage.

        - file : search for local file
        - database : display project database ui
        """
        if self.rbn_source_type_file.isChecked():
            self._define_local_path()
        elif self.rbn_source_type_postgresql.isChecked():
            self._define_database_path()

    def _define_database_path(self) -> None:
        """Define project path from database"""
        pgr = QgsProviderGuiRegistry(QgsApplication.pluginPath())
        if "postgres" in pgr.providerList():
            psgp = pgr.projectStorageGuiProviders("postgres")
            if len(psgp) > 0:
                uri = psgp[0].showLoadGui()
                self.lne_project_path_uri.setText(uri)

                if not self.lbl_project_name.text():
                    try:
                        name = uri.split("project=")[-1]
                        name = name.split(".")[0]
                    except Exception:
                        name = ""
                    self.lbl_project_name.setText(name)

    def _define_local_path(self) -> None:
        """Define project path for local path"""
        file_widget = self.lne_project_path_uri

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
        if filePath[0]:
            file_widget.setText(filePath[0])

            if not self.lbl_project_name.text():
                try:
                    name = filePath[0].split("/")[-1]
                    name = name.split(".")[0]
                except Exception:
                    name = ""

                self.lbl_project_name.setText(name)

    def _delete_project_cache(self) -> None:
        """Delete displayed project cache"""
        cache_manager = CacheManager(iface)
        cache_manager.clear_project_cache(project=self.get_project())

    def _open_project_cache_folder(self) -> None:
        """Open displayed project cache folder"""
        cache_manager = CacheManager(iface)
        project_cache_dir = str(cache_manager.get_project_cache_dir(self.get_project()))
        system_platform = platform.system()
        try:
            if system_platform == "Windows":
                os.startfile(project_cache_dir)
            elif system_platform == "Darwin":  # macOS
                subprocess.run(["open", project_cache_dir])
            else:  # Linux/Unix
                subprocess.run(["xdg-open", project_cache_dir])
        except Exception as err:
            QMessageBox.warning(
                self,
                self.tr("Explorator open error"),
                self.tr("Can't open project cache folder: {}".format(err)),
            )
            self.log(message=f"Error opening the cache folder: {err}")

    # TODO: until a log manager is implemented
    @staticmethod
    def log(message: str, application: str = __title__, indent: int = 0):
        indent_chars = " .. " * indent
        QgsMessageLog.logMessage(
            f"{indent_chars}{message}", application, notifyUser=True
        )
