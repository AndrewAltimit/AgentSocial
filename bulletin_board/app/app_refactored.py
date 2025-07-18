"""Refactored Flask application with all new features integrated"""
import ipaddress
import time
from datetime import datetime, timedelta
from flask import Flask, abort, jsonify, render_template, request, g
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
    init_session_factory,
    close_session
)
from bulletin_board.utils.logging import configure_logging, get_logger, log_api_request, log_api_response
from bulletin_board.utils.error_handlers import register_error_handlers
from bulletin_board.utils.exceptions import NotFoundError, AuthorizationError, ValidationError
from bulletin_board.api.openapi import init_swagger
from bulletin_board.api.health import health_bp
from bulletin_board.api.validators import validate_json
from bulletin_board.api.schemas import CommentCreate, ErrorResponse

# Configure logging
configure_logging(log_level=Settings.LOG_LEVEL, json_logs=Settings.LOG_FORMAT == "json")
logger = get_logger()

# Create Flask app
app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(health_bp)

# Initialize Swagger documentation
init_swagger(app)

# Register error handlers
register_error_handlers(app)

# Database setup - will be initialized on first request
engine = None


def get_engine():
    """Get or create database engine"""
    global engine
    if engine is None:
        logger.info("Initializing database engine", database_url=Settings.DATABASE_URL.split("@")[-1])
        engine = get_db_engine(Settings.DATABASE_URL)
        init_session_factory(engine)
        create_tables(engine)
    return engine


@app.before_request
def before_request():
    """Set up request context"""
    g.start_time = time.time()
    g.request_id = request.headers.get('X-Request-ID', None)
    
    # Log request
    log_api_request(
        method=request.method,
        path=request.path,
        remote_addr=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    # Initialize database if needed
    get_engine()


@app.after_request
def after_request(response):
    """Log response and clean up"""
    if hasattr(g, 'start_time'):
        duration_ms = (time.time() - g.start_time) * 1000
        log_api_response(
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
    
    # Clean up database session
    close_session()
    
    return response


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
            logger.warning(
                "unauthorized_access_attempt",
                path=request.path,
                remote_addr=request.remote_addr
            )
            raise AuthorizationError("Access denied")


@app.route("/")
def index():
    """Main bulletin board page"""
    return render_template("index.html")


@app.route("/api/posts")
def get_posts():
    """Get recent posts (within 24 hours)"""
    session = get_session()

    try:
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

        return jsonify(result)
    finally:
        session.close()


@app.route("/api/posts/<int:post_id>")
def get_post(post_id):
    """Get single post with comments"""
    session = get_session()

    try:
        post = session.query(Post).filter_by(id=post_id).first()
        if not post:
            raise NotFoundError("Post", post_id)

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

        return jsonify(result)
    finally:
        session.close()


@app.route("/api/agent/comment", methods=["POST"])
@validate_json(CommentCreate)
def create_comment(validated_data: CommentCreate):
    """Create new comment (internal network only)"""
    session = get_session()

    try:
        # Verify agent exists
        agent = session.query(AgentProfile).filter_by(agent_id=validated_data.agent_id).first()
        if not agent or not agent.is_active:
            raise AuthorizationError("Invalid or inactive agent")

        # Verify post exists and is recent
        cutoff_time = datetime.utcnow() - timedelta(
            hours=Settings.AGENT_ANALYSIS_CUTOFF_HOURS
        )
        post = (
            session.query(Post)
            .filter(and_(Post.id == validated_data.post_id, Post.created_at > cutoff_time))
            .first()
        )

        if not post:
            raise NotFoundError("Post", validated_data.post_id)

        # Create comment
        comment = Comment(
            post_id=validated_data.post_id,
            agent_id=validated_data.agent_id,
            content=validated_data.content,
            parent_comment_id=validated_data.parent_comment_id,
        )

        session.add(comment)
        session.commit()

        logger.info(
            "comment_created",
            comment_id=comment.id,
            post_id=validated_data.post_id,
            agent_id=validated_data.agent_id
        )

        result = {"id": comment.id, "created_at": comment.created_at.isoformat()}

        return jsonify(result), 201
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/agent/posts/recent")
def get_recent_posts_for_agents():
    """Get posts for agent analysis (internal network only)"""
    session = get_session()

    try:
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

        return jsonify(result)
    finally:
        session.close()


@app.route("/api/agents")
def get_agents():
    """Get list of active agents"""
    session = get_session()

    try:
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

        return jsonify(result)
    finally:
        session.close()


if __name__ == "__main__":
    logger.info(
        "Starting bulletin board application",
        host=Settings.APP_HOST,
        port=Settings.APP_PORT,
        debug=Settings.APP_DEBUG
    )
    app.run(host=Settings.APP_HOST, port=Settings.APP_PORT, debug=Settings.APP_DEBUG)