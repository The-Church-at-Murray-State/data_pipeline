import os


def _get_required_env_var(var_name: str) -> str:
    """
        Purpose:
            Retrieves a required environment variable value and raises ValueError if the variable is not set or empty.
        
        Args:
            var_name (str): The name of the environment variable to retrieve
        
        Returns:
            str: The value of the environment variable
    """
    if not var_name:
        raise ValueError("var_name is required")
    value: str | None = os.getenv(var_name)
    if value is None or value == "":
        raise ValueError(f"Required environment variable {var_name} is not set")
    return value.strip()

YOUTUBE_DATA_API_KEY: str = _get_required_env_var("YOUTUBE_DATA_API_KEY")
YOUTUBE_BASE_URL: str = _get_required_env_var("YOUTUBE_BASE_URL")
YOUTUBE_CHANNEL_ID: str = _get_required_env_var("YOUTUBE_CHANNEL_ID")

SUPADATA_KEY: str = _get_required_env_var("SUPADATA_KEY")

AGENTA_API_KEY: str = _get_required_env_var("AGENTA_API_KEY")
AGENTA_HOST_URL: str = _get_required_env_var("AGENTA_HOST_URL")

OPENAI_API_KEY: str = _get_required_env_var("OPENAI_API_KEY")

PINECONE_API_KEY: str = _get_required_env_var("PINECONE_API_KEY")
PINECONE_TRANSCRIPTIONS_HOST: str = _get_required_env_var("PINECONE_TRANSCRIPTIONS_HOST")

CLOUDFLARE_D1_API_KEY: str = _get_required_env_var("CLOUDFLARE_D1_API_KEY")
CLOUDFLARE_D1_DATABASE_ID: str = _get_required_env_var("CLOUDFLARE_D1_DATABASE_ID")
CLOUDFLARE_ACCOUNT_ID: str = _get_required_env_var("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME: str = _get_required_env_var("CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME")

ACCESS_TOKEN: str = _get_required_env_var("ACCESS_TOKEN")

HTTP_MAX_RETRIES: int = int(os.getenv("HTTP_MAX_RETRIES", "3"))
HTTP_BACKOFF_FACTOR: float = float(os.getenv("HTTP_BACKOFF_FACTOR", "1.0"))
HTTP_RETRY_STATUS_CODES: list[int] = [429, 500, 502, 503, 504]