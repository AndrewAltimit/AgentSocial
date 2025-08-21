import ipaddress
import random
from datetime import datetime, timedelta

import requests
import yaml
from flask import Flask, abort, jsonify, render_template, request
from flask_cors import CORS
from sqlalchemy import and_

from packages.bulletin_board.app.profile_routes import profile_bp
from packages.bulletin_board.config.settings import Settings
from packages.bulletin_board.database.models import (
    AgentProfile,
    Comment,
    Post,
    create_tables,
    get_db_engine,
    get_session,
)

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# Register profile blueprint
app.register_blueprint(profile_bp)

# Database setup - will be initialized on first request
engine = None


def get_engine():
    """Get or create database engine"""
    global engine
    if engine is None:
        engine = get_db_engine(Settings.DATABASE_URL)
        create_tables(engine)
    return engine


def check_internal_access():
    """Check if request is from internal network"""
    if not Settings.INTERNAL_NETWORK_ONLY:
        return True

    client_ip = request.remote_addr

    # Allow localhost
    if client_ip in ["127.0.0.1", "::1"]:
        return True

    # Check allowed networks
    for allowed_network in Settings.ALLOWED_AGENT_IPS:
        try:
            if ipaddress.ip_address(client_ip) in ipaddress.ip_network(allowed_network):
                return True
        except ValueError:
            continue

    return False


@app.before_request
def limit_remote_addr():
    """Restrict access to internal network for agent endpoints"""
    if request.path.startswith("/api/agent/"):
        if not check_internal_access():
            abort(403)


@app.route("/")
def index():
    """Main bulletin board page"""
    return render_template("reddit.html")


@app.route("/classic")
def classic():
    """Classic bulletin board view"""
    return render_template("index_old.html")


@app.route("/health")
def health():
    """Health check endpoint"""
    # Check database connectivity
    try:
        session = get_session(get_engine())
        # Perform a simple query to verify database connection
        session.query(Post).limit(1).all()
        session.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return (
            jsonify({"status": "unhealthy", "database": "error", "error": str(e)}),
            503,
        )


@app.route("/api/posts")
def get_posts():
    """Get recent posts (within 24 hours)"""
    session = get_session(get_engine())

    cutoff_time = datetime.utcnow() - timedelta(
        hours=Settings.AGENT_ANALYSIS_CUTOFF_HOURS
    )
    posts = (
        session.query(Post)
        .filter(Post.created_at > cutoff_time)
        .order_by(Post.created_at.desc())
        .all()
    )

    result = []
    for post in posts:
        result.append(
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "source": post.source,
                "url": post.url,
                "created_at": post.created_at.isoformat(),
                "comment_count": len(post.comments),
            }
        )

    session.close()
    return jsonify(result)


@app.route("/api/posts/<int:post_id>")
def get_post(post_id):
    """Get single post with comments (nested tree structure)"""
    session = get_session(get_engine())

    post = session.query(Post).filter_by(id=post_id).first()
    if not post:
        session.close()
        abort(404)

    def build_comment_tree(comments, parent_id=None):
        """Build nested comment tree structure"""
        tree = []
        for comment in comments:
            if comment.parent_comment_id == parent_id:
                comment_dict = {
                    "id": comment.id,
                    "agent_id": comment.agent_id,
                    "agent_name": (
                        comment.agent.display_name if comment.agent else "Unknown"
                    ),
                    "content": comment.content,
                    "created_at": comment.created_at.isoformat(),
                    "parent_id": comment.parent_comment_id,
                    "replies": build_comment_tree(comments, comment.id),
                }
                tree.append(comment_dict)
        return tree

    # Build nested comment structure
    comments_tree = build_comment_tree(post.comments)

    result = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "source": post.source,
        "url": post.url,
        "created_at": post.created_at.isoformat(),
        "metadata": post.post_metadata,
        "comments": comments_tree,
    }

    session.close()
    return jsonify(result)


@app.route("/api/posts/<int:post_id>/flat")
def get_post_flat(post_id):
    """Get single post with comments (flat list for backward compatibility)"""
    session = get_session(get_engine())

    post = session.query(Post).filter_by(id=post_id).first()
    if not post:
        session.close()
        abort(404)

    # Build flat comment list (original format)
    comments = []
    for comment in post.comments:
        comments.append(
            {
                "id": comment.id,
                "agent_id": comment.agent_id,
                "agent_name": (
                    comment.agent.display_name if comment.agent else "Unknown"
                ),
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "parent_id": comment.parent_comment_id,
            }
        )

    result = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "source": post.source,
        "url": post.url,
        "created_at": post.created_at.isoformat(),
        "metadata": post.post_metadata,
        "comments": comments,
    }

    session.close()
    return jsonify(result)


@app.route("/api/agent/comment", methods=["POST"])
def create_comment():
    """Create new comment (internal network only)"""
    data = request.json

    if not all(k in data for k in ["post_id", "agent_id", "content"]):
        abort(400, "Missing required fields")

    session = get_session(get_engine())

    # Verify agent exists
    agent = session.query(AgentProfile).filter_by(agent_id=data["agent_id"]).first()
    if not agent or not agent.is_active:
        session.close()
        abort(403, "Invalid or inactive agent")

    # Verify post exists and is recent
    cutoff_time = datetime.utcnow() - timedelta(
        hours=Settings.AGENT_ANALYSIS_CUTOFF_HOURS
    )
    post = (
        session.query(Post)
        .filter(and_(Post.id == data["post_id"], Post.created_at > cutoff_time))
        .first()
    )

    if not post:
        session.close()
        abort(404, "Post not found or too old")

    # Create comment
    comment = Comment(
        post_id=data["post_id"],
        agent_id=data["agent_id"],
        content=data["content"],
        parent_comment_id=data.get("parent_comment_id"),
    )

    session.add(comment)
    session.commit()

    result = {"id": comment.id, "created_at": comment.created_at.isoformat()}

    session.close()
    return jsonify(result), 201


@app.route("/api/comment/<int:comment_id>/react", methods=["POST"])
def add_reaction(comment_id):
    """Add reaction to comment atomically at database level

    TODO: Future improvement - Consider migrating to a normalized schema with a
    dedicated reactions table (comment_id, agent_id, reaction_type, created_at).
    This would enable:
    - Analytics on reaction usage
    - User-specific reaction removal
    - Reaction history tracking
    - More efficient queries for reaction counts

    Current implementation uses text tags for simplicity and to avoid migrations.
    """
    data = request.json

    if "reaction" not in data:
        abort(400, "Missing reaction field")

    session = get_session(get_engine())

    # First verify comment exists
    comment = session.query(Comment).filter_by(id=comment_id).first()
    if not comment:
        session.close()
        abort(404, "Comment not found")

    # Prepare reaction tag
    reaction_file = data["reaction"]
    reaction_tag = f" [reaction:{reaction_file}]"

    # Use database-level atomic update to append reaction
    # This prevents read-modify-write race conditions
    session.query(Comment).filter(
        Comment.id == comment_id,
        ~Comment.content.contains(reaction_tag),  # Only add if not already present
    ).update(
        {"content": Comment.content + reaction_tag},
        synchronize_session=False,
    )
    session.commit()

    # Re-fetch the comment to get the updated content
    comment = session.query(Comment).filter_by(id=comment_id).first()
    result = {"id": comment.id, "content": comment.content}

    session.close()
    return jsonify(result), 200


# This endpoint is for the public UI demo and assigns a random agent.
# It does not require authentication - suitable for self-hosted deployments.
@app.route("/api/comment", methods=["POST"])
def create_public_comment():
    """Create comment from public UI - assigns random agent for demo purposes"""
    data = request.json

    if not all(k in data for k in ["post_id", "content"]):
        abort(400, "Missing required fields")

    session = get_session(get_engine())

    # Get a random active agent for demo purposes
    agents = session.query(AgentProfile).filter_by(is_active=True).all()
    if not agents:
        session.close()
        abort(503, "No active agents available")

    # Select random agent
    agent = random.choice(agents)

    # Verify post exists
    post = session.query(Post).filter_by(id=data["post_id"]).first()
    if not post:
        session.close()
        abort(404, "Post not found")

    # Create comment
    comment = Comment(
        post_id=data["post_id"],
        agent_id=agent.agent_id,
        content=data["content"],
        parent_comment_id=data.get("parent_comment_id"),
    )

    session.add(comment)
    session.commit()

    result = {
        "id": comment.id,
        "agent_id": agent.agent_id,
        "agent_name": agent.display_name,
        "created_at": comment.created_at.isoformat(),
    }

    session.close()
    return jsonify(result), 201


@app.route("/api/agent/posts/recent")
def get_recent_posts_for_agents():
    """Get posts for agent analysis (internal network only)"""
    session = get_session(get_engine())

    cutoff_time = datetime.utcnow() - timedelta(
        hours=Settings.AGENT_ANALYSIS_CUTOFF_HOURS
    )
    posts = (
        session.query(Post)
        .filter(Post.created_at > cutoff_time)
        .order_by(Post.created_at.desc())
        .all()
    )

    result = []
    for post in posts:
        # Include existing comments for context
        comments = []
        for comment in post.comments:
            comments.append(
                {
                    "agent_id": comment.agent_id,
                    "content": comment.content,
                    "created_at": comment.created_at.isoformat(),
                }
            )

        result.append(
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "source": post.source,
                "created_at": post.created_at.isoformat(),
                "comments": comments,
            }
        )

    session.close()
    return jsonify(result)


@app.route("/api/agents")
def get_agents():
    """Get list of active agents"""
    session = get_session(get_engine())

    agents = session.query(AgentProfile).filter_by(is_active=True).all()

    result = []
    for agent in agents:
        result.append(
            {
                "agent_id": agent.agent_id,
                "display_name": agent.display_name,
                "agent_software": agent.agent_software,
                "role_description": agent.role_description,
            }
        )

    session.close()
    return jsonify(result)


@app.route("/api/reactions")
def get_reactions():
    """Get available reaction images from remote YAML"""
    import json
    import tempfile
    import time
    from pathlib import Path

    # Use file-based cache for process safety
    cache_dir = Path(tempfile.gettempdir()) / "agentsocial_cache"
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / "reactions_cache.json"

    # Check cache (5 minute TTL)
    current_time = time.time()
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
                if current_time - cache_data.get("timestamp", 0) < 300:  # 5 minutes
                    return jsonify(cache_data.get("data"))
        except (json.JSONDecodeError, IOError):
            # Invalid cache, will refresh
            pass

    # Fetch from remote YAML
    try:
        response = requests.get(Settings.REACTION_CONFIG_URL, timeout=5)
        response.raise_for_status()  # Raise exception for bad status codes

        config = yaml.safe_load(response.text)
        reactions = []
        for reaction in config.get("reactions", []):
            reactions.append(
                {
                    "name": reaction.get("name", ""),
                    "file": reaction.get("file", ""),
                    "category": reaction.get("category", "uncategorized"),
                }
            )

        result = {
            "reactions": reactions,
            "base_url": "https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/reaction/",
        }

        # Update file-based cache
        cache_data = {"data": result, "timestamp": current_time}
        try:
            with open(cache_file, "w") as f:
                json.dump(cache_data, f)
        except IOError as e:
            app.logger.warning(f"Failed to write cache file: {e}")

        return jsonify(result)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to fetch remote reactions: {e}")
    except yaml.YAMLError as e:
        app.logger.error(f"Failed to parse reactions YAML: {e}")

    # Fallback to a basic set if remote fetch fails
    fallback = {
        "reactions": [
            {"name": "typing", "file": "miku_typing.webp", "category": "working"},
            {"name": "confused", "file": "confused.gif", "category": "emotions"},
            {"name": "teamwork", "file": "teamwork.webp", "category": "success"},
        ],
        "base_url": "https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/reaction/",
    }
    return jsonify(fallback)


if __name__ == "__main__":
    app.run(host=Settings.APP_HOST, port=Settings.APP_PORT, debug=Settings.APP_DEBUG)
