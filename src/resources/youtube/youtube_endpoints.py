from src.resources.endpoint import Endpoint
from src.settings import YOUTUBE_BASE_URL
from src.resources.youtube.models import SearchRequest, SearchResponse

class YoutubeEndpoints:
    SEARCH: Endpoint = Endpoint(
        path=f"{YOUTUBE_BASE_URL}/search",
        method="GET",
        request_scheme=SearchRequest,
        response_scheme=SearchResponse
    )