#! python3  # noqa: E265

# standard
from typing import List, Optional

# PyQGIS
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QModelIndex, QObject, Qt
from qgis.PyQt.QtGui import QColor, QIcon, QStandardItemModel

# project
from menu_from_project.datamodel.project import Project
from menu_from_project.logic.tools import icon_per_storage_type


class ProjectListModel(QStandardItemModel):
    NAME_COL = 0
    LOCATION_COL = 1
    CACHE_COL = 2

    def __init__(self, parent: QObject = None):
        """
        QStandardItemModel for project list display

        Args:
            parent: QObject parent
        """
        super().__init__(parent)
        self.setHorizontalHeaderLabels(
            [self.tr("Name"), self.tr("Location"), self.tr("Cache")]
        )

    def flags(self, index: QModelIndex) -> QtCore.Qt.ItemFlags:
        """Flags to disable editing

        :param index: index (unused)
        :type index: QModelIndex
        :return: flags
        :rtype: QtCore.Qt.ItemFlags
        """
        default_flags = super().flags(index)
        return default_flags & ~Qt.ItemIsEditable  # Disable editing

    def get_project_list(self) -> List[Project]:
        """Return project list

        :return: project list
        :rtype: List[Project]
        """
        result = []
        for row in range(0, self.rowCount()):
            result.append(self.get_row_project(row))
        return result

    def set_project_list(self, project_list: List[Project]) -> None:
        """Define project list

        :param project_list: project list
        :type project_list: List[Project]
        """
        self.removeRows(0, self.rowCount())
        for project in project_list:
            self.insert_project(project)

    def insert_project(self, project: Project) -> None:
        """Insert project into model

        :param project: project to insert
        :type project: project
        """
        row = self.rowCount()
        self.insertRow(row)
        self.set_row_project(row, project)

    def set_row_project(self, row: int, project: Project) -> None:
        """Define project for a row

        :param row: row
        :type row: int
        :param project: project
        :type project: Project
        """
        self.setData(self.index(row, self.NAME_COL), project.name)
        self.setData(self.index(row, self.NAME_COL), project, Qt.UserRole)
        self.setData(self.index(row, self.NAME_COL), project.file, Qt.ToolTipRole)
        self.setData(
            self.index(row, self.NAME_COL),
            QIcon(icon_per_storage_type(project.type_storage)),
            Qt.DecorationRole,
        )
        self.setData(self.index(row, self.LOCATION_COL), project.location)
        if project.cache_config.enable:
            self.setData(
                self.index(row, self.CACHE_COL),
                QIcon(":images/themes/default/algorithms/mAlgorithmCheckGeometry.svg"),
                Qt.DecorationRole,
            )

        if not project.enable:
            self._set_row_color(row, QColor("lightgrey"))
        elif not project.valid:
            self._set_row_color(row, QColor("crimson"))
        else:
            self._set_row_color(row, None)

    def _set_row_color(self, row: int, color: Optional[QColor]) -> None:
        """Define row color

        :param row: row
        :type row: int
        :param color: color to use
        :type color: Optional[QColor]
        """
        self.setData(self.index(row, self.NAME_COL), color, Qt.BackgroundRole)
        self.setData(self.index(row, self.LOCATION_COL), color, Qt.BackgroundRole)
        self.setData(self.index(row, self.CACHE_COL), color, Qt.BackgroundRole)

    def get_row_project(self, row) -> Project:
        """Get project for a row

        :param row: row
        :type row: _type_
        :return: project
        :rtype: Project
        """
        return self.data(self.index(row, self.NAME_COL), Qt.UserRole)
