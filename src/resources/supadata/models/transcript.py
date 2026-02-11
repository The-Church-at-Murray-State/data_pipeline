from pydantic import BaseModel


class TranscriptChunk(BaseModel):
    """
        Purpose:
            Represents a timestamped chunk of transcript text.
        
        Args:
            text (str): The transcript text content
            start (float): Start time in seconds
            duration (float): Duration in seconds
        
        Returns:
            None: Pydantic model instance
    """
    text: str
    start: float
    duration: float


class Transcript(BaseModel):
    """
        Purpose:
            Represents a video transcript with metadata.
        
        Args:
            video_id (str): YouTube video ID
            content (str | list[TranscriptChunk]): Full transcript text or list of chunks
            lang (str): Language code of the transcript
        
        Returns:
            None: Pydantic model instance
    """
    video_id: str
    content: str | list[TranscriptChunk]
    lang: str

