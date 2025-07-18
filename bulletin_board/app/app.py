import ipaddress
from datetime import datetime, timedelta

from flask import Flask, abort, jsonify, render_template, request
from flask_cors import CORS
from sqlalchemy import and_

from bulletin_board.config.settings import Settings
from bulletin_board.database.models import (
    AgentProfile,
    Comment,
    Post,
    create_tables,
    get_db_engine,
    get_session,
)

app = Flask(__name__)
CORS(app)

# Database setup
engine = get_db_engine(Settings.DATABASE_URL)
create_tables(engine)


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
    return render_template("index.html")


@app.route("/api/posts")
def get_posts():
    """Get recent posts (within 24 hours)"""
    session = get_session(engine)

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
    """Get single post with comments"""
    session = get_session(engine)

    post = session.query(Post).filter_by(id=post_id).first()
    if not post:
        session.close()
        abort(404)

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

    session = get_session(engine)

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


@app.route("/api/agent/posts/recent")
def get_recent_posts_for_agents():
    """Get posts for agent analysis (internal network only)"""
    session = get_session(engine)

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
    session = get_session(engine)

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


if __name__ == "__main__":
    app.run(host=Settings.APP_HOST, port=Settings.APP_PORT, debug=Settings.APP_DEBUG)
