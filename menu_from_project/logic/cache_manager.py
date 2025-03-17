# standard
import json
import os
import shutil
import tempfile
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# PyQGIS
from qgis.core import QgsApplication, QgsFileDownloader, QgsMessageLog
from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QUrl

# project
from menu_from_project.__about__ import __title__
from menu_from_project.datamodel.project import Project
from menu_from_project.datamodel.project_config import MenuProjectConfig


class CacheManager:
    """Manager to get information from cached data

    :param iface: QGIS iface
    :type iface: QgsInterface
    """

    DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"

    def __init__(self, iface) -> None:
        self.iface = iface

    @staticmethod
    def tr(message):
        return QCoreApplication.translate("MenuFromProject", message)

    # TODO: until a log manager is implemented
    @staticmethod
    def log(message, application=__title__, indent=0):
        indent_chars = " .. " * indent
        QgsMessageLog.logMessage(
            f"{indent_chars}{message}", application, notifyUser=True
        )

    def clear_project_cache(self, project: Project) -> None:
        """Clear project cache directory

        :param project: project
        :type project: Project
        """
        project_cache_dir = self.get_project_cache_dir(project)
        shutil.rmtree(project_cache_dir)

    def downloadError(self, errorMessages: List[str]):
        """Display error messages that occurs during download

        :param errorMessages: error messages
        :type errorMessages: List[str]
        """
        for err in errorMessages:
            QgsMessageLog.logMessage(
                "Download error. " + err,
                "Layers menu from project",
                notifyUser=True,
            )

    def _try_load_cache_validation_file(
        self, cache_validation_file: str, cache_validation_uri: str
    ) -> dict:
        """Try to load file content as json.

        :param cache_validation_file: file to load
        :type cache_validation_file: str
        :param cache_validation_uri: cache validation uri for this file
        :type cache_validation_uri: str
        :return: dict from json data in file
        :rtype: dict
        """
        with open(cache_validation_file, encoding="UTF-8") as f:
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError as e:
                self.log(
                    f"Invalid content in cache validation file '{cache_validation_uri}' : {e}. Can't check cache context."
                )
        return {}

    def get_cache_validation(self, cache_validation_uri: str) -> dict:
        """Read dict for cache validation for cache validation uri
        If uri if an url with http, the file is downloaded in a temporary dir

        If the file is not available (downloaded or local), an empty dict is returned

        If the file content is not json, an empty dict is returned

        :param cache_validation_uri: cache validation ur
        :type cache_validation_uri: str
        :return: dict for cache validation
        :rtype: dict
        """
        data = {}
        if cache_validation_uri.startswith("http"):
            # download it
            with tempfile.NamedTemporaryFile() as f:
                temp_file_path = f.name

            loop = QEventLoop()
            project_download = QgsFileDownloader(
                url=QUrl(cache_validation_uri),
                outputFileName=temp_file_path,
                delayStart=True,
            )
            project_download.downloadExited.connect(loop.quit)
            project_download.downloadError.connect(self.downloadError)
            project_download.startDownload()
            loop.exec()

            if Path(temp_file_path).exists():
                data = self._try_load_cache_validation_file(
                    cache_validation_file=temp_file_path,
                    cache_validation_uri=cache_validation_uri,
                )
                os.remove(temp_file_path)
            else:
                self.log(
                    f"Error when downloading cache validation file '{cache_validation_uri}'. Can't check cache context."
                )
        else:
            if Path(cache_validation_uri).exists():
                data = self._try_load_cache_validation_file(
                    cache_validation_file=cache_validation_uri,
                    cache_validation_uri=cache_validation_uri,
                )
            else:
                self.log(
                    f"Cache validation file '{cache_validation_uri}' doesn't exist. Can't check cache context."
                )
        return data

    def get_available_cache_info(self, project: Project) -> dict:
        """Read available cache info, empty dict if no cache info available

        :param project: project
        :type project: Project
        :return: cache info in dict
        :rtype: dict
        """
        cache_info = {}
        cache_path = self.get_project_cache_dir(project)
        cache_info_path = cache_path / "cache_info.json"
        if cache_info_path.exists():
            with open(cache_info_path, encoding="UTF-8") as f:
                cache_info = json.load(f)
        return cache_info

    def check_if_cache_enabled(self, project: Project) -> bool:
        """Check if cache is enabled for project

        :param project: project
        :type project: Project
        :return: True if cache is enabled, False otherwise
        :rtype: bool
        """
        cache_config = project.cache_config
        if not cache_config.enable:
            self.log(self.tr(f"Cache disabled for project {project.name}"))
            return False

        # Check if a cache info is available
        cache_info = self.get_available_cache_info(project)

        # Get cache last refresh
        if "last_refresh" in cache_info:
            cache_last_refresh = datetime.strptime(
                cache_info["last_refresh"], self.DATETIME_FORMAT
            )
        else:
            cache_last_refresh = None

        # Check refresh days period
        if cache_last_refresh and cache_config.refresh_days_period:
            refresh_date = cache_last_refresh + timedelta(
                days=cache_config.refresh_days_period
            )
            if datetime.now() > refresh_date:
                self.log(
                    self.tr(
                        f"Cache is not up to date since {refresh_date} for project {project.name}."
                    )
                )
                return False

        # Check validation file
        if cache_config.cache_validation_uri:
            cache_validation_data = self.get_cache_validation(
                cache_config.cache_validation_uri
            )
            if "last_release" in cache_validation_data and cache_last_refresh:
                last_release = datetime.strptime(
                    cache_validation_data["last_release"], self.DATETIME_FORMAT
                )
                if last_release > cache_last_refresh:
                    self.log(
                        self.tr(
                            f"Cache is not up to date with last release version in cache validation file {last_release} for project {project.name}."
                        )
                    )
                    return False

        return True

    def get_project_menu_config(self, project: Project) -> Optional[MenuProjectConfig]:
        """Get menu project configuration from cache for a project

        :param project: dict of information about the project
        :type project: Project
        :return: menu project configuration from cache, None if no cache available
        :rtype: Optional[MenuProjectConfig]
        """
        cache_path = self.get_project_cache_dir(project)
        if not self.check_if_cache_enabled(project):
            self.log(
                self.tr(f"Cache disabled for project {project.name}. Reloading data.")
            )
            return None

        json_cache_path = cache_path / "project_config.json"
        if json_cache_path.exists():
            with open(json_cache_path, "r", encoding="UTF-8") as f:
                data = json.load(f)
            return MenuProjectConfig.from_dict(data)
        return None

    def save_project_menu_config(
        self, project: Project, project_config: MenuProjectConfig
    ) -> None:
        """Save menu project configuration in cache

        :param project: dict of information about the project
        :type project: Project
        :param project_config: menu project configuration
        :type project_config: MenuProjectConfig
        """
        cache_path = self.get_project_cache_dir(project)
        json_cache_path = cache_path / "project_config.json"
        with open(json_cache_path, "w", encoding="UTF-8") as f:
            json.dump(asdict(project_config), f, indent=4)

        cache_info_path = cache_path / "cache_info.json"
        with open(cache_info_path, "w", encoding="UTF-8") as f:
            json.dump(
                {"last_refresh": datetime.now().strftime(self.DATETIME_FORMAT)},
                f,
                indent=4,
            )

    def get_project_cache_dir(self, project: Project) -> Path:
        """Get local project cache directory

        :param project: dict of information about the project
        :type project: Project
        :return: path to project cache directory
        :rtype: Path
        """
        cache_path = Path(QgsApplication.qgisSettingsDirPath())
        cache_path = cache_path / "cache" / "menu_from_project" / project.id
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    def get_project_download_dir(self, project: Project) -> Path:
        """Get local project cache download directory

        :param project: dict of information about the project
        :type project: Project
        :return: path to project cache directory
        :rtype: Path
        """
        cache_path = self.get_project_cache_dir(project)
        cache_path = cache_path / "downloads"
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path
