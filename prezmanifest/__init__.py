import importlib.metadata

__version__ = importlib.metadata.version(__package__)

from .definednamespaces import MRR, OLIS, PREZ
from .validator import validate
from .documentor import create_table
from .loader import load
from .labeller import label
