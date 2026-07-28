"""Legacy config module alias (deprecated). Re-exports from burn_job.core.config."""

import warnings
from burn_job.core.config import *

warnings.warn(
    "Importing from 'burn_job.config' is deprecated; use 'burn_job.core.config' instead.",
    DeprecationWarning,
    stacklevel=2,
)
