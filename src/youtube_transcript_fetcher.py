from dotenv import load_dotenv
from pathlib import Path

# Load env vars from ../.env (one level above this script)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

import os
import re
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import agenta as ag
from openai import OpenAI
from pinecone import Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.settings import (
    AGENTA_API_KEY,
    AGENTA_HOST_URL,
    OPENAI_API_KEY,
    YOUTUBE_CHANNEL_ID,
    PINECONE_API_KEY,
    PINECONE_TRANSCRIPTIONS_HOST,
    CLOUDFLARE_D1_API_KEY,
    CLOUDFLARE_D1_DATABASE_ID,
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME,
)
from src.resources.youtube.youtube_videos_resource import YoutubeVideosResource
from src.resources.supadata.supadata_transcript_resource import SupadataTranscriptResource

os.environ["AGENTA_API_KEY"] = AGENTA_API_KEY
os.environ["AGENTA_HOST"] = AGENTA_HOST_URL

_VALID_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_D1_API_BASE = "https://api.cloudflare.com/client/v4"


def get_processed_video_ids() -> set[str]:
    """Fetch all processed video IDs from Cloudflare D1."""
    if not _VALID_TABLE_RE.match(CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME):
        raise ValueError("Invalid CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME")
    
    url = f"{_D1_API_BASE}/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{CLOUDFLARE_D1_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_D1_API_KEY}",
        "Content-Type": "application/json",
    }
    sql = f"SELECT id FROM {CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME};"
    payload = {"sql": sql}
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    
    if not body.get("success", False):
        raise RuntimeError(f"Cloudflare D1 SELECT failed: {body}")
    
    results = body.get("result", [{}])[0].get("results", [])
    return {row["id"] for row in results}


def insert_processed_video_id(video_id: str) -> None:
    """Insert a processed video ID into Cloudflare D1."""
    if not _VALID_TABLE_RE.match(CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME):
        raise ValueError("Invalid CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME")
    
    url = f"{_D1_API_BASE}/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{CLOUDFLARE_D1_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_D1_API_KEY}",
        "Content-Type": "application/json",
    }
    sql = f"INSERT OR IGNORE INTO {CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME} (id) VALUES (?1);"
    payload = {"sql": sql, "params": [video_id]}
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    
    if not body.get("success", False):
        raise RuntimeError(f"Cloudflare D1 insert failed: {body}")


def delete_video(video_id: str, pinecone_index) -> None:
    """
    Delete a video from both Cloudflare D1 and Pinecone.
    This function is never called automatically - for manual cleanup only.
    
    Args:
        video_id (str): YouTube video ID to delete
        pinecone_index: Pinecone index instance
    """
    # Delete from Cloudflare D1
    if not _VALID_TABLE_RE.match(CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME):
        raise ValueError("Invalid CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME")
    
    url = f"{_D1_API_BASE}/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{CLOUDFLARE_D1_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_D1_API_KEY}",
        "Content-Type": "application/json",
    }
    sql = f"DELETE FROM {CLOUDFLARE_TRANSCRIPTIONS_ADDED_TABLE_NAME} WHERE id = ?1;"
    payload = {"sql": sql, "params": [video_id]}
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    
    if not body.get("success", False):
        raise RuntimeError(f"Cloudflare D1 delete failed: {body}")
    
    print(f"[{video_id}] Deleted from Cloudflare D1")
    
    # Delete from Pinecone using metadata filter
    pinecone_index.delete(filter={"video_id": {"$eq": video_id}})
    print(f"[{video_id}] Deleted all chunks from Pinecone")


def process_video(
    video_id: str,
    title: str,
    published_at: str,
    transcript_text: str,
    system_prompt: str,
    model: str,
    openai_client: OpenAI,
    pinecone_index,
) -> None:
    """Process a single video: clean, chunk, embed, upsert to Pinecone & D1."""
    try:
        print(f"[{video_id}] Starting processing...")
        print(f"[{video_id}] Transcript already fetched ({len(transcript_text)} chars)")
        
        # Clean with OpenAI
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript_text}
            ]
        )
        cleaned_text = response.choices[0].message.content or ""
        print(f"[{video_id}] Cleaned transcript ({len(cleaned_text)} chars)")
        
        # Chunk
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
        chunks = text_splitter.split_text(cleaned_text)
        print(f"[{video_id}] Created {len(chunks)} chunks")
        
        # Embed
        embedding_response = openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=chunks
        )
        print(f"[{video_id}] Generated embeddings")
        
        # Prepare vectors
        vectors = []
        for chunk_index, embedding_item in enumerate(embedding_response.data):
            vectors.append({
                "id": f"{video_id}:{chunk_index}",
                "values": embedding_item.embedding,
                "metadata": {
                    "video_id": video_id,
                    "video_title": title,
                    "published_at": published_at,
                    "chunk_index": chunk_index,
                    "text": chunks[chunk_index],
                },
            })
        
        # Upsert to Pinecone
        pinecone_index.upsert(vectors=vectors)
        print(f"[{video_id}] Upserted to Pinecone")
        
        # Insert to D1
        insert_processed_video_id(video_id)
        print(f"[{video_id}] Inserted to D1")
        
        print(f"[{video_id}] ✓ Completed processing")
        
    except Exception as error:
        print(f"[{video_id}] ✗ ERROR: {error}")
        raise


def main():
    # Initialize Agenta and fetch config
    ag.init()
    config = ag.ConfigManager.get_from_registry(
        app_slug="Transcription_Cleaning",
        environment_slug="development",
    )
    system_prompt = config['prompt']['messages'][0]['content']
    model = "gpt-5.2-2025-12-11"
    
    print(f"Using model: {model}\n")
    
    # Initialize resources
    youtube_videos_resource = YoutubeVideosResource()
    transcript_resource = SupadataTranscriptResource()
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
    pinecone_index = pinecone_client.Index(host=PINECONE_TRANSCRIPTIONS_HOST)
    
    # Fetch all YouTube videos
    print("Fetching YouTube videos...")
    video_metadata = youtube_videos_resource.search_all_channel_videos_with_metadata(YOUTUBE_CHANNEL_ID)
    print(f"Found {len(video_metadata)} total videos\n")
    
    # Fetch already-processed video IDs
    print("Checking processed videos in D1...")
    processed_ids = get_processed_video_ids()
    print(f"Found {len(processed_ids)} already processed\n")
    
    # Filter to unprocessed videos
    unprocessed_videos = [
        (vid, title, pub_at)
        for vid, title, pub_at in video_metadata
        if vid not in processed_ids
    ]
    print(f"{len(unprocessed_videos)} videos to process\n")
    
    if not unprocessed_videos:
        print("No new videos to process")
        return
    
    # Fetch all transcripts sequentially (rate limit: 1 per second)
    print("Fetching transcripts (2 second delay between each)...\n")
    transcripts_by_id: dict[str, str] = {}
    for idx, (video_id, title, published_at) in enumerate(unprocessed_videos):
        try:
            print(f"[{idx+1}/{len(unprocessed_videos)}] Fetching transcript for {video_id}...")
            transcript = transcript_resource.get_transcript(video_id)
            transcripts_by_id[video_id] = transcript.content
            print(f"[{video_id}] ✓ Transcript fetched ({len(transcript.content)} chars)")
            if idx < len(unprocessed_videos) - 1:
                time.sleep(2)
        except Exception as error:
            print(f"[{video_id}] ✗ Failed to fetch transcript: {error}")
            continue
    
    print(f"\nSuccessfully fetched {len(transcripts_by_id)} transcripts\n")
    
    # Process with ThreadPoolExecutor
    print(f"Starting parallel processing with 8 threads...\n")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(
                process_video,
                video_id,
                title,
                published_at,
                transcripts_by_id[video_id],
                system_prompt,
                model,
                openai_client,
                pinecone_index,
            ): video_id
            for video_id, title, published_at in unprocessed_videos
            if video_id in transcripts_by_id
        }
        
        for future in as_completed(futures):
            video_id = futures[future]
            try:
                future.result()
            except Exception as error:
                print(f"[{video_id}] Failed with exception: {error}")
    
    print("\n✓ All processing complete")


if __name__ == "__main__":
    main()