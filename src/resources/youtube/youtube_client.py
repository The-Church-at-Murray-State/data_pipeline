from src.resources.endpoint import Endpoint
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pydantic import BaseModel
from src.settings import (
    YOUTUBE_DATA_API_KEY,
    HTTP_MAX_RETRIES,
    HTTP_BACKOFF_FACTOR,
    HTTP_RETRY_STATUS_CODES
)

class YoutubeClient:
    def __init__(self, api_key: str = YOUTUBE_DATA_API_KEY, max_retries: int = HTTP_MAX_RETRIES, backoff_factor: float = HTTP_BACKOFF_FACTOR):
        """
            Purpose:
                Initializes a YouTube API client with configurable retry behavior and session management.
            
            Args:
                api_key (str): YouTube Data API key for authentication
                max_retries (int): Maximum number of retry attempts for failed requests
                backoff_factor (float): Multiplier for exponential backoff between retries
            
            Returns:
                None: Initializes YoutubeClient instance
        """
        self.api_key = api_key
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=HTTP_RETRY_STATUS_CODES,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def make_request(self, endpoint: Endpoint, request: BaseModel) -> BaseModel:
        """
            Purpose:
                Executes an HTTP request to the specified endpoint with automatic retry logic and response validation.
            
            Args:
                endpoint (Endpoint): Endpoint configuration containing URL path, HTTP method, and response schema
                request (BaseModel): Pydantic model containing request parameters to be serialized
            
            Returns:
                BaseModel: Parsed and validated response data as the endpoint's response schema type
        """
        request_params: dict = request.model_dump(by_alias=True, exclude_none=True)
        request_params['key'] = self.api_key
        try:
            if endpoint.method.upper() == "GET":
                response = self.session.get(endpoint.path, params=request_params)
            elif endpoint.method.upper() == "POST":
                response = self.session.post(endpoint.path, json=request_params)
            elif endpoint.method.upper() == "PUT":
                response = self.session.put(endpoint.path, json=request_params)
            elif endpoint.method.upper() == "DELETE":
                response = self.session.delete(endpoint.path, params=request_params)
            elif endpoint.method.upper() == "PATCH":
                response = self.session.patch(endpoint.path, json=request_params)
            else:
                raise ValueError(f"Unsupported HTTP method: {endpoint.method}")
            response.raise_for_status()
            if endpoint.response_scheme is None:
                raise ValueError("Endpoint must have a response_scheme defined")
            response_data: dict = response.json()
            return endpoint.response_scheme(**response_data)
        except requests.exceptions.HTTPError as http_error:
            print(f"HTTP Error: {http_error}")
            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            raise
        except Exception as error:
            print(f"Error during request: {error}")
            if 'response' in locals():
                print(f"Response Status: {response.status_code}")
                print(f"Response Body: {response.text}")
            raise