"""Routes package for web and API blueprints."""

from app.routes.api import api_bp
from app.routes.web import web_bp

__all__ = ["web_bp", "api_bp"]
