"""Custom exception hierarchy for the forex trading system."""


class ForexSystemError(Exception):
    """Base exception for all forex system errors."""


class ConfigError(ForexSystemError):
    """Configuration loading or validation error."""


class DataError(ForexSystemError):
    """Data acquisition, validation, or storage error."""


class ValidationError(DataError):
    """Data quality check failure."""


class StrategyError(ForexSystemError):
    """Strategy computation error."""


class BacktestError(ForexSystemError):
    """Backtesting engine error."""


class CostModelError(ForexSystemError):
    """Transaction cost calculation error."""


class ExperimentError(ForexSystemError):
    """Experiment registry error."""
