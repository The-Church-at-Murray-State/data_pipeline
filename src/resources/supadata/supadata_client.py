from supadata import Supadata
from src.settings import SUPADATA_KEY


class SupadataClient:
    def __init__(self, api_key: str = SUPADATA_KEY):
        """
            Purpose:
                Initializes a Supadata API client for accessing transcript and metadata services.
            
            Args:
                api_key (str): Supadata API key for authentication
            
            Returns:
                None: Initializes SupadataClient instance
        """
        self.api_key = api_key
        self.client = Supadata(api_key=api_key)

