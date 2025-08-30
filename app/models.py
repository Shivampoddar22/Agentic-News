from pydantic import BaseModel, Field
from typing import List, Optional

class ArticleSummary(BaseModel):
    """Data model for a single summarized article."""
    source: str = Field(..., description="The source URL of the article.")
    summary: str = Field(..., description="The concise summary of the article.")
    bullets: List[str] = Field(..., description="Key bullet points from the article.")

class NewsDigestRequest(BaseModel):
    """Request model for generating a news digest."""
    query: str = Field(..., description="The topic to generate a news digest for.", min_length=5)

class NewsDigestResponse(BaseModel):
    """Response model containing the generated news digest and metadata."""
    digest: List[ArticleSummary]
    metadata: dict = Field(..., description="Metadata about the request processing.")