"""Quantum Executor Module."""

__version__ = "0.1.0"

import logging

from .dispatch import Dispatch
from .executor import QuantumExecutor
from .virtual_provider import VirtualProvider

__all__ = ["Dispatch", "QuantumExecutor", "VirtualProvider"]

# Configure logging for the package.
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
