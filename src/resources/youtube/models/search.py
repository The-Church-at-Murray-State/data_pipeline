from typing import Literal
from pydantic import BaseModel, Field


class SearchResultId(BaseModel):
    """
        Purpose:
            Represents the ID of a search result item.
        
        Args:
            kind (str): Type of resource (e.g., youtube#video)
            video_id (str | None): Video ID if the result is a video
        
        Returns:
            None: Pydantic model instance
    """
    kind: str
    video_id: str | None = Field(default=None, alias="videoId")


class SearchResultSnippet(BaseModel):
    """
        Purpose:
            Contains basic details about a search result.
        
        Args:
            channel_id (str): Channel ID that published the resource
            published_at (str): Upload timestamp in ISO 8601 format
            title (str): Title of the search result
            description (str): Description of the search result
        
        Returns:
            None: Pydantic model instance
    """
    channel_id: str = Field(alias="channelId")
    published_at: str = Field(alias="publishedAt")
    title: str
    description: str


class SearchResult(BaseModel):
    """
        Purpose:
            Represents a single search result item.
        
        Args:
            id (SearchResultId): ID object containing resource identifiers
            snippet (SearchResultSnippet): Basic details about the result
        
        Returns:
            None: Pydantic model instance
    """
    id: SearchResultId
    snippet: SearchResultSnippet


class PageInfo(BaseModel):
    """
        Purpose:
            Encapsulates paging information for result set.
        
        Args:
            total_results (int): Total number of results in the result set
            results_per_page (int): Number of results included in the API response
        
        Returns:
            None: Pydantic model instance
    """
    total_results: int = Field(alias="totalResults")
    results_per_page: int = Field(alias="resultsPerPage")


class SearchRequest(BaseModel):
    """
        Purpose:
            Request parameters for YouTube Search.list endpoint.
        
        Args:
            part (str): Comma-separated list of resource properties to include
            channel_id (str | None): Channel ID to filter results
            max_results (int): Maximum number of items to return (0-50)
            order (str): Sort order for results
            page_token (str | None): Token for specific page in result set
            type (str): Type of resource to search for
        
        Returns:
            None: Pydantic model instance
    """
    model_config = {"populate_by_name": True}
    
    part: str = "snippet"
    channel_id: str | None = Field(default=None, alias="channelId")
    max_results: int = Field(default=50, ge=0, le=50, alias="maxResults")
    order: Literal["date", "rating", "relevance", "title", "videoCount", "viewCount"] = "date"
    page_token: str | None = Field(default=None, alias="pageToken")
    type: str = "video"


class SearchResponse(BaseModel):
    """
        Purpose:
            Response from YouTube Search.list endpoint.
        
        Args:
            next_page_token (str | None): Token to retrieve next page
            page_info (PageInfo): Paging information for the result set
            items (list[SearchResult]): List of search results matching request criteria
        
        Returns:
            None: Pydantic model instance
    """
    next_page_token: str | None = Field(default=None, alias="nextPageToken")
    page_info: PageInfo = Field(alias="pageInfo")
    items: list[SearchResult]

