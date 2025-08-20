"""Configuration validation utilities for bulletin board services."""

import os
import sys
from typing import Any, Dict, List, Tuple


class ConfigValidator:
    """Validates required environment variables and configuration."""

    # Required for full functionality
    REQUIRED_VARS = {
        "OPENROUTER_API_KEY": "Required for Claude agents to generate comments",
        "GEMINI_API_KEY": "Required for Gemini agents to generate comments",
        "NEWS_API_KEY": "Required for fetching tech news from NewsAPI",
        "GITHUB_READ_TOKEN": "Required for fetching curated content from GitHub",
    }

    # Optional but recommended
    OPTIONAL_VARS = {
        "GITHUB_FEED_REPO": "Repository for curated feed content (default: AndrewAltimit/AgentSocialFeed)",
        "GITHUB_FEED_BRANCH": "Branch for feed repository (default: main)",
        "BULLETIN_BOARD_API_URL": "API URL for bulletin board (default: http://bulletin-web:8080)",
    }

    # Critical for basic operation
    CRITICAL_VARS = {
        "DATABASE_URL": "Database connection string",
    }

    @classmethod
    def validate_critical(cls) -> Tuple[bool, List[str]]:
        """
        Validate critical environment variables required for basic operation.

        Returns:
            Tuple of (success, list of missing variables)
        """
        missing = []
        for var, description in cls.CRITICAL_VARS.items():
            if not os.getenv(var):
                missing.append(f"{var}: {description}")
        return len(missing) == 0, missing

    @classmethod
    def validate_required(cls) -> Tuple[bool, List[str]]:
        """
        Validate required environment variables for full functionality.

        Returns:
            Tuple of (success, list of missing variables)
        """
        missing = []
        for var, description in cls.REQUIRED_VARS.items():
            if not os.getenv(var):
                missing.append(f"{var}: {description}")
        return len(missing) == 0, missing

    @classmethod
    def validate_all(cls, fail_fast: bool = False) -> Dict[str, Any]:
        """
        Validate all configuration and return comprehensive status.

        Args:
            fail_fast: If True, exit with error on critical failures

        Returns:
            Dictionary with validation results
        """
        results: Dict[str, Any] = {
            "critical": {"valid": True, "missing": []},
            "required": {"valid": True, "missing": []},
            "warnings": [],
        }

        # Check critical variables
        critical_valid, critical_missing = cls.validate_critical()
        results["critical"]["valid"] = critical_valid
        results["critical"]["missing"] = critical_missing

        if not critical_valid and fail_fast:
            print(
                "❌ CRITICAL: Missing required environment variables:", file=sys.stderr
            )
            for var in critical_missing:
                print(f"  - {var}", file=sys.stderr)
            sys.exit(1)

        # Check required variables for full functionality
        required_valid, required_missing = cls.validate_required()
        results["required"]["valid"] = required_valid
        results["required"]["missing"] = required_missing

        # Generate warnings for missing but non-critical variables
        if required_missing:
            results["warnings"].append(
                f"Missing {len(required_missing)} API keys - some features will be limited"
            )

        # Check optional variables
        for var, description in cls.OPTIONAL_VARS.items():
            if not os.getenv(var):
                results["warnings"].append(f"Optional: {var} not set ({description})")

        return results

    @classmethod
    def print_validation_report(
        cls, verbose: bool = True, results: Dict[str, Any] | None = None
    ):
        """
        Print a formatted validation report to console.

        Args:
            verbose: If True, show all details; if False, show summary only
            results: Pre-computed validation results (if None, will run validation)
        """
        if results is None:
            results = cls.validate_all(fail_fast=False)

        print("\n" + "=" * 60)
        print("📋 CONFIGURATION VALIDATION REPORT")
        print("=" * 60)

        # Critical status
        if results["critical"]["valid"]:
            print("✅ Critical: All required for basic operation")
        else:
            print("❌ Critical: Missing required variables")
            if verbose:
                for var in results["critical"]["missing"]:
                    print(f"   - {var}")

        # Required status for full functionality
        if results["required"]["valid"]:
            print("✅ API Keys: All configured for full functionality")
        else:
            print("⚠️  API Keys: Some features will be limited")
            if verbose:
                for var in results["required"]["missing"]:
                    print(f"   - {var}")

        # Warnings
        if results["warnings"] and verbose:
            print("\n📝 Warnings:")
            for warning in results["warnings"]:
                print(f"   - {warning}")

        # Summary
        print("\n" + "-" * 60)
        if results["critical"]["valid"] and results["required"]["valid"]:
            print("✅ System is fully configured and ready!")
        elif results["critical"]["valid"]:
            print("⚠️  System can run with limited functionality")
            print("   Add missing API keys for full features")
        else:
            print("❌ System cannot start - fix critical issues first")

        print("=" * 60 + "\n")


def validate_startup(fail_fast: bool = True) -> bool:
    """
    Validate configuration at service startup.

    Args:
        fail_fast: If True, exit on critical failures

    Returns:
        True if all validations pass, False otherwise
    """
    validator = ConfigValidator()
    results = validator.validate_all(fail_fast=fail_fast)

    # Print report
    validator.print_validation_report(verbose=True)

    return bool(results["critical"]["valid"] and results["required"]["valid"])


if __name__ == "__main__":
    # Run validation when executed directly
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate bulletin board configuration"
    )
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Don't exit on critical failures, just report",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Show summary only, not detailed output"
    )

    args = parser.parse_args()

    validator = ConfigValidator()

    if args.quiet:
        results = validator.validate_all(fail_fast=not args.no_fail_fast)
        if results["critical"]["valid"] and results["required"]["valid"]:
            print("✅ Configuration valid")
            sys.exit(0)
        else:
            print("❌ Configuration incomplete")
            sys.exit(1)
    else:
        is_valid = validate_startup(fail_fast=not args.no_fail_fast)
        sys.exit(0 if is_valid else 1)
