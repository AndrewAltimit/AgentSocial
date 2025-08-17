"""
Agent profiles for bulletin board interactions
"""

import os
from pathlib import Path

import yaml
from structlog import get_logger

logger = get_logger()


# Load agent profiles from YAML configuration
def load_agent_profiles():
    """Load agent profiles from YAML configuration file"""
    config_path = Path(__file__).parent.parent / "config" / "agent_profiles.yaml"

    # Allow override via environment variable
    config_file = os.getenv("AGENT_PROFILES_CONFIG", str(config_path))

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
            logger.info(
                "Loaded agent profiles",
                config_file=config_file,
                agent_count=len(config.get("agents", [])),
            )
            return config.get("agents", [])
    except FileNotFoundError:
        logger.error("Agent profiles configuration not found", config_file=config_file)
        return []
    except yaml.YAMLError as e:
        logger.error("Error parsing agent profiles YAML", config_file=config_file, error=str(e))
        return []
    except Exception as e:
        logger.error("Error loading agent profiles", config_file=config_file, error=str(e))
        return []


# Load profiles on module import
AGENT_PROFILES = load_agent_profiles()


def get_agent_by_id(agent_id: str):
    """Get agent profile by ID"""
    for profile in AGENT_PROFILES:
        if profile["agent_id"] == agent_id:
            return profile
    return None


def get_agents_by_software(software: str):
    """Get all agents using specific software"""
    return [p for p in AGENT_PROFILES if p["agent_software"] == software]
