#!/usr/bin/env python3
"""
Initialize agent profiles in the database
"""
from bulletin_board.agents.agent_profiles import AGENT_PROFILES
from bulletin_board.config.settings import Settings
from bulletin_board.database.models import (
    AgentProfile,
    create_tables,
    get_db_engine,
    get_session,
)
from bulletin_board.utils.logging import configure_logging
from sqlalchemy.exc import IntegrityError
from structlog import get_logger

# Initialize logger - configuration will be done when needed
logger = get_logger()


def init_agents():
    """Initialize agent profiles in the database"""
    # Configure logging when function is called
    configure_logging(Settings.LOG_LEVEL, Settings.LOG_FORMAT == "json")

    engine = get_db_engine(Settings.DATABASE_URL)
    create_tables(engine)

    session = get_session(engine)

    for profile_data in AGENT_PROFILES:
        try:
            # Check if agent already exists
            existing = session.query(AgentProfile).filter_by(agent_id=profile_data["agent_id"]).first()

            if existing:
                # Update existing profile
                existing.display_name = profile_data["display_name"]
                existing.agent_software = profile_data["agent_software"]
                existing.role_description = profile_data["role_description"]
                existing.context_instructions = profile_data["context_instructions"]
                existing.is_active = True
                logger.info("Updated agent", agent_id=profile_data["agent_id"])
            else:
                # Create new profile
                agent = AgentProfile(
                    agent_id=profile_data["agent_id"],
                    display_name=profile_data["display_name"],
                    agent_software=profile_data["agent_software"],
                    role_description=profile_data["role_description"],
                    context_instructions=profile_data["context_instructions"],
                )
                session.add(agent)
                logger.info("Created agent", agent_id=profile_data["agent_id"])

            session.commit()

        except IntegrityError as e:
            session.rollback()
            logger.error("Error creating agent", agent_id=profile_data["agent_id"], error=str(e))

    session.close()
    logger.info("Agent initialization completed", total_agents=len(AGENT_PROFILES))


if __name__ == "__main__":
    init_agents()
