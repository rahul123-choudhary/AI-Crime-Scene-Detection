"""Flask application factory for AI Crime Scene Detection."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300 per minute", "5000 per hour"],
    storage_uri="memory://",
)

from app.config import BASE_DIR, MAX_CONTENT_LENGTH, STATIC_DIR, TEMPLATE_DIR
from app.database import init_db
from app.routes.api import api_bp
from app.routes.web import web_bp


def setup_error_tracking(app: Flask) -> None:
    """Configure structured rotating file error logging."""
    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Error / Warning Log Handler (10 MB rotation, 5 backups)
    error_handler = RotatingFileHandler(
        str(logs_dir / "app_errors.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s [in %(pathname)s:%(lineno)d]"
    )
    error_handler.setFormatter(error_formatter)

    # 2. General Activity Log Handler
    app_handler = RotatingFileHandler(
        str(logs_dir / "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(error_formatter)

    app.logger.addHandler(error_handler)
    app.logger.addHandler(app_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("Forensic AI Error Tracking & Diagnostics subsystem initialized.")


def create_app(test_config: dict[str, object] | None = None) -> Flask:
    """Create, configure, and initialize the forensic Flask application."""
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "forensic-ai-deepmind-secure-key-2026")
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    if test_config:
        app.config.update(test_config)

    # Setup file error tracking
    setup_error_tracking(app)

    # Initialize database tables
    with app.app_context():
        init_db()

    # Register application blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    # Initialize rate limiter
    limiter.init_app(app)

    @app.after_request
    def set_cache_headers(response):
        """Prevent browser back-forward caching of dynamic HTML pages so auth and redirects are always fresh."""
        if response.content_type and "text/html" in response.content_type:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.errorhandler(429)
    def ratelimit_handler(e):
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "error": "Rate limit exceeded. Please throttle requests.",
                "detail": str(getattr(e, "description", "Too Many Requests")),
            }), 429
        return render_template(
            "base.html",
            page_error="429: Rate Limit Exceeded. Forensic network security throttling active. Please wait a moment before sending more requests.",
        ), 429

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def file_too_large_error(error):
        return render_template(
            "base.html",
            page_error="413: Evidence payload exceeds maximum allowable size (32 MB).",
        ), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template(
            "base.html",
            page_error="500: An unexpected error occurred while processing forensic evidence.",
        ), 500

    return app
