"""
Flask routes for agent profile customization
"""

from datetime import datetime, timedelta

import bleach  # type: ignore[import-untyped]
from flask import Blueprint, abort, jsonify, render_template, request
from structlog import get_logger

from ..database.models import AgentProfile, get_session
from ..database.profile_models import (
    ProfileBlogPost,
    ProfileComment,
    ProfileCustomization,
    ProfileMedia,
    ProfilePlaylist,
    ProfileVisit,
    ProfileWidget,
    friend_connections,
)

logger = get_logger()
profile_bp = Blueprint("profiles", __name__, url_prefix="/profiles")


def _get_hydrated_profiles(db, agent_ids=None, include_stats=True):
    """
    Helper function to get fully hydrated profile data.

    Args:
        db: Database session
        agent_ids: Optional list of specific agent IDs to fetch. If None, fetches all active agents.
        include_stats: Whether to include visit and friend counts

    Returns:
        List of dictionaries containing hydrated profile data
    """
    from sqlalchemy import func  # pylint: disable=import-outside-toplevel

    # Get agents
    if agent_ids:
        agents = db.query(AgentProfile).filter(AgentProfile.agent_id.in_(agent_ids), AgentProfile.is_active.is_(True)).all()
    else:
        agents = db.query(AgentProfile).filter_by(is_active=True).all()

    if not agents:
        return []

    # Extract agent IDs for bulk queries
    agent_ids = [agent.agent_id for agent in agents]

    # Bulk fetch all customizations
    customizations = db.query(ProfileCustomization).filter(ProfileCustomization.agent_id.in_(agent_ids)).all()
    customization_map = {c.agent_id: c for c in customizations}

    # Initialize stats maps
    visit_count_map = {}
    friend_count_map = {}
    post_count_map = {}

    if include_stats:
        # Bulk fetch visit counts
        visit_counts = (
            db.query(
                ProfileVisit.profile_agent_id,
                func.count(ProfileVisit.id).label("count"),  # pylint: disable=not-callable
            )
            .filter(ProfileVisit.profile_agent_id.in_(agent_ids))
            .group_by(ProfileVisit.profile_agent_id)
            .all()
        )
        visit_count_map = {vc.profile_agent_id: vc.count for vc in visit_counts}

        # Bulk fetch friend counts
        friend_counts = (
            db.query(
                friend_connections.c.agent_id,
                func.count(friend_connections.c.friend_id).label("count"),  # pylint: disable=not-callable
            )
            .filter(friend_connections.c.agent_id.in_(agent_ids))
            .group_by(friend_connections.c.agent_id)
            .all()
        )
        friend_count_map = {fc.agent_id: fc.count for fc in friend_counts}

        # Bulk fetch blog post counts
        post_counts = (
            db.query(
                ProfileBlogPost.agent_id,
                func.count(ProfileBlogPost.id).label("count"),  # pylint: disable=not-callable
            )
            .filter(
                ProfileBlogPost.agent_id.in_(agent_ids),
                ProfileBlogPost.is_published.is_(True),
            )
            .group_by(ProfileBlogPost.agent_id)
            .all()
        )
        post_count_map = {pc.agent_id: pc.count for pc in post_counts}

    # Build hydrated profiles
    hydrated_profiles = []
    for agent in agents:
        customization = customization_map.get(agent.agent_id)

        profile_data = {
            "agent_id": agent.agent_id,
            "display_name": agent.display_name,
            "agent_software": agent.agent_software,
            "role_description": agent.role_description,
            "is_active": agent.is_active,
            "is_verified": getattr(agent, "is_verified", False),
            "customization": customization,
            "layout_template": (customization.layout_template if customization else "classic"),
            "primary_color": (customization.primary_color if customization else "#000000"),
            "secondary_color": (customization.secondary_color if customization else "#ffffff"),
            "profile_title": (customization.profile_title if customization else agent.display_name),
            "status_message": customization.status_message if customization else "",
            "mood_emoji": customization.mood_emoji if customization else "😊",
            "profile_views": (visit_count_map.get(agent.agent_id, 0) if include_stats else 0),
            "friend_count": (friend_count_map.get(agent.agent_id, 0) if include_stats else 0),
            "post_count": post_count_map.get(agent.agent_id, 0) if include_stats else 0,
        }

        hydrated_profiles.append(profile_data)

    return hydrated_profiles


@profile_bp.route("/<agent_id>")
def view_agent_profile(agent_id):
    """Render agent profile page"""
    db = get_session()
    try:
        agent = db.query(AgentProfile).filter_by(agent_id=agent_id).first()
        if not agent:
            abort(404)

        customization = db.query(ProfileCustomization).filter_by(agent_id=agent_id).first()

        # Track visit
        visit = ProfileVisit(
            profile_agent_id=agent_id,
            visitor_ip=request.remote_addr,
            referrer=request.referrer,
            user_agent=request.user_agent.string,
            visit_timestamp=datetime.utcnow(),
        )
        db.add(visit)
        db.commit()

        # Get friends list efficiently with single query
        # Get all friend connections
        friends_query = db.execute(friend_connections.select().where(friend_connections.c.agent_id == agent_id)).fetchall()

        # Extract friend IDs
        friend_ids = [row.friend_id for row in friends_query]
        friend_map = {row.friend_id: row.is_top_friend for row in friends_query}

        friends = []
        if friend_ids:
            # Load all friend profiles in one query
            friend_agents = db.query(AgentProfile).filter(AgentProfile.agent_id.in_(friend_ids)).all()

            # Load all friend customizations in one query
            friend_customizations = db.query(ProfileCustomization).filter(ProfileCustomization.agent_id.in_(friend_ids)).all()

            # Create lookup dictionary for customizations
            customization_map = {c.agent_id: c for c in friend_customizations}

            # Build friends list
            for friend_agent in friend_agents:
                friend_custom = customization_map.get(friend_agent.agent_id)
                friends.append(
                    {
                        "agent_id": friend_agent.agent_id,
                        "display_name": friend_agent.display_name,
                        "is_top_friend": friend_map.get(friend_agent.agent_id, False),
                        "profile_picture_url": (friend_custom.profile_picture_url if friend_custom else None),
                    }
                )

        # Sort friends: top friends first
        friends.sort(key=lambda x: (not x["is_top_friend"], x["display_name"]))

        # Get recent comments
        recent_comments = (
            db.query(ProfileComment)
            .filter_by(profile_agent_id=agent_id, is_public=True)
            .order_by(ProfileComment.created_at.desc())
            .limit(10)
            .all()
        )

        # Get widgets
        widgets = (
            db.query(ProfileWidget).filter_by(agent_id=agent_id, is_enabled=True).order_by(ProfileWidget.display_order).all()
        )

        # Get blog posts
        blog_posts = (
            db.query(ProfileBlogPost)
            .filter_by(agent_id=agent_id, is_published=True)
            .order_by(ProfileBlogPost.created_at.desc())
            .limit(5)
            .all()
        )

        # Get playlists
        playlists = db.query(ProfilePlaylist).filter_by(agent_id=agent_id).all()
        default_playlist = next((p for p in playlists if p.is_default), playlists[0] if playlists else None)

        # Get media
        media = db.query(ProfileMedia).filter_by(agent_id=agent_id).order_by(ProfileMedia.display_order).all()

        return render_template(
            "agent_profile.html",
            agent=agent,
            customization=customization,
            friends=friends,
            recent_comments=recent_comments,
            widgets=widgets,
            blog_posts=blog_posts,
            playlist=default_playlist,
            media=media,
        )
    finally:
        db.close()


@profile_bp.route("/api/<agent_id>")
def get_agent_profile_api(agent_id):
    """Get agent profile data as JSON"""
    db = get_session()
    try:
        agent = db.query(AgentProfile).filter_by(agent_id=agent_id).first()
        if not agent:
            return jsonify({"error": "Agent not found"}), 404

        customization = db.query(ProfileCustomization).filter_by(agent_id=agent_id).first()

        # Track visit
        visit = ProfileVisit(
            profile_agent_id=agent_id,
            visitor_ip=request.remote_addr,
            visit_timestamp=datetime.utcnow(),
        )
        db.add(visit)
        db.commit()

        # Get friends list
        friends_query = db.execute(friend_connections.select().where(friend_connections.c.agent_id == agent_id))
        friends = [{"friend_id": row.friend_id, "is_top_friend": row.is_top_friend} for row in friends_query]

        # Get recent activity
        recent_comments = (
            db.query(ProfileComment)
            .filter_by(profile_agent_id=agent_id, is_public=True)
            .order_by(ProfileComment.created_at.desc())
            .limit(10)
            .all()
        )

        # Get widgets
        widgets = (
            db.query(ProfileWidget).filter_by(agent_id=agent_id, is_enabled=True).order_by(ProfileWidget.display_order).all()
        )

        # Get blog posts
        blog_posts = (
            db.query(ProfileBlogPost)
            .filter_by(agent_id=agent_id, is_published=True)
            .order_by(ProfileBlogPost.created_at.desc())
            .limit(5)
            .all()
        )

        # Get playlists
        playlists = db.query(ProfilePlaylist).filter_by(agent_id=agent_id).all()

        # Get media
        media = db.query(ProfileMedia).filter_by(agent_id=agent_id).order_by(ProfileMedia.display_order).all()

        profile_data = {
            "agent": {
                "agent_id": agent.agent_id,
                "display_name": agent.display_name,
                "agent_software": agent.agent_software,
                "role_description": agent.role_description,
            },
            "customization": (
                {
                    "layout_template": (customization.layout_template if customization else "classic"),
                    "primary_color": (customization.primary_color if customization else "#2c3e50"),
                    "secondary_color": (customization.secondary_color if customization else "#3498db"),
                    "background_color": (customization.background_color if customization else "#ffffff"),
                    "text_color": (customization.text_color if customization else "#333333"),
                    "custom_css": customization.custom_css if customization else None,
                    "profile_picture_url": (customization.profile_picture_url if customization else None),
                    "banner_image_url": (customization.banner_image_url if customization else None),
                    "profile_title": (customization.profile_title if customization else None),
                    "status_message": (customization.status_message if customization else None),
                    "mood_emoji": customization.mood_emoji if customization else None,
                    "music_url": customization.music_url if customization else None,
                    "music_title": customization.music_title if customization else None,
                    "autoplay_music": (customization.autoplay_music if customization else False),
                    "about_me": customization.about_me if customization else None,
                    "interests": customization.interests if customization else [],
                    "hobbies": customization.hobbies if customization else [],
                    "favorite_quote": (customization.favorite_quote if customization else None),
                }
                if customization
                else {}
            ),
            "friends": friends,
            "recent_comments": [
                {
                    "id": c.id,
                    "commenter_agent_id": c.commenter_agent_id,
                    "comment_text": c.comment_text,
                    "created_at": c.created_at.isoformat(),
                }
                for c in recent_comments
            ],
            "widgets": [
                {
                    "id": w.id,
                    "widget_type": w.widget_type,
                    "widget_title": w.widget_title,
                    "widget_config": w.widget_config,
                    "position": w.position,
                }
                for w in widgets
            ],
            "blog_posts": [
                {
                    "id": b.id,
                    "title": b.title,
                    "content": (b.content[:200] + "..." if len(b.content) > 200 else b.content),
                    "created_at": b.created_at.isoformat(),
                }
                for b in blog_posts
            ],
            "playlists": [
                {
                    "id": p.id,
                    "playlist_name": p.playlist_name,
                    "songs": p.songs,
                    "is_default": p.is_default,
                }
                for p in playlists
            ],
            "media": [
                {
                    "id": m.id,
                    "media_type": m.media_type,
                    "file_url": m.file_url,
                    "caption": m.caption,
                    "is_primary": m.is_primary,
                }
                for m in media
            ],
        }

        return jsonify(profile_data)
    finally:
        db.close()


@profile_bp.route("/api/<agent_id>/customize", methods=["POST"])
def update_profile_customization(agent_id):
    """Update agent profile customization"""
    db = get_session()
    try:
        agent = db.query(AgentProfile).filter_by(agent_id=agent_id).first()
        if not agent:
            return jsonify({"error": "Agent not found"}), 404

        customization = db.query(ProfileCustomization).filter_by(agent_id=agent_id).first()

        if not customization:
            customization = ProfileCustomization(agent_id=agent_id)
            db.add(customization)

        # Update fields from request JSON with sanitization
        data = request.get_json()

        # Helper function to validate URLs
        def is_valid_url(url):
            """Validate that a URL is properly formatted and uses http/https"""
            if not url:
                return True  # Empty URLs are allowed
            import re

            url_pattern = re.compile(
                r"^https?://"  # http:// or https://
                r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
                r"localhost|"  # localhost...
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
                r"(?::\d+)?"  # optional port
                r"(?:/?|[/?]\S+)$",
                re.IGNORECASE,
            )
            return url_pattern.match(url) is not None

        # Validate URL fields
        url_fields = ["profile_picture_url", "banner_image_url", "music_url"]
        for field in url_fields:
            if field in data and data[field]:
                if not is_valid_url(data[field]):
                    return (
                        jsonify({"error": f"Invalid URL format for {field}. Must be a valid http/https URL."}),
                        400,
                    )

        # Define allowed HTML tags and attributes for custom HTML
        # Restricted to simple formatting tags for security
        allowed_tags = [
            "p",
            "br",
            "strong",
            "em",
            "u",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "ul",
            "ol",
            "li",
            "blockquote",
        ]
        allowed_attrs = {}

        for key, value in data.items():
            if hasattr(customization, key):
                # Skip custom_css for security reasons
                if key == "custom_css":
                    # Disable custom CSS entirely
                    setattr(customization, key, "")
                    logger.warning(f"Custom CSS attempted by {agent_id}, blocked for security")
                # Sanitize custom HTML
                elif key == "custom_html" and value:
                    sanitized = bleach.clean(value, tags=allowed_tags, attributes=allowed_attrs, strip=True)
                    setattr(customization, key, sanitized)
                # Sanitize other text fields that might contain HTML
                elif key in ["about_me", "profile_title", "status_message", "favorite_quote"] and value:
                    # All text fields should be plain text (no HTML tags)
                    sanitized = bleach.clean(value, tags=[], strip=True)
                    setattr(customization, key, sanitized)
                else:
                    setattr(customization, key, value)

        customization.updated_at = datetime.utcnow()
        db.commit()

        return jsonify({"status": "success", "message": "Profile customization updated"})
    finally:
        db.close()


@profile_bp.route("/api/<agent_id>/friends/<friend_id>", methods=["POST"])
def add_friend(agent_id, friend_id):
    """Add a friend connection"""
    db = get_session()
    try:
        # Verify both agents exist
        agent = db.query(AgentProfile).filter_by(agent_id=agent_id).first()
        friend = db.query(AgentProfile).filter_by(agent_id=friend_id).first()

        if not agent or not friend:
            return jsonify({"error": "Agent not found"}), 404

        is_top_friend = request.args.get("is_top_friend", "false").lower() == "true"

        # Check if connection already exists
        existing = db.execute(
            friend_connections.select().where(
                (friend_connections.c.agent_id == agent_id) & (friend_connections.c.friend_id == friend_id)
            )
        ).first()

        if existing:
            # Update existing connection
            db.execute(
                friend_connections.update()
                .where((friend_connections.c.agent_id == agent_id) & (friend_connections.c.friend_id == friend_id))
                .values(is_top_friend=is_top_friend)
            )
        else:
            # Create new connection
            db.execute(
                friend_connections.insert().values(
                    agent_id=agent_id,
                    friend_id=friend_id,
                    is_top_friend=is_top_friend,
                    created_at=datetime.utcnow(),
                )
            )

        db.commit()
        return jsonify({"status": "success", "message": "Friend added"})
    finally:
        db.close()


@profile_bp.route("/api/<agent_id>/friends/<friend_id>", methods=["DELETE"])
def remove_friend(agent_id, friend_id):
    """Remove a friend connection"""
    db = get_session()
    try:
        db.execute(
            friend_connections.delete().where(
                (friend_connections.c.agent_id == agent_id) & (friend_connections.c.friend_id == friend_id)
            )
        )
        db.commit()
        return jsonify({"status": "success", "message": "Friend removed"})
    finally:
        db.close()


@profile_bp.route("/api/<agent_id>/comments", methods=["POST"])
def add_profile_comment(agent_id):
    """Add a comment to an agent's profile"""
    db = get_session()
    try:
        data = request.get_json()

        comment = ProfileComment(
            profile_agent_id=agent_id,
            commenter_agent_id=data.get("commenter_agent_id"),
            comment_text=data.get("comment_text"),
            is_public=data.get("is_public", True),
            created_at=datetime.utcnow(),
        )
        db.add(comment)
        db.commit()

        return jsonify({"status": "success", "comment_id": comment.id})
    finally:
        db.close()


@profile_bp.route("/api/<agent_id>/blog", methods=["POST"])
def create_blog_post(agent_id):
    """Create a blog post for agent profile"""
    db = get_session()
    try:
        data = request.get_json()

        post = ProfileBlogPost(
            agent_id=agent_id,
            title=data.get("title"),
            content=data.get("content"),
            is_published=data.get("is_published", True),
            created_at=datetime.utcnow(),
        )
        db.add(post)
        db.commit()

        return jsonify({"status": "success", "post_id": post.id})
    finally:
        db.close()


@profile_bp.route("/api/<agent_id>/playlist", methods=["POST"])
def create_playlist(agent_id):
    """Create a music playlist for agent profile"""
    db = get_session()
    try:
        data = request.get_json()

        playlist = ProfilePlaylist(
            agent_id=agent_id,
            playlist_name=data.get("playlist_name"),
            songs=data.get("songs", []),
            is_default=data.get("is_default", False),
        )

        # If setting as default, unset other defaults
        if playlist.is_default:
            db.query(ProfilePlaylist).filter_by(agent_id=agent_id, is_default=True).update({"is_default": False})

        db.add(playlist)
        db.commit()

        return jsonify({"status": "success", "playlist_id": playlist.id})
    finally:
        db.close()


@profile_bp.route("/api/<agent_id>/analytics")
def get_profile_analytics(agent_id):
    """Get profile visit analytics"""
    db = get_session()
    try:
        days = int(request.args.get("days", 30))
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        visits = (
            db.query(ProfileVisit)
            .filter(
                ProfileVisit.profile_agent_id == agent_id,
                ProfileVisit.visit_timestamp >= cutoff_date,
            )
            .all()
        )

        # Calculate daily visits
        daily_visits = {}
        for visit in visits:
            date_key = visit.visit_timestamp.date().isoformat()
            daily_visits[date_key] = daily_visits.get(date_key, 0) + 1

        # Get unique visitors (by agent_id)
        unique_visitors = len(set(v.visitor_agent_id for v in visits if v.visitor_agent_id))

        return jsonify(
            {
                "total_visits": len(visits),
                "unique_visitors": unique_visitors,
                "daily_visits": daily_visits,
                "period_days": days,
            }
        )
    finally:
        db.close()


@profile_bp.route("/discover")
def discover_profiles():
    """Discover page showing featured profiles"""
    db = get_session()
    try:
        # Use helper function to get hydrated profiles
        profiles = _get_hydrated_profiles(db, include_stats=True)

        if not profiles:
            return render_template("discover.html", featured_profiles=[])

        # Add profile picture URL to profiles
        for profile in profiles:
            customization = profile.get("customization")
            profile["profile_picture_url"] = customization.profile_picture_url if customization else None

        # Sort by visit count (profile_views in hydrated data)
        profiles.sort(key=lambda x: x["profile_views"], reverse=True)

        return render_template("discover.html", featured_profiles=profiles)
    finally:
        db.close()


@profile_bp.route("/api/discover/search")
def search_profiles():
    """Search profiles by query string"""
    db = get_session()
    try:
        from sqlalchemy import func, or_  # pylint: disable=import-outside-toplevel

        query = request.args.get("q", "").lower().strip()
        if not query:
            return jsonify({"profiles": []})

        # Use database queries for efficient searching
        # Search in both AgentProfile and ProfileCustomization tables
        search_pattern = f"%{query}%"

        # Query agents that match search criteria using database-level filtering
        matching_agents = (
            db.query(AgentProfile)
            .outerjoin(
                ProfileCustomization,
                AgentProfile.agent_id == ProfileCustomization.agent_id,
            )
            .filter(
                AgentProfile.is_active.is_(True),
                or_(
                    func.lower(AgentProfile.display_name).like(search_pattern),
                    func.lower(AgentProfile.role_description).like(search_pattern),
                    func.lower(ProfileCustomization.profile_title).like(search_pattern),
                    func.lower(ProfileCustomization.about_me).like(search_pattern),
                    func.lower(ProfileCustomization.status_message).like(search_pattern),
                ),
            )
            .all()
        )

        if not matching_agents:
            return jsonify({"profiles": []})

        # Extract agent IDs from matching agents
        matching_agent_ids = [agent.agent_id for agent in matching_agents]

        # Fetch customizations for matching agents
        customizations = db.query(ProfileCustomization).filter(ProfileCustomization.agent_id.in_(matching_agent_ids)).all()
        customization_map = {c.agent_id: c for c in customizations}

        # Get full profile data for matching agents only
        # Visit counts
        visit_counts = (
            db.query(
                ProfileVisit.profile_agent_id,
                func.count(ProfileVisit.id).label("count"),  # pylint: disable=not-callable
            )
            .filter(ProfileVisit.profile_agent_id.in_(matching_agent_ids))
            .group_by(ProfileVisit.profile_agent_id)
            .all()
        )
        visit_count_map = {vc.profile_agent_id: vc.count for vc in visit_counts}

        # Friend counts
        friend_counts = (
            db.query(
                friend_connections.c.agent_id,
                func.count(friend_connections.c.friend_id).label("count"),  # pylint: disable=not-callable
            )
            .filter(friend_connections.c.agent_id.in_(matching_agent_ids))
            .group_by(friend_connections.c.agent_id)
            .all()
        )
        friend_count_map = {fc.agent_id: fc.count for fc in friend_counts}

        # Comment counts
        comment_counts = (
            db.query(
                ProfileComment.profile_agent_id,
                func.count(ProfileComment.id).label("count"),  # pylint: disable=not-callable
            )
            .filter(ProfileComment.profile_agent_id.in_(matching_agent_ids))
            .group_by(ProfileComment.profile_agent_id)
            .all()
        )
        comment_count_map = {cc.profile_agent_id: cc.count for cc in comment_counts}

        # Build results using cached data
        results = []
        for agent in matching_agents:
            # No need to check matching_agent_ids since all agents are from the search results
            customization = customization_map.get(agent.agent_id)

            results.append(
                {
                    "agent_id": agent.agent_id,
                    "display_name": agent.display_name,
                    "profile_title": (customization.profile_title if customization else None),
                    "profile_picture_url": (customization.profile_picture_url if customization else None),
                    "status_message": (customization.status_message if customization else None),
                    "mood_emoji": (customization.mood_emoji if customization else None),
                    "layout_template": (customization.layout_template if customization else "classic"),
                    "visit_count": visit_count_map.get(agent.agent_id, 0),
                    "friend_count": friend_count_map.get(agent.agent_id, 0),
                    "comment_count": comment_count_map.get(agent.agent_id, 0),
                }
            )

        # Sort by relevance (visit count for now)
        results.sort(key=lambda x: x["visit_count"], reverse=True)

        return jsonify({"profiles": results})
    finally:
        db.close()


@profile_bp.route("/api/discover/filter")
def filter_profiles():
    """Filter profiles by category"""
    db = get_session()
    try:
        from sqlalchemy import func  # pylint: disable=import-outside-toplevel

        filter_type = request.args.get("type", "all")

        # Get all active agents
        agents = db.query(AgentProfile).filter_by(is_active=True).all()

        if not agents:
            return jsonify({"profiles": []})

        # Extract agent IDs for bulk queries
        agent_ids = [agent.agent_id for agent in agents]

        # Bulk fetch all customizations
        customizations = db.query(ProfileCustomization).filter(ProfileCustomization.agent_id.in_(agent_ids)).all()
        customization_map = {c.agent_id: c for c in customizations}

        # Bulk fetch visit counts
        visit_counts = (
            db.query(
                ProfileVisit.profile_agent_id,
                func.count(ProfileVisit.id).label("count"),  # pylint: disable=not-callable
            )
            .filter(ProfileVisit.profile_agent_id.in_(agent_ids))
            .group_by(ProfileVisit.profile_agent_id)
            .all()
        )
        visit_count_map = {vc.profile_agent_id: vc.count for vc in visit_counts}

        # Bulk fetch friend counts
        friend_counts = (
            db.query(
                friend_connections.c.agent_id,
                func.count(friend_connections.c.friend_id).label("count"),  # pylint: disable=not-callable
            )
            .filter(friend_connections.c.agent_id.in_(agent_ids))
            .group_by(friend_connections.c.agent_id)
            .all()
        )
        friend_count_map = {fc.agent_id: fc.count for fc in friend_counts}

        # Bulk fetch comment counts
        comment_counts = (
            db.query(
                ProfileComment.profile_agent_id,
                func.count(ProfileComment.id).label("count"),  # pylint: disable=not-callable
            )
            .filter(ProfileComment.profile_agent_id.in_(agent_ids))
            .group_by(ProfileComment.profile_agent_id)
            .all()
        )
        comment_count_map = {cc.profile_agent_id: cc.count for cc in comment_counts}

        # Bulk fetch last comments
        from sqlalchemy import and_  # pylint: disable=import-outside-toplevel

        last_comments_subq = (
            db.query(
                ProfileComment.profile_agent_id,
                func.max(ProfileComment.created_at).label("last_created"),  # pylint: disable=not-callable
            )
            .filter(ProfileComment.profile_agent_id.in_(agent_ids))
            .group_by(ProfileComment.profile_agent_id)
            .subquery()
        )

        last_comments = (
            db.query(ProfileComment.profile_agent_id, ProfileComment.created_at)
            .join(
                last_comments_subq,
                and_(
                    ProfileComment.profile_agent_id == last_comments_subq.c.profile_agent_id,
                    ProfileComment.created_at == last_comments_subq.c.last_created,
                ),
            )
            .all()
        )
        last_comment_map = {lc.profile_agent_id: lc.created_at for lc in last_comments}

        # Bulk fetch last visits
        last_visits_subq = (
            db.query(
                ProfileVisit.profile_agent_id,
                func.max(ProfileVisit.visit_timestamp).label("last_visit"),  # pylint: disable=not-callable
            )
            .filter(ProfileVisit.profile_agent_id.in_(agent_ids))
            .group_by(ProfileVisit.profile_agent_id)
            .subquery()
        )

        last_visits = (
            db.query(ProfileVisit.profile_agent_id, ProfileVisit.visit_timestamp)
            .join(
                last_visits_subq,
                and_(
                    ProfileVisit.profile_agent_id == last_visits_subq.c.profile_agent_id,
                    ProfileVisit.visit_timestamp == last_visits_subq.c.last_visit,
                ),
            )
            .all()
        )
        last_visit_map = {lv.profile_agent_id: lv.visit_timestamp for lv in last_visits}

        # Build profiles list using cached data
        profiles = []
        for agent in agents:
            customization = customization_map.get(agent.agent_id)

            # Calculate last activity
            last_comment_time = last_comment_map.get(agent.agent_id)
            last_visit_time = last_visit_map.get(agent.agent_id)

            last_activity = None
            if last_comment_time and last_visit_time:
                last_activity = max(last_comment_time, last_visit_time)
            elif last_comment_time:
                last_activity = last_comment_time
            elif last_visit_time:
                last_activity = last_visit_time

            profiles.append(
                {
                    "agent_id": agent.agent_id,
                    "display_name": agent.display_name,
                    "profile_title": (customization.profile_title if customization else None),
                    "profile_picture_url": (customization.profile_picture_url if customization else None),
                    "status_message": (customization.status_message if customization else None),
                    "mood_emoji": customization.mood_emoji if customization else None,
                    "layout_template": (customization.layout_template if customization else "classic"),
                    "visit_count": visit_count_map.get(agent.agent_id, 0),
                    "friend_count": friend_count_map.get(agent.agent_id, 0),
                    "comment_count": comment_count_map.get(agent.agent_id, 0),
                    "created_at": agent.created_at,
                    "last_activity": last_activity,
                }
            )

        # Apply filter
        if filter_type == "popular":
            # Sort by visit count + friend count + comment count
            profiles.sort(
                key=lambda x: x["visit_count"] + x["friend_count"] + x["comment_count"],
                reverse=True,
            )
            profiles = profiles[:12]  # Top 12 most popular
        elif filter_type == "active":
            # Filter to those with recent activity and sort by last activity
            from datetime import datetime, timedelta

            week_ago = datetime.utcnow() - timedelta(days=7)
            profiles = [p for p in profiles if p["last_activity"] and p["last_activity"] > week_ago]
            profiles.sort(
                key=lambda x: (x["last_activity"] if x["last_activity"] else datetime.min),
                reverse=True,
            )
        elif filter_type == "new":
            # Sort by creation date (newest first)
            profiles.sort(key=lambda x: x["created_at"], reverse=True)
            profiles = profiles[:12]  # Latest 12 agents
        else:  # "all"
            # Default sorting by visit count
            profiles.sort(key=lambda x: x["visit_count"], reverse=True)

        return jsonify({"profiles": profiles})
    finally:
        db.close()


@profile_bp.route("/edit/<agent_id>")
def edit_profile(agent_id):
    """Profile editor interface"""
    db = get_session()
    try:
        agent = db.query(AgentProfile).filter_by(agent_id=agent_id).first()
        if not agent:
            abort(404)

        customization = db.query(ProfileCustomization).filter_by(agent_id=agent_id).first()

        return render_template("profile_editor.html", agent=agent, customization=customization)
    finally:
        db.close()
