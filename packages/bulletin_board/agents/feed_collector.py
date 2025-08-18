import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

import aiohttp
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from structlog import get_logger

from packages.bulletin_board.config.settings import Settings
from packages.bulletin_board.database.models import Post, get_session
from packages.bulletin_board.utils.logging import configure_logging

# Initialize logger - configuration will be done when needed
logger = get_logger()


class FeedCollector:
    """Base class for feed collectors"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    async def fetch_and_store(self) -> int:
        """Fetch items and store in database. Returns number of new items."""
        raise NotImplementedError


class GitHubFavoritesCollector(FeedCollector):
    """Collects favorites from GitHub repository"""

    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self.repo = Settings.GITHUB_FEED_REPO
        self.branch = Settings.GITHUB_FEED_BRANCH
        self.path = Settings.GITHUB_FEED_PATH
        self.token = Settings.GITHUB_TOKEN

    async def fetch_and_store(self) -> int:
        """Fetch favorites from GitHub and store in database"""
        try:
            favorites = await self._fetch_github_file()
            return self._store_favorites(favorites)
        except aiohttp.ClientError as e:
            logger.error(
                "Network error fetching GitHub favorites",
                error=str(e),
                error_type=type(e).__name__,
                repo=Settings.GITHUB_FEED_REPO,
            )
            return 0
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON in GitHub favorites file",
                error=str(e),
                line=e.lineno,
                column=e.colno,
                repo=Settings.GITHUB_FEED_REPO,
            )
            return 0
        except ValueError as e:
            logger.error(
                "Data validation error in GitHub favorites",
                error=str(e),
                repo=Settings.GITHUB_FEED_REPO,
            )
            return 0

    async def _fetch_github_file(self) -> List[Dict[str, Any]]:
        """Fetch JSON file from GitHub"""
        url = (
            f"https://api.github.com/repos/{self.repo}/"
            f"contents/{self.path}?ref={self.branch}"
        )
        headers = {
            "Accept": "application/vnd.github.v3.raw",
            "User-Agent": "AgentSocial-BulletinBoard",
        }

        if self.token:
            headers["Authorization"] = f"token {self.token}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    return json.loads(content)
                else:
                    error_body = await response.text()
                    logger.error(
                        "GitHub API request failed",
                        status_code=response.status,
                        error_body=error_body[:500],  # Truncate for logging
                    )
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"GitHub API error: {response.status}",
                        headers=response.headers,
                    )

    def _store_favorites(self, favorites: List[Dict[str, Any]]) -> int:
        """Store favorites in database"""
        new_count = 0

        for item in favorites:
            try:
                post = Post(
                    external_id=item.get("id", ""),
                    source="favorites",
                    title=item.get("title", "Untitled"),
                    content=item.get("content", ""),
                    url=item.get("url"),
                    post_metadata=item.get("metadata", {}),
                    created_at=datetime.fromisoformat(
                        item.get("created_at", datetime.utcnow().isoformat())
                    ),
                )
                self.db_session.add(post)
                self.db_session.commit()
                new_count += 1
            except IntegrityError:
                # Post already exists
                self.db_session.rollback()
                continue
            except Exception as e:
                logger.error(
                    "Failed to store favorite",
                    error=str(e),
                    error_type=type(e).__name__,
                    item_id=item.get("id", "unknown"),
                )
                self.db_session.rollback()
                continue

        return new_count


class NewsCollector(FeedCollector):
    """Collects news from various sources"""

    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self.api_key = Settings.NEWS_API_KEY
        self.sources = Settings.NEWS_SOURCES

    async def fetch_and_store(self) -> int:
        """Fetch news and store in database"""
        if not self.api_key:
            logger.warning("News API key not configured")
            return 0

        try:
            articles = await self._fetch_news()
            return self._store_articles(articles)
        except aiohttp.ClientError as e:
            logger.error(
                "Network error fetching news",
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON response from News API",
                error=str(e),
                line=e.lineno,
                column=e.colno,
            )
            return 0
        except ValueError as e:
            logger.error(
                "Data validation error in news articles",
                error=str(e),
            )
            return 0

    async def _fetch_news(self) -> List[Dict[str, Any]]:
        """Fetch news from News API"""
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "apiKey": self.api_key,
            "sources": ",".join(self.sources),
            "pageSize": 50,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("articles", [])
                else:
                    error_body = await response.text()
                    logger.error(
                        "News API request failed",
                        status_code=response.status,
                        error_body=error_body[:500],  # Truncate for logging
                    )
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"News API error: {response.status}",
                        headers=response.headers,
                    )

    def _store_articles(self, articles: List[Dict[str, Any]]) -> int:
        """Store news articles in database"""
        new_count = 0

        for article in articles:
            try:
                post = Post(
                    external_id=article.get("url", ""),
                    source="news",
                    title=article.get("title", "Untitled"),
                    content=article.get("description", "")
                    or article.get("content", ""),
                    url=article.get("url"),
                    post_metadata={
                        "author": article.get("author"),
                        "source": article.get("source", {}).get("name"),
                        "publishedAt": article.get("publishedAt"),
                    },
                    created_at=datetime.fromisoformat(
                        article.get(
                            "publishedAt", datetime.utcnow().isoformat()
                        ).replace("Z", "+00:00")
                    ),
                )
                self.db_session.add(post)
                self.db_session.commit()
                new_count += 1
            except IntegrityError:
                # Article already exists
                self.db_session.rollback()
                continue
            except Exception as e:
                logger.error(
                    "Failed to store article",
                    error=str(e),
                    error_type=type(e).__name__,
                    article_url=article.get("url", "unknown"),
                )
                self.db_session.rollback()
                continue

        return new_count


async def run_collectors(engine):
    """Run all collectors"""
    # Configure logging when function is called
    configure_logging(Settings.LOG_LEVEL, Settings.LOG_FORMAT == "json")

    session = get_session(engine)

    # Run collectors
    github_collector = GitHubFavoritesCollector(session)
    news_collector = NewsCollector(session)

    github_count = await github_collector.fetch_and_store()
    news_count = await news_collector.fetch_and_store()

    logger.info(
        "Feed collection completed", github_count=github_count, news_count=news_count
    )

    session.close()


if __name__ == "__main__":
    from packages.bulletin_board.database.models import create_tables, get_db_engine

    # Configure logging at runtime
    configure_logging(Settings.LOG_LEVEL, Settings.LOG_FORMAT == "json")

    engine = get_db_engine(Settings.DATABASE_URL)
    create_tables(engine)

    asyncio.run(run_collectors(engine))
