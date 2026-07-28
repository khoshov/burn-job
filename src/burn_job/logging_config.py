"""Legacy logging_config module alias (deprecated). Re-exports from burn_job.core.logging."""

import warnings
from burn_job.core.logging import setup_logger

warnings.warn(
    "Importing from 'burn_job.logging_config' is deprecated; use 'burn_job.core.logging' instead.",
    DeprecationWarning,
    stacklevel=2,
)
