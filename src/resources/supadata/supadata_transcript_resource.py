import time
from src.resources.supadata.supadata_client import SupadataClient
from src.resources.supadata.models.transcript import Transcript


class SupadataTranscriptResource:
    def __init__(self, supadata_client: SupadataClient = SupadataClient()):
        self.supadata_client = supadata_client

    def get_transcript(self, video_id: str, lang: str = "en", text: bool = True) -> Transcript:
        """
            Purpose:
                Fetches transcript for a single YouTube video, handling both immediate and async batch results.
            
            Args:
                video_id (str): YouTube video ID
                lang (str): Preferred language code (default: en)
                text (bool): Return plain text instead of timestamped chunks (default: True)
            
            Returns:
                Transcript: Transcript object containing video ID, content, and language
        """
        url: str = f"https://www.youtube.com/watch?v={video_id}"
        result = self.supadata_client.client.transcript(url=url, lang=lang, text=text)
        
        # Check if immediate result or batch job
        if hasattr(result, 'content'):
            # Immediate result
            return Transcript(
                video_id=video_id,
                content=result.content,
                lang=result.lang
            )
        else:
            # Async batch job - poll for results
            job_id = result.job_id
            max_attempts = 60
            for attempt in range(max_attempts):
                time.sleep(2)
                batch_results = self.supadata_client.client.youtube.batch.get_batch_results(job_id=job_id)
                if batch_results.status == 'completed':
                    if batch_results.results and len(batch_results.results) > 0:
                        first_result = batch_results.results[0]
                        return Transcript(
                            video_id=video_id,
                            content=first_result.content if hasattr(first_result, 'content') else str(first_result),
                            lang=lang
                        )
                    else:
                        raise RuntimeError(f"Batch job completed but no results for video {video_id}")
                elif batch_results.status == 'failed':
                    raise RuntimeError(f"Batch job failed for video {video_id}")
            raise TimeoutError(f"Batch job timed out after {max_attempts * 2} seconds for video {video_id}")

    def get_transcripts_batch(self, video_ids: list[str], lang: str = "en") -> list[tuple[str, str | None]]:
        """
            Purpose:
                Fetches transcripts for multiple YouTube videos and returns list of video ID and transcript pairs.
            
            Args:
                video_ids (list[str]): List of YouTube video IDs
                lang (str): Preferred language code (default: en)
            
            Returns:
                list[tuple[str, str | None]]: List of tuples containing (video_id, transcript_text or None if failed)
        """
        results: list[tuple[str, str | None]] = []
        for video_id in video_ids:
            try:
                transcript: Transcript = self.get_transcript(video_id, lang=lang, text=True)
                results.append((video_id, transcript.content if isinstance(transcript.content, str) else None))
            except Exception as error:
                print(f"Failed to get transcript for {video_id}: {error}")
                results.append((video_id, None))
        return results

