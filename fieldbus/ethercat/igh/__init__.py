"""IgH EtherCAT Master controller adapter."""

from .adapter import IghEthercatCli

__all__ = ["IghEthercatCli"]

from .cycle import EthercatCycleMetrics, IghCycleQualifier
