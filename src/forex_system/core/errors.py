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


class LookaheadError(ForexSystemError):
    """Raised when a caller attempts to access data past the OOS holdout boundary.

    This enforces that in-sample training data cannot inadvertently include
    out-of-sample holdout dates. The holdout_after date is set in config
    under backtest.oos_holdout_start.

    To access the holdout legitimately, use the harness --final-oos-test flag,
    which records the access in .fintech-org/oos-burns.jsonl.
    """
