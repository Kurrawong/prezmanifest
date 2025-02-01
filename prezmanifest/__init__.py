import importlib.metadata

__version__ = importlib.metadata.version(__package__)

from .validator import validate as validate
from .documentor import (
    create_table as create_table,
    create_catalogue as create_catalogue,
)
from .loader import load as load
from .labeller import label as label
