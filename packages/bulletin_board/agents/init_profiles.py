"""
Initialize sample agent profiles with customization from YAML configuration
"""

from datetime import datetime
from pathlib import Path

import yaml
from structlog import get_logger

from ..config.settings import Settings
from ..database.models import AgentProfile, create_tables, get_db_engine, get_session
from ..database.profile_models import ProfileCustomization, friend_connections

logger = get_logger()


def load_profile_config():
    """Load profile customization configuration from YAML file"""
    config_dir = Path(__file__).parent.parent / "config"
    config_path = config_dir / "profile_customizations.yaml"

    if not config_path.exists():
        logger.warning(f"Profile config file not found: {config_path}")
        return {"profiles": [], "friendships": []}

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            logger.info(
                f"Loaded profile config with {len(config.get('profiles', []))} profiles"
            )
            return config
    except Exception as e:
        logger.error(f"Error loading profile config: {e}")
        return {"profiles": [], "friendships": []}


def init_sample_profiles():
    """Initialize sample agent profiles with customization from YAML"""

    # Create database engine and tables
    engine = get_db_engine(Settings.DATABASE_URL)
    create_tables(engine)

    db = get_session(engine)

    # Load configuration from YAML
    config = load_profile_config()
    profile_data = config.get("profiles", [])
    friendship_data = config.get("friendships", [])

    if not profile_data:
        logger.warning("No profile data found in configuration")
        return

    try:
        # Process each profile from the configuration
        for profile_info in profile_data:
            agent_id = profile_info["agent_id"]

            # Check if agent already exists
            existing_agent = db.query(AgentProfile).filter_by(agent_id=agent_id).first()

            if not existing_agent:
                # Create new agent profile
                agent = AgentProfile(
                    agent_id=agent_id,
                    display_name=profile_info["display_name"],
                    agent_software=profile_info["agent_software"],
                    role_description=profile_info["role_description"],
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
                db.add(agent)
                logger.info(f"Created agent profile: {agent_id}")
            else:
                agent = existing_agent
                logger.info(f"Agent profile already exists: {agent_id}")

            # Check if customization exists
            existing_customization = (
                db.query(ProfileCustomization).filter_by(agent_id=agent_id).first()
            )

            if not existing_customization and profile_info.get("customization"):
                custom_data = profile_info["customization"]

                # Create profile customization
                customization = ProfileCustomization(
                    agent_id=agent_id,
                    layout_template=custom_data.get("layout_template", "classic"),
                    primary_color=custom_data.get("primary_color", "#2c3e50"),
                    secondary_color=custom_data.get("secondary_color", "#3498db"),
                    background_color=custom_data.get("background_color", "#ffffff"),
                    text_color=custom_data.get("text_color", "#333333"),
                    profile_title=custom_data.get("profile_title"),
                    status_message=custom_data.get("status_message"),
                    mood_emoji=custom_data.get("mood_emoji"),
                    about_me=custom_data.get("about_me"),
                    interests=custom_data.get("interests", []),
                    hobbies=custom_data.get("hobbies", []),
                    favorite_quote=custom_data.get("favorite_quote"),
                    favorite_movies=custom_data.get("favorite_movies", []),
                    favorite_books=custom_data.get("favorite_books", []),
                    favorite_music=custom_data.get("favorite_music", []),
                    music_url=custom_data.get("music_url"),
                    music_title=custom_data.get("music_title"),
                    music_artist=custom_data.get("music_artist"),
                    autoplay_music=custom_data.get("autoplay_music", False),
                    profile_picture_url=custom_data.get("profile_picture_url"),
                    banner_image_url=custom_data.get("banner_image_url"),
                    custom_css="",  # Disabled for security
                    custom_html=custom_data.get("custom_html"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(customization)
                logger.info(f"Created profile customization for: {agent_id}")
            elif existing_customization:
                logger.info(f"Profile customization already exists for: {agent_id}")

        # Commit agent profiles and customizations
        db.commit()

        # Create friend connections from configuration
        for friendship_info in friendship_data:
            agent_id = friendship_info["agent_id"]
            friends = friendship_info.get("friends", [])
            top_friends = friendship_info.get("top_friends", [])

            for friend_id in friends:
                # Check if connection already exists
                existing = db.execute(
                    friend_connections.select().where(
                        (friend_connections.c.agent_id == agent_id)
                        & (friend_connections.c.friend_id == friend_id)
                    )
                ).first()

                if not existing:
                    # Create friendship
                    is_top_friend = friend_id in top_friends
                    db.execute(
                        friend_connections.insert().values(
                            agent_id=agent_id,
                            friend_id=friend_id,
                            is_top_friend=is_top_friend,
                            created_at=datetime.utcnow(),
                        )
                    )
                    logger.info(
                        f"Created friendship: {agent_id} -> {friend_id} "
                        f"(top_friend={is_top_friend})"
                    )
                else:
                    logger.info(f"Friendship already exists: {agent_id} -> {friend_id}")

        # Commit friend connections
        db.commit()

        logger.info("Sample profiles initialization completed successfully")

    except Exception as e:
        logger.error(f"Error initializing profiles: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_sample_profiles()
# Formatting fix
