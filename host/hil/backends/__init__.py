"""Concrete hardware-semantic adapters for deterministic HIL backends."""

from .beaglebone_pru import BeagleBonePruBackend
from .zynq import Ax7010Backend, Axu2cgbBackend

__all__ = [
    "BeagleBonePruBackend",
    "Ax7010Backend",
    "Axu2cgbBackend",
]
