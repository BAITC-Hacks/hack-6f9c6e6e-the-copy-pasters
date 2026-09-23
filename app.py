"""Uvicorn entry point for EventMatch KZ."""

from event_matcher.api.application import create_app


app = create_app()
