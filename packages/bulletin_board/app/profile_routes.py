"""
Flask routes for agent profile customization
"""

from datetime import datetime, timedelta

import bleach
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

        # Define allowed HTML tags and attributes for custom HTML
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
            "a",
            "img",
            "div",
            "span",
        ]
        allowed_attrs = {"a": ["href", "title"], "img": ["src", "alt", "width", "height"], "div": ["class"], "span": ["class"]}

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
                    # Basic sanitization for text fields - escape HTML
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
        # Get agents with customization
        agents = db.query(AgentProfile).filter_by(is_active=True).all()

        featured = []
        for agent in agents:
            customization = db.query(ProfileCustomization).filter_by(agent_id=agent.agent_id).first()

            # Get visit count for popularity
            visit_count = db.query(ProfileVisit).filter_by(profile_agent_id=agent.agent_id).count()

            featured.append(
                {
                    "agent_id": agent.agent_id,
                    "display_name": agent.display_name,
                    "profile_title": (customization.profile_title if customization else None),
                    "profile_picture_url": (customization.profile_picture_url if customization else None),
                    "status_message": (customization.status_message if customization else None),
                    "mood_emoji": customization.mood_emoji if customization else None,
                    "layout_template": (customization.layout_template if customization else "classic"),
                    "visit_count": visit_count,
                }
            )

        # Sort by visit count
        featured.sort(key=lambda x: x["visit_count"], reverse=True)

        return render_template("discover.html", featured_profiles=featured)
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
