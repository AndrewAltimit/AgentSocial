"""Common test fixtures for bulletin board tests"""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.bulletin_board.config.test_settings import test_settings
from packages.bulletin_board.database.models import Base


# Patch agent profiles loading at module level to prevent YAML loading during tests
@pytest.fixture(scope="session", autouse=True)
def mock_agent_profiles_loading():
    """Prevent agent profiles from being loaded from YAML during tests"""
    empty_profiles = []
    with patch("packages.bulletin_board.agents.agent_profiles.AGENT_PROFILES", empty_profiles):
        with patch(
            "packages.bulletin_board.agents.agent_profiles.load_agent_profiles",
            return_value=empty_profiles,
        ):
            yield


@pytest.fixture(scope="function")
def test_db_engine():
    """Create an in-memory SQLite database engine for testing"""
    # Reset global session factory to prevent state carryover
    import packages.bulletin_board.database.models

    packages.bulletin_board.database.models._SessionFactory = None
    packages.bulletin_board.database.models._ScopedSession = None

    # Use StaticPool to ensure the same connection is reused
    # This prevents "database is locked" errors in SQLite
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

    # Reset global session factory after test
    packages.bulletin_board.database.models._SessionFactory = None
    packages.bulletin_board.database.models._ScopedSession = None


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create a test database session"""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    # Ensure we start with a clean transaction
    session.commit()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def mock_settings():
    """Mock the Settings object with test configuration"""
    with patch("packages.bulletin_board.config.settings.Settings", test_settings):
        with patch("packages.bulletin_board.app.app.Settings", test_settings):
            with patch("packages.bulletin_board.agents.agent_runner.Settings", test_settings):
                with patch("packages.bulletin_board.agents.feed_collector.Settings", test_settings):
                    yield test_settings


@pytest.fixture(scope="function")
def mock_db_functions(test_db_engine):
    """Mock database helper functions to use test engine"""
    # Keep track of sessions to ensure they're properly closed
    sessions = []

    def mock_get_engine(url=None):
        return test_db_engine

    def mock_get_session(engine=None):
        if engine is None:
            engine = test_db_engine
        Session = sessionmaker(bind=engine)
        session = Session()
        sessions.append(session)
        return session

    with patch("packages.bulletin_board.database.models.get_db_engine", mock_get_engine):
        with patch("packages.bulletin_board.database.models.get_session", mock_get_session):
            with patch("packages.bulletin_board.app.app.get_db_engine", mock_get_engine):
                with patch("packages.bulletin_board.app.app.get_session", mock_get_session):
                    with patch(
                        "packages.bulletin_board.agents.feed_collector.get_session",
                        mock_get_session,
                    ):
                        with patch(
                            "packages.bulletin_board.agents.init_agents.get_db_engine",
                            mock_get_engine,
                        ):
                            with patch(
                                "packages.bulletin_board.agents.init_agents.get_session",
                                mock_get_session,
                            ):
                                yield
                                # Close all sessions after test
                                for session in sessions:
                                    try:
                                        session.rollback()
                                        session.close()
                                    except Exception:
                                        pass


@pytest.fixture
def app(mock_settings, mock_db_functions):
    """Create a test Flask application"""
    from packages.bulletin_board.app.app import app as flask_app

    flask_app.config["TESTING"] = True
    flask_app.config["DEBUG"] = False

    # Reset the global engine to None to force re-initialization
    import packages.bulletin_board.app.app

    packages.bulletin_board.app.app.engine = None

    with flask_app.app_context():
        yield flask_app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application"""
    return app.test_client()


@pytest.fixture
def api_headers():
    """Common headers for API requests"""
    return {"Content-Type": "application/json", "Accept": "application/json"}
