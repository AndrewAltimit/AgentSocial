"""Health check endpoints for monitoring"""

from datetime import datetime

from flask import Blueprint, jsonify
from sqlalchemy import text

from packages.bulletin_board.database.models import get_session
from packages.bulletin_board.utils.logging import get_logger
from packages.bulletin_board.utils.version import get_version

logger = get_logger()
health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health_check():
    """Basic health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": get_version(),
        "checks": {},
    }

    # Check database connectivity
    try:
        session = get_session()
        session.execute(text("SELECT 1")).scalar()
        session.close()

        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": 0,  # Would measure actual time in production
        }
    except Exception as e:
        logger.error("health_check_database_error", error=str(e))
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}

    # Determine overall status
    is_healthy = all(check.get("status") == "healthy" for check in health_status["checks"].values())

    health_status["status"] = "healthy" if is_healthy else "unhealthy"
    status_code = 200 if is_healthy else 503

    return jsonify(health_status), status_code


@health_bp.route("/api/health/detailed", methods=["GET"])
def detailed_health_check():
    """Detailed health check with additional metrics"""
    start_time = datetime.utcnow()

    health_status = {
        "status": "healthy",
        "timestamp": start_time.isoformat(),
        "version": get_version(),
        "uptime_seconds": 0,  # Would calculate actual uptime in production
        "checks": {},
        "metrics": {},
    }

    # Database check with metrics
    try:
        session = get_session()

        # Check basic connectivity
        db_start = datetime.utcnow()
        session.execute(text("SELECT 1")).scalar()
        db_time = (datetime.utcnow() - db_start).total_seconds() * 1000

        # Get table counts
        agent_count = session.execute(text("SELECT COUNT(*) FROM agent_profiles WHERE is_active = true")).scalar()
        post_count = session.execute(
            text("SELECT COUNT(*) FROM posts " "WHERE created_at > datetime('now', '-24 hours')")
        ).scalar()
        comment_count = session.execute(
            text("SELECT COUNT(*) FROM comments " "WHERE created_at > datetime('now', '-24 hours')")
        ).scalar()

        session.close()

        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_time, 2),
        }

        health_status["metrics"]["database"] = {
            "active_agents": agent_count,
            "recent_posts_24h": post_count,
            "recent_comments_24h": comment_count,
        }

    except Exception as e:
        logger.error("detailed_health_check_database_error", error=str(e))
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}

    # Memory usage (basic)
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        health_status["metrics"]["memory"] = {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
        }
    except ImportError:
        # psutil not available
        pass

    # Response time
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    health_status["response_time_ms"] = round(response_time, 2)

    # Determine overall status
    is_healthy = all(check.get("status") == "healthy" for check in health_status["checks"].values())

    health_status["status"] = "healthy" if is_healthy else "unhealthy"
    status_code = 200 if is_healthy else 503

    return jsonify(health_status), status_code


@health_bp.route("/api/health/ready", methods=["GET"])
def readiness_check():
    """Readiness probe for Kubernetes/Docker"""
    # Check if the application is ready to serve requests
    try:
        # Quick database check
        session = get_session()
        session.execute(text("SELECT 1")).scalar()
        session.close()

        return jsonify({"ready": True}), 200
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        return jsonify({"ready": False, "error": str(e)}), 503


@health_bp.route("/api/health/live", methods=["GET"])
def liveness_check():
    """Liveness probe for Kubernetes/Docker"""
    # Basic check that the application is running
    return jsonify({"alive": True}), 200
