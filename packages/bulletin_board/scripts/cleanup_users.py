#!/usr/bin/env python3
"""
Clean up database to only keep users with profile customizations.
"""

from sqlalchemy import text
from structlog import get_logger

from packages.bulletin_board.config.settings import Settings
from packages.bulletin_board.database.models import (
    AgentProfile,
    get_db_engine,
    get_session,
)
from packages.bulletin_board.database.profile_models import ProfileCustomization
from packages.bulletin_board.utils.logging import configure_logging

# Configure logging
configure_logging(Settings.LOG_LEVEL, Settings.LOG_FORMAT == "json")
logger = get_logger()


def cleanup_users():
    """Remove users without profile customizations"""
    logger.info("Starting user cleanup...")

    # Create database connection
    engine = get_db_engine(Settings.DATABASE_URL)
    session = get_session(engine)

    try:
        # Find agents without customizations
        agents_with_profiles = session.query(ProfileCustomization.agent_id)
        agents_to_remove = session.query(AgentProfile).filter(~AgentProfile.agent_id.in_(agents_with_profiles)).all()

        if agents_to_remove:
            logger.info(f"Found {len(agents_to_remove)} agents without profiles to remove:")
            agent_ids = []
            for agent in agents_to_remove:
                logger.info(f"  - {agent.display_name} ({agent.agent_id})")
                agent_ids.append(agent.agent_id)

            # First delete related data (cascade)
            # Delete profile visits
            agent_ids_str = ", ".join(f"'{aid}'" for aid in agent_ids)
            session.execute(text(f"DELETE FROM profile_visits WHERE profile_agent_id IN ({agent_ids_str})"))
            session.execute(text(f"DELETE FROM profile_visits WHERE visitor_agent_id IN ({agent_ids_str})"))

            # Delete friend connections
            session.execute(text(f"DELETE FROM friend_connections WHERE agent_id IN ({agent_ids_str})"))
            session.execute(text(f"DELETE FROM friend_connections WHERE friend_id IN ({agent_ids_str})"))

            # Now delete the agents
            for agent in agents_to_remove:
                session.delete(agent)

            session.commit()
            logger.info(f"Successfully removed {len(agents_to_remove)} agents")
        else:
            logger.info("No agents to remove - all have profiles")

        # Show remaining agents
        remaining = session.query(AgentProfile).all()
        logger.info(f"Remaining agents with profiles: {len(remaining)}")
        for agent in remaining:
            logger.info(f"  ✓ {agent.display_name} ({agent.agent_id})")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    cleanup_users()
