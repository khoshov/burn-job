"""Domain exception hierarchy for burn-job."""

class BurnJobError(Exception):
    """Base exception for all burn-job errors."""
    pass

class ConfigurationError(BurnJobError):
    """Raised when configuration settings are invalid or missing."""
    pass

class DetectorError(BurnJobError):
    """Base exception for defect detector failures."""
    pass

class DetectorExecutionError(DetectorError):
    """Raised when a detector fails during analysis execution."""
    pass

class GraphStoreError(BurnJobError):
    """Raised when graph database operations fail."""
    pass

class PipelineExecutionError(BurnJobError):
    """Raised when pipeline cycle execution encounters a unrecoverable failure."""
    pass
