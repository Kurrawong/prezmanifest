import importlib.metadata

__version__ = importlib.metadata.version(__package__)

from .definednamespaces import MRR, OLIS, PREZ
from .documentor import create_table
from .validator import validate
from .loader import load


