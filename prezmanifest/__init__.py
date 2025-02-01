import importlib.metadata

__version__ = importlib.metadata.version(__package__)

from .documentor import (
    catalogue as create_catalogue,
)
from .documentor import (
    table as create_table,
)
from .labeller import label as label
from .loader import load as load
from .validator import validate as validate
