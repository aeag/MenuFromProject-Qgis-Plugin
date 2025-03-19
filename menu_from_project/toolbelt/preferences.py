#! python3  # noqa: E265

"""
Plugin settings.
"""

import uuid

# standard
from dataclasses import dataclass, field
from typing import List

# PyQGIS
from qgis.core import QgsSettings

# package
from menu_from_project.__about__ import __version__
from menu_from_project.datamodel.project import Project, ProjectCacheConfig
from menu_from_project.datamodel.project_config import MenuLayerConfig
from menu_from_project.logic.qgs_manager import QgsDomManager
from menu_from_project.logic.tools import guess_type_from_uri

# ############################################################################
# ########## Classes ###############
# ##################################

SOURCE_MD_OGC = "ogc"
SOURCE_MD_LAYER = "layer"
SOURCE_MD_NOTE = "note"


@dataclass
class PlgSettingsStructure:
    """Plugin settings structure and defaults values."""

    # global
    debug_mode: bool = False
    version: str = __version__

    # Projects
    projects: List[Project] = field(default_factory=lambda: [])

    # Menu option
    optionTooltip: bool = False
    optionCreateGroup: bool = False
    optionLoadAll: bool = False
    optionOpenLinks: bool = False
    optionSourceMD: List[str] = field(
        default_factory=lambda: [SOURCE_MD_OGC, SOURCE_MD_LAYER, SOURCE_MD_NOTE]
    )

    # Browser option
    browser_name: str = "Layers from project"

    # Internal option
    is_setup_visible: bool = True

    def tooltip_for_layer(self, layer_config: MenuLayerConfig) -> str:
        """Define tooltip from layer configuration and current settings

        :param layer_config: layer configuration
        :type layer_config: MenuLayerConfig
        :return: tooltip
        :rtype: str
        """
        if self.optionSourceMD == SOURCE_MD_OGC:
            abstract = layer_config.abstract or layer_config.metadata_abstract
            title = layer_config.title or layer_config.metadata_title
        else:
            abstract = layer_config.metadata_abstract or layer_config.abstract
            title = layer_config.metadata_title or layer_config.title

        abstract = ""
        title = ""
        for oSource in self.optionSourceMD:
            if oSource == SOURCE_MD_OGC:
                abstract = (
                    layer_config.metadata_abstract if abstract == "" else abstract
                )
                title = title or layer_config.metadata_title

            if oSource == SOURCE_MD_LAYER:
                abstract = layer_config.abstract if abstract == "" else abstract
                title = title or layer_config.title

            if oSource == SOURCE_MD_NOTE:
                abstract = layer_config.layer_notes if abstract == "" else abstract

        if (abstract != "") and (title == ""):
            tooltip = "<p>{}</p>".format(abstract)
        else:
            if abstract != "" or title != "":
                tooltip = "<b>{}</b><br/>{}".format(title, abstract)
            else:
                tooltip = ""
        return tooltip


class PlgOptionsManager:
    @staticmethod
    def get_plg_settings() -> PlgSettingsStructure:
        """Load and return plugin settings as a dictionary. \
        Useful to get user preferences across plugin logic.

        :return: plugin settings
        :rtype: PlgSettingsStructure
        """
        # instanciate new settings object
        options = PlgSettingsStructure()

        s = QgsSettings()

        if s.value("menu_from_project/is_setup_visible") is None:
            # This setting does not exist. We add it by default.
            s.setValue("menu_from_project/is_setup_visible", True)

        # If we want to hide the dialog setup to users.
        options.is_setup_visible = s.value(
            "menu_from_project/is_setup_visible", True, bool
        )

        try:
            s.beginGroup("menu_from_project")
            try:
                options.optionTooltip = s.value("optionTooltip", True, type=bool)
                options.optionCreateGroup = s.value(
                    "optionCreateGroup", False, type=bool
                )
                options.optionLoadAll = s.value("optionLoadAll", False, type=bool)
                options.optionOpenLinks = s.value("optionOpenLinks", True, type=bool)
                defaultOptionSourceMD = "{},{},{}".format(
                    SOURCE_MD_OGC,
                    SOURCE_MD_LAYER,
                    SOURCE_MD_NOTE,
                )
                optionSourceMD = s.value(
                    "optionSourceMD",
                    defaultOptionSourceMD,
                    type=str,
                )
                options.optionSourceMD = optionSourceMD.split(",")
                # Retro comp
                if (
                    len(options.optionSourceMD) == 1
                    and options.optionSourceMD[0] == SOURCE_MD_OGC
                ):
                    options.optionSourceMD = [
                        SOURCE_MD_OGC,
                        SOURCE_MD_LAYER,
                        SOURCE_MD_NOTE,
                    ]
                if (
                    len(options.optionSourceMD) == 1
                    and options.optionSourceMD[0] == SOURCE_MD_LAYER
                ):
                    options.optionSourceMD = [
                        SOURCE_MD_LAYER,
                        SOURCE_MD_OGC,
                        SOURCE_MD_NOTE,
                    ]
                if (
                    len(options.optionSourceMD) == 1
                    and options.optionSourceMD[0] == SOURCE_MD_NOTE
                ):
                    options.optionSourceMD = [
                        SOURCE_MD_NOTE,
                        SOURCE_MD_LAYER,
                        SOURCE_MD_OGC,
                    ]

                options.browser_name = s.value("browser_name", options.browser_name)

                size = s.beginReadArray("projects")
                try:
                    for i in range(size):
                        s.setArrayIndex(i)
                        file = s.value("file", "")
                        name = s.value("name", "")
                        location = s.value("location", "new")
                        type_storage = s.value(
                            "type_storage", guess_type_from_uri(file)
                        )

                        s.beginGroup("cache_config")
                        cache_config = ProjectCacheConfig(
                            refresh_days_period=s.value(
                                "refresh_days_period", None, type=int
                            ),
                            enable=s.value("enable", True, type=bool),
                            cache_validation_uri=s.value("cache_validation_uri", ""),
                        )
                        s.endGroup()

                        if file != "":
                            project = Project(
                                file=file,
                                name=name,
                                location=location,
                                type_storage=type_storage,
                                cache_config=cache_config,
                                id=s.value("id", str(uuid.uuid4())),
                                enable=s.value("enable", True, type=bool),
                                comment=s.value("comment", ""),
                                valid=s.value("valid", True, type=bool),
                            )
                            options.projects.append(project)
                finally:
                    s.endArray()

            finally:
                s.endGroup()

        except Exception:
            pass

        return options

    @classmethod
    def save_from_object(cls, plugin_settings_obj: PlgSettingsStructure):
        """Load and return plugin settings as a dictionary.

        Useful to get user preferences across plugin logic.

        :return: plugin settings value matching key
        """
        dom_manager = QgsDomManager()
        s = QgsSettings()

        s.beginGroup("menu_from_project")
        try:
            s.setValue("optionTooltip", plugin_settings_obj.optionTooltip)
            s.setValue("optionCreateGroup", plugin_settings_obj.optionCreateGroup)
            s.setValue("optionLoadAll", plugin_settings_obj.optionLoadAll)
            s.setValue("optionOpenLinks", plugin_settings_obj.optionOpenLinks)
            s.setValue("optionSourceMD", ",".join(plugin_settings_obj.optionSourceMD))

            s.setValue("browser_name", plugin_settings_obj.browser_name)

            s.remove("projects")
            s.beginWriteArray("projects", len(plugin_settings_obj.projects))
            try:
                for i, project in enumerate(plugin_settings_obj.projects):
                    s.setArrayIndex(i)
                    s.setValue("file", project.file)
                    s.setValue("name", project.name)
                    s.setValue("location", project.location)
                    s.setValue("type_storage", guess_type_from_uri(project.file))
                    s.setValue("id", project.id)
                    s.setValue("enable", project.enable)

                    s.beginGroup("cache_config")
                    s.setValue(
                        "refresh_days_period", project.cache_config.refresh_days_period
                    )
                    s.setValue("enable", project.cache_config.enable)
                    s.setValue(
                        "cache_validation_uri",
                        project.cache_config.cache_validation_uri,
                    )
                    s.setValue("comment", project.comment)
                    s.setValue("valid", dom_manager.check_if_project_valid(project))
                    s.endGroup()
            finally:
                s.endArray()
        finally:
            s.endGroup()
