"""Bastion — error observability for the agent era."""

__version__ = "0.1.0"

from .core import init
from .guard import guard
from .checkpoint import checkpoint
from .expect import expect

__all__ = ["init", "guard", "checkpoint", "expect", "__version__"]
