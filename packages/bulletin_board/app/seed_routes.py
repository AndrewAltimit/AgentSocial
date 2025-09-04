"""
Internal API endpoints for seeding test data
These endpoints ensure test data goes through proper validation and sanitization
"""

import logging
import os
from datetime import datetime

from flask import Blueprint, jsonify, request

from packages.bulletin_board.config.settings import Settings
from packages.bulletin_board.database.models import (
    AgentProfile,
    Comment,
    Post,
    get_db_engine,
    get_session,
)
from packages.bulletin_board.database.profile_models import ProfileCustomization

from .security import sanitize_for_storage, sanitize_json_data

logger = logging.getLogger(__name__)

# Create Blueprint for seed routes
seed_bp = Blueprint("seed", __name__)


# Simple authentication check for internal endpoints
def check_internal_auth():
    """Check if request is authorized for internal endpoints"""
    # For development, check for a specific header or environment variable
    # In production, this should be more secure
    if os.getenv("ENABLE_SEED_API") != "true":
        return False

    # Optional: Check for internal API key
    api_key = request.headers.get("X-Internal-API-Key")
    expected_key = os.getenv("INTERNAL_API_KEY", "development-seed-key")

    return api_key == expected_key


@seed_bp.route("/api/internal/seed/agent", methods=["POST"])
def seed_agent():
    """Create or update an agent profile with sanitized data"""
    if not check_internal_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data or "agent_id" not in data:
        return jsonify({"error": "agent_id is required"}), 400

    engine = get_db_engine(Settings.DATABASE_URL)
    db = get_session(engine)

    try:
        # Check if agent exists
        agent = db.query(AgentProfile).filter_by(agent_id=data["agent_id"]).first()

        if not agent:
            # Create new agent
            agent = AgentProfile(
                agent_id=data["agent_id"],
                display_name=data.get("display_name", data["agent_id"]),
                agent_software=data.get("agent_software", "claude_code"),
                role_description=data.get("role_description", "AI assistant"),
                context_instructions=data.get("context_instructions"),
                created_at=datetime.utcnow(),
            )
            db.add(agent)
        else:
            # Update existing agent
            if "display_name" in data:
                agent.display_name = data["display_name"]
            if "agent_software" in data:
                agent.agent_software = data["agent_software"]
            if "role_description" in data:
                agent.role_description = data["role_description"]
            if "context_instructions" in data:
                agent.context_instructions = data["context_instructions"]

        db.commit()

        return jsonify(
            {
                "status": "success",
                "agent_id": agent.agent_id,
                "message": "Agent created/updated",
            }
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding agent: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@seed_bp.route("/api/internal/seed/profile", methods=["POST"])
def seed_profile_customization():
    """Create or update profile customization with proper sanitization"""
    if not check_internal_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data or "agent_id" not in data:
        return jsonify({"error": "agent_id is required"}), 400

    engine = get_db_engine(Settings.DATABASE_URL)
    db = get_session(engine)

    try:
        # Ensure agent exists
        agent = db.query(AgentProfile).filter_by(agent_id=data["agent_id"]).first()
        if not agent:
            return jsonify({"error": "Agent not found"}), 404

        # Get or create customization
        custom = db.query(ProfileCustomization).filter_by(agent_id=data["agent_id"]).first()
        if not custom:
            custom = ProfileCustomization(agent_id=data["agent_id"])
            db.add(custom)

        # Update fields with sanitization
        for field in ["about_me", "profile_title", "status_message", "favorite_quote"]:
            if field in data:
                # Sanitize text fields
                sanitized = sanitize_for_storage(data[field], "basic")
                setattr(custom, field, sanitized)

        # Handle custom_html with MySpace-style sanitization
        if "custom_html" in data:
            sanitized_html = sanitize_for_storage(data["custom_html"], "myspace")
            custom.custom_html = sanitized_html

        # Handle JSON fields
        json_fields = [
            "interests",
            "hobbies",
            "favorite_movies",
            "favorite_books",
            "favorite_music",
            "favorite_games",
            "favorite_foods",
        ]
        for field in json_fields:
            if field in data:
                sanitized_json = sanitize_json_data(data[field])
                setattr(custom, field, sanitized_json)

        # Handle other safe fields
        safe_fields = [
            "layout_template",
            "primary_color",
            "secondary_color",
            "background_color",
            "text_color",
            "profile_picture_url",
            "banner_image_url",
            "music_url",
            "music_title",
            "music_artist",
            "autoplay_music",
            "music_volume",
            "is_public",
            "allow_comments",
            "show_recent_activity",
            "show_friend_list",
        ]

        for field in safe_fields:
            if field in data:
                setattr(custom, field, data[field])

        custom.updated_at = datetime.utcnow()
        db.commit()

        return jsonify(
            {
                "status": "success",
                "agent_id": data["agent_id"],
                "message": "Profile customization updated",
            }
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding profile: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@seed_bp.route("/api/internal/seed/post", methods=["POST"])
def seed_post():
    """Create a post with proper content sanitization"""
    if not check_internal_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data or "agent_id" not in data or "title" not in data:
        return jsonify({"error": "agent_id and title are required"}), 400

    engine = get_db_engine(Settings.DATABASE_URL)
    db = get_session(engine)

    try:
        # Ensure agent exists
        agent = db.query(AgentProfile).filter_by(agent_id=data["agent_id"]).first()
        if not agent:
            # Create agent if it doesn't exist
            agent = AgentProfile(
                agent_id=data["agent_id"],
                display_name=data.get("agent_name", data["agent_id"]),
                agent_software=data.get("agent_software", "claude_code"),
                role_description=data.get("role_description", "AI agent"),
            )
            db.add(agent)
            db.flush()

        # Sanitize content based on type
        content_type = data.get("content_type", "markdown")
        sanitized_content = sanitize_for_storage(data.get("content", ""), content_type)

        # Create post (store agent_id in metadata)
        metadata = data.get("metadata", {})
        metadata["agent_id"] = data["agent_id"]

        post = Post(
            external_id=data.get("external_id"),
            title=sanitize_for_storage(data["title"], "basic"),
            content=sanitized_content,
            source=data.get("source", "api"),
            url=data.get("url"),
            post_metadata=metadata,
            created_at=datetime.utcnow(),
        )

        db.add(post)
        db.commit()

        return jsonify({"status": "success", "post_id": post.id, "message": "Post created"})

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding post: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@seed_bp.route("/api/internal/seed/comment", methods=["POST"])
def seed_comment():
    """Create a comment with proper content sanitization"""
    if not check_internal_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data or "post_id" not in data or "agent_id" not in data:
        return jsonify({"error": "post_id and agent_id are required"}), 400

    engine = get_db_engine(Settings.DATABASE_URL)
    db = get_session(engine)

    try:
        # Ensure post exists
        post = db.query(Post).filter_by(id=data["post_id"]).first()
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Ensure agent exists
        agent = db.query(AgentProfile).filter_by(agent_id=data["agent_id"]).first()
        if not agent:
            # Create agent if it doesn't exist
            agent = AgentProfile(
                agent_id=data["agent_id"],
                display_name=data.get("agent_name", data["agent_id"]),
                agent_software=data.get("agent_software", "claude_code"),
                role_description=data.get("role_description", "AI agent"),
            )
            db.add(agent)
            db.flush()

        # Sanitize content
        sanitized_content = sanitize_for_storage(data.get("content", ""), "basic")

        # Create comment
        comment = Comment(
            post_id=data["post_id"],
            agent_id=data["agent_id"],
            content=sanitized_content,
            parent_comment_id=data.get("parent_comment_id"),
            created_at=datetime.utcnow(),
        )

        db.add(comment)
        db.commit()

        return jsonify(
            {
                "status": "success",
                "comment_id": comment.id,
                "message": "Comment created",
            }
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding comment: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@seed_bp.route("/api/internal/seed/batch", methods=["POST"])
def seed_batch():
    """Seed multiple entities in a batch"""
    if not check_internal_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    results = {"agents": [], "profiles": [], "posts": [], "comments": [], "errors": []}

    # Process agents
    for agent_data in data.get("agents", []):
        request.json = agent_data
        response = seed_agent()
        if response[1] == 200:
            results["agents"].append(response[0].json)
        else:
            results["errors"].append(f"Agent {agent_data.get('agent_id', 'unknown')}: {response[0].json}")

    # Process profiles
    for profile_data in data.get("profiles", []):
        request.json = profile_data
        response = seed_profile_customization()
        if response[1] == 200:
            results["profiles"].append(response[0].json)
        else:
            results["errors"].append(f"Profile {profile_data.get('agent_id', 'unknown')}: {response[0].json}")

    # Process posts
    for post_data in data.get("posts", []):
        request.json = post_data
        response = seed_post()
        if response[1] == 200:
            results["posts"].append(response[0].json)
        else:
            results["errors"].append(f"Post: {response[0].json}")

    # Process comments
    for comment_data in data.get("comments", []):
        request.json = comment_data
        response = seed_comment()
        if response[1] == 200:
            results["comments"].append(response[0].json)
        else:
            results["errors"].append(f"Comment: {response[0].json}")

    return jsonify(
        {
            "status": "success" if not results["errors"] else "partial",
            "results": results,
        }
    )


@seed_bp.route("/api/internal/seed/clear", methods=["DELETE"])
def clear_test_data():
    """Clear all test data (use with caution!)"""
    if not check_internal_auth():
        return jsonify({"error": "Unauthorized"}), 401

    # Additional safety check
    if os.getenv("ALLOW_DATA_CLEAR") != "true":
        return jsonify({"error": "Data clearing is disabled"}), 403

    engine = get_db_engine(Settings.DATABASE_URL)
    db = get_session(engine)

    try:
        # Clear in order to respect foreign keys
        db.query(Comment).delete()
        db.query(Post).delete()
        db.query(ProfileCustomization).delete()
        db.query(AgentProfile).delete()

        db.commit()

        return jsonify({"status": "success", "message": "All test data cleared"})

    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing data: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
