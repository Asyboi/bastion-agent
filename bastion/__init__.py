"""Bastion — error observability for the agent era."""

__version__ = "0.3.0"

from .core import init
from .guard import guard
from .checkpoint import checkpoint
from .expect import expect
from .breadcrumb import breadcrumb

__all__ = ["init", "guard", "checkpoint", "expect", "breadcrumb", "__version__"]
