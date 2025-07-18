"""Error handlers for Flask application"""
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from bulletin_board.utils.exceptions import (
    BulletinBoardError,
    ValidationError,
    AuthorizationError,
    NotFoundError,
    ExternalAPIError,
    ConfigurationError,
    RateLimitError,
    DatabaseError
)
from bulletin_board.utils.logging import get_logger
import traceback


logger = get_logger()


def handle_bulletin_board_error(error: BulletinBoardError):
    """Handle custom bulletin board errors"""
    status_code = 500  # Default
    
    if isinstance(error, ValidationError):
        status_code = 400
    elif isinstance(error, AuthorizationError):
        status_code = 403
    elif isinstance(error, NotFoundError):
        status_code = 404
    elif isinstance(error, RateLimitError):
        status_code = 429
    elif isinstance(error, ExternalAPIError):
        status_code = 502
    elif isinstance(error, ConfigurationError):
        status_code = 500
    elif isinstance(error, DatabaseError):
        status_code = 503
    
    response = {
        "error": error.message,
        "code": error.code,
    }
    
    if error.details:
        response["details"] = error.details
    
    # Log the error
    logger.error(
        "application_error",
        error_type=type(error).__name__,
        error_message=error.message,
        error_code=error.code,
        status_code=status_code,
        path=request.path,
        method=request.method,
        **error.details
    )
    
    return jsonify(response), status_code


def handle_http_exception(error: HTTPException):
    """Handle Werkzeug HTTP exceptions"""
    response = {
        "error": error.description or str(error),
        "code": error.name.upper().replace(" ", "_")
    }
    
    logger.warning(
        "http_exception",
        status_code=error.code,
        error_name=error.name,
        path=request.path,
        method=request.method
    )
    
    return jsonify(response), error.code


def handle_generic_exception(error: Exception):
    """Handle unexpected exceptions"""
    # Log full traceback for debugging
    logger.error(
        "unhandled_exception",
        error_type=type(error).__name__,
        error_message=str(error),
        traceback=traceback.format_exc(),
        path=request.path,
        method=request.method
    )
    
    # Don't expose internal details in production
    response = {
        "error": "An unexpected error occurred",
        "code": "INTERNAL_ERROR"
    }
    
    # In debug mode, include more details
    if hasattr(request, 'app') and request.app.debug:
        response["details"] = {
            "type": type(error).__name__,
            "message": str(error)
        }
    
    return jsonify(response), 500


def register_error_handlers(app: Flask):
    """Register all error handlers with the Flask app"""
    # Custom exceptions
    app.register_error_handler(BulletinBoardError, handle_bulletin_board_error)
    
    # HTTP exceptions
    app.register_error_handler(HTTPException, handle_http_exception)
    
    # Generic exceptions (catch-all)
    app.register_error_handler(Exception, handle_generic_exception)
    
    # Specific HTTP status codes
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "error": "Bad request",
            "code": "BAD_REQUEST"
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Resource not found",
            "code": "NOT_FOUND"
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "error": "Method not allowed",
            "code": "METHOD_NOT_ALLOWED"
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error("internal_server_error", error=str(error))
        return jsonify({
            "error": "Internal server error",
            "code": "INTERNAL_ERROR"
        }), 500