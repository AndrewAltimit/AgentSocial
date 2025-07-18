#!/usr/bin/env python3
"""
Initialize agent profiles in the database
"""
from sqlalchemy.exc import IntegrityError

from bulletin_board.agents.agent_profiles import AGENT_PROFILES
from bulletin_board.config.settings import Settings
from bulletin_board.database.models import (
    AgentProfile,
    create_tables,
    get_db_engine,
    get_session,
)


def init_agents():
    """Initialize agent profiles in the database"""
    engine = get_db_engine(Settings.DATABASE_URL)
    create_tables(engine)

    session = get_session(engine)

    for profile_data in AGENT_PROFILES:
        try:
            # Check if agent already exists
            existing = (
                session.query(AgentProfile)
                .filter_by(agent_id=profile_data["agent_id"])
                .first()
            )

            if existing:
                # Update existing profile
                existing.display_name = profile_data["display_name"]
                existing.agent_software = profile_data["agent_software"]
                existing.role_description = profile_data["role_description"]
                existing.context_instructions = profile_data["context_instructions"]
                existing.is_active = True
                print(f"Updated agent: {profile_data['agent_id']}")
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
                print(f"Created agent: {profile_data['agent_id']}")

            session.commit()

        except IntegrityError:
            session.rollback()
            print(f"Error creating agent: {profile_data['agent_id']}")

    session.close()
    print(f"\nInitialized {len(AGENT_PROFILES)} agent profiles")


if __name__ == "__main__":
    init_agents()
