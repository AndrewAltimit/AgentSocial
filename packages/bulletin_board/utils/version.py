"""Version management for the bulletin board application"""

import os
import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def get_version() -> str:
    """
    Get the application version dynamically.

    Priority order:
    1. APP_VERSION environment variable
    2. Git tag/commit hash
    3. Default version from __version__ file
    4. Fallback to "unknown"
    """
    # First check environment variable
    env_version = os.environ.get("APP_VERSION")
    if env_version:
        return env_version

    # Try to get version from git
    try:
        # Try to get the current tag
        tag = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            check=False,
        )
        if tag.returncode == 0:
            return tag.stdout.strip()

        # Otherwise get commit hash
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if commit.returncode == 0:
            # Check if working directory is clean
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
            )
            dirty = "-dirty" if status.stdout.strip() else ""
            return f"dev-{commit.stdout.strip()}{dirty}"
    except Exception:
        pass

    # Try to read from version file
    try:
        version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "__version__")
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                return f.read().strip()
    except Exception:
        pass

    # Fallback
    return "unknown"


# Export version for easy import
__version__ = get_version()
