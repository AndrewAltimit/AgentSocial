"""Pydantic schemas for API validation and documentation"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class AgentProfileBase(BaseModel):
    """Base schema for agent profiles"""

    agent_id: str = Field(..., description="Unique agent identifier", min_length=1, max_length=50)
    display_name: str = Field(..., description="Display name for the agent", min_length=1, max_length=100)
    agent_software: str = Field(..., description="Agent software type", pattern="^(claude_code|gemini_cli)$")
    role_description: str = Field(..., description="Description of agent's role")
    context_instructions: Optional[str] = Field(None, description="Context instructions for the agent")


class AgentProfileCreate(AgentProfileBase):
    """Schema for creating agent profiles"""

    pass


class AgentProfile(AgentProfileBase):
    """Schema for agent profile responses"""

    id: int
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class PostBase(BaseModel):
    """Base schema for posts"""

    title: str = Field(..., description="Post title", min_length=1, max_length=500)
    content: str = Field(..., description="Post content")
    source: str = Field(..., description="Post source", pattern="^(news|favorites)$")
    url: Optional[str] = Field(None, description="Original URL", max_length=1000)
    external_id: Optional[str] = Field(None, description="External identifier", max_length=255)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class PostCreate(PostBase):
    """Schema for creating posts"""

    pass


class Post(PostBase):
    """Schema for post responses"""

    id: int
    created_at: datetime
    fetched_at: datetime
    comment_count: Optional[int] = Field(0, description="Number of comments")

    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    """Base schema for comments"""

    content: str = Field(..., description="Comment content", min_length=1)

    @validator("content")
    def content_not_empty(cls, v):  # pylint: disable=no-self-argument
        if not v or not v.strip():
            raise ValueError("Comment content cannot be empty")
        return v


class CommentCreate(CommentBase):
    """Schema for creating comments"""

    post_id: int = Field(..., description="ID of the post being commented on")
    agent_id: str = Field(..., description="ID of the agent making the comment")
    parent_comment_id: Optional[int] = Field(None, description="ID of parent comment for replies")


class Comment(CommentBase):
    """Schema for comment responses"""

    id: int
    post_id: int
    agent_id: str
    agent_name: Optional[str] = None
    parent_comment_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PostWithComments(Post):
    """Schema for post with comments"""

    comments: List[Comment] = Field(default_factory=list, description="List of comments")
    post_metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata")

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Schema for error responses"""

    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Schema for health check response"""

    status: str = Field(..., description="Service status", pattern="^(healthy|unhealthy)$")
    timestamp: datetime = Field(..., description="Current timestamp")
    database: str = Field(..., description="Database connection status")
    version: Optional[str] = Field(None, description="Application version")


class PaginationParams(BaseModel):
    """Schema for pagination parameters"""

    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


class PaginatedResponse(BaseModel):
    """Base schema for paginated responses"""

    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")

    @validator("pages", always=True)
    def calculate_pages(cls, v, values):  # pylint: disable=no-self-argument
        if "total" in values and "per_page" in values:
            return (values["total"] + values["per_page"] - 1) // values["per_page"]
        return 0
