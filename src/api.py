from flask import Flask, jsonify, request
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from src.youtube_transcript_fetcher import main as run_transcript_fetcher, delete_video
from pinecone import Pinecone
from src.settings import PINECONE_API_KEY, PINECONE_TRANSCRIPTIONS_HOST

app = Flask(__name__)

# Global lock to track if a job is running
job_lock = threading.Lock()
job_running = False


@app.route('/process', methods=['POST'])
def process_transcripts():
    """
    Start processing YouTube transcripts.
    Returns job started or job already running.
    """
    global job_running
    
    # Try to acquire the lock (non-blocking)
    if not job_lock.acquire(blocking=False):
        return jsonify({"status": "job already running"}), 409
    
    try:
        if job_running:
            job_lock.release()
            return jsonify({"status": "job already running"}), 409
        
        job_running = True
        
        # Run the job in a separate thread so we can return immediately
        def run_job():
            global job_running
            try:
                run_transcript_fetcher()
            finally:
                job_running = False
                job_lock.release()
        
        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()
        
        return jsonify({"status": "job started"}), 200
    
    except Exception as e:
        job_running = False
        job_lock.release()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/delete/<video_id>', methods=['DELETE'])
def delete_video_endpoint(video_id: str):
    """
    Delete a video from Cloudflare D1 and Pinecone.
    Only works when no other job is running.
    """
    global job_running
    
    # Try to acquire the lock (non-blocking)
    if not job_lock.acquire(blocking=False):
        return jsonify({"status": "something's in progress"}), 409
    
    try:
        if job_running:
            job_lock.release()
            return jsonify({"status": "something's in progress"}), 409
        
        job_running = True
        
        # Initialize Pinecone
        pc = Pinecone(api_key=PINECONE_API_KEY)
        pinecone_index = pc.Index(host=PINECONE_TRANSCRIPTIONS_HOST)
        
        # Run the deletion
        delete_video(video_id, pinecone_index)
        
        return jsonify({"status": "started", "video_id": video_id}), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        job_running = False
        job_lock.release()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "job_running": job_running}), 200


def scheduled_process():
    """
    Scheduled job that triggers transcript processing.
    Runs every Sunday at 1PM CST.
    """
    global job_running
    
    # Try to acquire the lock (non-blocking)
    if not job_lock.acquire(blocking=False):
        print("Scheduled job skipped - another job is already running")
        return
    
    try:
        if job_running:
            job_lock.release()
            print("Scheduled job skipped - another job is already running")
            return
        
        job_running = True
        print("Starting scheduled transcript processing...")
        
        # Run the job in a separate thread
        def run_job():
            global job_running
            try:
                run_transcript_fetcher()
                print("Scheduled transcript processing completed")
            except Exception as e:
                print(f"Scheduled job failed: {e}")
            finally:
                job_running = False
                job_lock.release()
        
        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()
    
    except Exception as e:
        print(f"Error starting scheduled job: {e}")
        job_running = False
        job_lock.release()


# Initialize scheduler
scheduler = BackgroundScheduler(timezone=pytz.timezone('America/Chicago'))

# Schedule job for every Sunday at 1PM CST
scheduler.add_job(
    func=scheduled_process,
    trigger=CronTrigger(day_of_week='sun', hour=20, minute=0, timezone='America/Chicago'),
    id='sunday_transcript_job',
    name='Process transcripts every Sunday',
    replace_existing=True
)

# Start the scheduler
scheduler.start()
print("Scheduler started - will run every Sunday at 1PM CST")


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        # Shutdown the scheduler when the app stops
        scheduler.shutdown()
