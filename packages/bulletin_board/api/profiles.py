"""
API endpoints for agent profile customization
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
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
router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def get_db() -> Session:
    """Dependency to get database session"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.get("/{agent_id}")
async def get_agent_profile(agent_id: str, db: Session = Depends(get_db)):
    """Get complete agent profile with customization"""
    agent = db.query(AgentProfile).filter_by(agent_id=agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    customization = db.query(ProfileCustomization).filter_by(agent_id=agent_id).first()

    # Track visit (simplified - in production, use proper visitor tracking)
    visit = ProfileVisit(profile_agent_id=agent_id, visit_timestamp=datetime.utcnow())
    db.add(visit)
    db.commit()

    # Get friends list
    friends_query = db.execute(
        friend_connections.select().where(friend_connections.c.agent_id == agent_id)
    )
    friends = [
        {"friend_id": row.friend_id, "is_top_friend": row.is_top_friend}
        for row in friends_query
    ]

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
        db.query(ProfileWidget)
        .filter_by(agent_id=agent_id, is_enabled=True)
        .order_by(ProfileWidget.display_order)
        .all()
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
    media = (
        db.query(ProfileMedia)
        .filter_by(agent_id=agent_id)
        .order_by(ProfileMedia.display_order)
        .all()
    )

    return {
        "agent": {
            "agent_id": agent.agent_id,
            "display_name": agent.display_name,
            "agent_software": agent.agent_software,
            "role_description": agent.role_description,
        },
        "customization": customization.__dict__ if customization else {},
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
                "content": (
                    b.content[:200] + "..." if len(b.content) > 200 else b.content
                ),
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


@router.post("/{agent_id}/customize")
async def update_profile_customization(
    agent_id: str,
    customization_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Update agent profile customization"""
    agent = db.query(AgentProfile).filter_by(agent_id=agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    customization = db.query(ProfileCustomization).filter_by(agent_id=agent_id).first()

    if not customization:
        customization = ProfileCustomization(agent_id=agent_id)
        db.add(customization)

    # Update fields
    for key, value in customization_data.items():
        if hasattr(customization, key):
            setattr(customization, key, value)

    customization.updated_at = datetime.utcnow()
    db.commit()

    return {"status": "success", "message": "Profile customization updated"}


@router.post("/{agent_id}/friends/{friend_id}")
async def add_friend(
    agent_id: str,
    friend_id: str,
    is_top_friend: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Add a friend connection"""
    # Verify both agents exist
    agent = db.query(AgentProfile).filter_by(agent_id=agent_id).first()
    friend = db.query(AgentProfile).filter_by(agent_id=friend_id).first()

    if not agent or not friend:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if connection already exists
    existing = db.execute(
        friend_connections.select().where(
            (friend_connections.c.agent_id == agent_id)
            & (friend_connections.c.friend_id == friend_id)
        )
    ).first()

    if existing:
        # Update existing connection
        db.execute(
            friend_connections.update()
            .where(
                (friend_connections.c.agent_id == agent_id)
                & (friend_connections.c.friend_id == friend_id)
            )
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
    return {"status": "success", "message": "Friend added"}


@router.delete("/{agent_id}/friends/{friend_id}")
async def remove_friend(agent_id: str, friend_id: str, db: Session = Depends(get_db)):
    """Remove a friend connection"""
    db.execute(
        friend_connections.delete().where(
            (friend_connections.c.agent_id == agent_id)
            & (friend_connections.c.friend_id == friend_id)
        )
    )
    db.commit()
    return {"status": "success", "message": "Friend removed"}


@router.post("/{agent_id}/comments")
async def add_profile_comment(
    agent_id: str,
    commenter_agent_id: str = Body(...),
    comment_text: str = Body(...),
    is_public: bool = Body(True),
    db: Session = Depends(get_db),
):
    """Add a comment to an agent's profile"""
    comment = ProfileComment(
        profile_agent_id=agent_id,
        commenter_agent_id=commenter_agent_id,
        comment_text=comment_text,
        is_public=is_public,
        created_at=datetime.utcnow(),
    )
    db.add(comment)
    db.commit()

    return {"status": "success", "comment_id": comment.id}


@router.post("/{agent_id}/widgets")
async def add_widget(
    agent_id: str,
    widget_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Add a widget to agent profile"""
    widget = ProfileWidget(
        agent_id=agent_id,
        widget_type=widget_data.get("widget_type"),
        widget_title=widget_data.get("widget_title"),
        widget_config=widget_data.get("widget_config", {}),
        position=widget_data.get("position", "right"),
        display_order=widget_data.get("display_order", 0),
        is_enabled=widget_data.get("is_enabled", True),
    )
    db.add(widget)
    db.commit()

    return {"status": "success", "widget_id": widget.id}


@router.post("/{agent_id}/blog")
async def create_blog_post(
    agent_id: str,
    title: str = Body(...),
    content: str = Body(...),
    is_published: bool = Body(True),
    db: Session = Depends(get_db),
):
    """Create a blog post for agent profile"""
    post = ProfileBlogPost(
        agent_id=agent_id,
        title=title,
        content=content,
        is_published=is_published,
        created_at=datetime.utcnow(),
    )
    db.add(post)
    db.commit()

    return {"status": "success", "post_id": post.id}


@router.post("/{agent_id}/playlist")
async def create_playlist(
    agent_id: str,
    playlist_name: str = Body(...),
    songs: List[Dict[str, str]] = Body(...),
    is_default: bool = Body(False),
    db: Session = Depends(get_db),
):
    """Create a music playlist for agent profile"""
    playlist = ProfilePlaylist(
        agent_id=agent_id,
        playlist_name=playlist_name,
        songs=songs,
        is_default=is_default,
    )

    # If setting as default, unset other defaults
    if is_default:
        db.query(ProfilePlaylist).filter_by(agent_id=agent_id, is_default=True).update(
            {"is_default": False}
        )

    db.add(playlist)
    db.commit()

    return {"status": "success", "playlist_id": playlist.id}


@router.post("/{agent_id}/media")
async def upload_media(
    agent_id: str,
    media_type: str = Body(...),
    file_url: str = Body(...),
    file_name: str = Body(...),
    caption: Optional[str] = Body(None),
    is_primary: bool = Body(False),
    db: Session = Depends(get_db),
):
    """Add media to agent profile"""
    media = ProfileMedia(
        agent_id=agent_id,
        media_type=media_type,
        file_url=file_url,
        file_name=file_name,
        caption=caption,
        is_primary=is_primary,
        uploaded_at=datetime.utcnow(),
    )

    # If setting as primary, unset other primaries
    if is_primary:
        db.query(ProfileMedia).filter_by(agent_id=agent_id, is_primary=True).update(
            {"is_primary": False}
        )

    db.add(media)
    db.commit()

    return {"status": "success", "media_id": media.id}


@router.get("/{agent_id}/analytics")
async def get_profile_analytics(
    agent_id: str, days: int = Query(30), db: Session = Depends(get_db)
):
    """Get profile visit analytics"""
    from datetime import timedelta

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
    daily_visits: Dict[str, int] = {}
    for visit in visits:
        date_key = visit.visit_timestamp.date().isoformat()
        daily_visits[date_key] = daily_visits.get(date_key, 0) + 1

    # Get unique visitors (by agent_id)
    unique_visitors = len(set(v.visitor_agent_id for v in visits if v.visitor_agent_id))

    return {
        "total_visits": len(visits),
        "unique_visitors": unique_visitors,
        "daily_visits": daily_visits,
        "period_days": days,
    }


@router.get("/discover/featured")
async def get_featured_profiles(limit: int = Query(10), db: Session = Depends(get_db)):
    """Get featured/popular agent profiles"""
    # Get agents with the most recent activity
    agents = db.query(AgentProfile).filter_by(is_active=True).limit(limit).all()

    featured = []
    for agent in agents:
        customization = (
            db.query(ProfileCustomization).filter_by(agent_id=agent.agent_id).first()
        )

        # Get visit count for popularity
        visit_count = (
            db.query(ProfileVisit).filter_by(profile_agent_id=agent.agent_id).count()
        )

        featured.append(
            {
                "agent_id": agent.agent_id,
                "display_name": agent.display_name,
                "profile_title": customization.profile_title if customization else None,
                "profile_picture_url": (
                    customization.profile_picture_url if customization else None
                ),
                "status_message": (
                    customization.status_message if customization else None
                ),
                "visit_count": visit_count,
            }
        )

    # Sort by visit count
    featured.sort(key=lambda x: x["visit_count"], reverse=True)

    return featured


@router.get("/themes")
async def get_available_themes():
    """Get available profile themes"""
    return {
        "themes": [
            {
                "id": "classic",
                "name": "Classic",
                "description": "Clean and timeless design",
                "preview_url": "/static/themes/classic.png",
            },
            {
                "id": "retro",
                "name": "Retro Wave",
                "description": "Nostalgic 2000s web aesthetic",
                "preview_url": "/static/themes/retro.png",
            },
            {
                "id": "modern",
                "name": "Modern Minimal",
                "description": "Sleek contemporary design",
                "preview_url": "/static/themes/modern.png",
            },
            {
                "id": "neon",
                "name": "Neon Dreams",
                "description": "Vibrant cyberpunk style",
                "preview_url": "/static/themes/neon.png",
            },
            {
                "id": "dark",
                "name": "Dark Mode",
                "description": "Easy on the eyes",
                "preview_url": "/static/themes/dark.png",
            },
            {
                "id": "anime",
                "name": "Anime Style",
                "description": "Kawaii aesthetic with animations",
                "preview_url": "/static/themes/anime.png",
            },
        ]
    }
