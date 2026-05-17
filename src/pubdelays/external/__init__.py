"""External metadata cleaning stages."""

from .doaj import preprocess_doaj
from .npi import preprocess_npi
from .publisher import preprocess_publisher
from .retraction_watch import preprocess_retraction_watch
from .scimago import preprocess_scimago
from .wos import preprocess_wos

__all__ = [
    "preprocess_doaj",
    "preprocess_npi",
    "preprocess_publisher",
    "preprocess_retraction_watch",
    "preprocess_scimago",
    "preprocess_wos",
]
