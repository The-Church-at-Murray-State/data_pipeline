from src.resources.youtube.youtube_client import YoutubeClient
from src.resources.youtube.youtube_endpoints import YoutubeEndpoints
from src.resources.youtube.models.search import SearchRequest, SearchResponse

class YoutubeVideosResource:
    def __init__(self, youtube_client: YoutubeClient = YoutubeClient()):
        self.youtube_client = youtube_client

    def search_channel_videos_page_with_metadata(self, channel_id: str, page_token: str | None = None) -> tuple[list[tuple[str, str, str]], str | None]:
        """
            Purpose:
                Searches for a page of video IDs and metadata from a specific YouTube channel with pagination support.
            
            Args:
                channel_id (str): YouTube channel ID to search videos from
                page_token (str | None): Token for the next page of results
            
            Returns:
                tuple[list[tuple[str, str, str]], str | None]: Tuple containing list of (video_id, title, published_at) and next page token
        """
        request: SearchRequest = SearchRequest(channel_id=channel_id, page_token=page_token)
        response: SearchResponse = self.youtube_client.make_request(YoutubeEndpoints.SEARCH, request)
        video_metadata: list[tuple[str, str, str]] = [(item.id.video_id, item.snippet.title, item.snippet.published_at) for item in response.items if item.id.video_id is not None]
        return (video_metadata, response.next_page_token)

    def search_channel_videos_page(self, channel_id: str, page_token: str | None = None) -> tuple[list[str], str | None]:
        """
            Purpose:
                Searches for a page of video IDs from a specific YouTube channel with pagination support.
            
            Args:
                channel_id (str): YouTube channel ID to search videos from
                page_token (str | None): Token for the next page of results
            
            Returns:
                tuple[list[str], str | None]: Tuple containing list of video IDs and next page token
        """
        request: SearchRequest = SearchRequest(channel_id=channel_id, page_token=page_token)
        response: SearchResponse = self.youtube_client.make_request(
            YoutubeEndpoints.SEARCH,
            request
        )
        video_ids: list[str] = [item.id.video_id for item in response.items if item.id.video_id is not None]
        return (video_ids, response.next_page_token)

    def search_all_channel_videos_with_metadata(self, channel_id: str) -> list[tuple[str, str, str]]:
        """
            Purpose:
                Searches for all video IDs and metadata from a specific YouTube channel by paginating through all available pages.
            
            Args:
                channel_id (str): YouTube channel ID to search videos from
            
            Returns:
                list[tuple[str, str, str]]: Complete list of (video_id, title, published_at) from the channel across all pages
        """
        all_video_metadata: list[tuple[str, str, str]] = []
        next_page_token: str | None = None
        while True:
            page_video_metadata: list[tuple[str, str, str]]
            page_video_metadata, next_page_token = self.search_channel_videos_page_with_metadata(channel_id, next_page_token)
            all_video_metadata.extend(page_video_metadata)
            if next_page_token is None:
                break
        return all_video_metadata

    def search_all_channel_videos(self, channel_id: str) -> list[str]:
        """
            Purpose:
                Searches for all video IDs from a specific YouTube channel by paginating through all available pages.
            
            Args:
                channel_id (str): YouTube channel ID to search videos from
            
            Returns:
                list[str]: Complete list of all video IDs from the channel across all pages
        """
        all_video_ids: list[str] = []
        next_page_token: str | None = None
        while True:
            video_ids: list[str]
            video_ids, next_page_token = self.search_channel_videos_page(channel_id, next_page_token)
            all_video_ids.extend(video_ids)
            if next_page_token is None:
                break
        return all_video_ids

