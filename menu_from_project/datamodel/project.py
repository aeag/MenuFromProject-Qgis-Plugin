from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProjectCacheConfig:
    """Project cache configuration"""

    enable: bool = True
    refresh_days_period: Optional[int] = None
    cache_validation_uri: str = ""


@dataclass
class Project:
    """All information for project"""

    id: str
    name: str
    location: str
    file: str
    type_storage: str
    valid: bool = True
    enable: bool = True
    cache_config: ProjectCacheConfig = field(
        default_factory=lambda: ProjectCacheConfig()
    )
    comment: str = ""
