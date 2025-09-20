from celery import Celery
from .database import SessionLocal
from . import crud, video_processor
import os
from pathlib import Path
import uuid
from .config import REDIS_URL

# Celery configuration
celery_app = Celery(
    'video_processing',
    broker=REDIS_URL,
    backend=REDIS_URL
)

@celery_app.task
def process_video_upload(file_path, original_filename, video_id, job_id):
    """Process video upload - calculate duration and size"""
    db = SessionLocal()
    try:
        crud.update_job_status(db, job_id, "processing")
        duration = video_processor.get_video_duration(file_path)
        size = video_processor.get_video_size(file_path)
        
        # Update video record with metadata
        crud.update_video_metadata(db, video_id, duration, size)
        
        # Mark job as completed
        crud.update_job_status(db, job_id, "completed")
    except Exception as e:
        crud.update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()

@celery_app.task
def process_video_trim(video_id, start_time, end_time, job_id):
    """Process video trimming"""
    db = SessionLocal()
    try:
        crud.update_job_status(db, job_id, "processing")
        # Get original video
        video = crud.get_video(db, video_id)
        
        # Create output path
        output_filename = f"trimmed_{video.id}_{uuid.uuid4().hex}.mp4"
        output_path = os.path.join("static", "videos", output_filename)
        
        # Trim video
        video_processor.trim_video(video.path, output_path, start_time, end_time)
        
        # Create new video record for trimmed version
        duration = video_processor.get_video_duration(output_path)
        size = video_processor.get_video_size(output_path)
        
        new_video = crud.create_video(
            db, 
            filename=output_filename,
            original_filename=f"trimmed_{video.original_filename}",
            duration=duration,
            size=size,
            path=output_path,
            parent_id=video.id,
            quality=video.quality
        )
        
        # Update job status
        crud.update_job_status(db, job_id, "completed", {"new_video_id": new_video.id})
    except Exception as e:
        crud.update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()

@celery_app.task
def process_quality_change(video_id, quality, job_id):
    """Process quality change"""
    db = SessionLocal()
    try:
        crud.update_job_status(db, job_id, "processing")
        # Get original video
        video = crud.get_video(db, video_id)
        
        # Create output path
        output_filename = f"{quality}_{video.id}_{uuid.uuid4().hex}.mp4"
        output_path = os.path.join("static", "videos", output_filename)
        
        # Change quality
        video_processor.change_quality(video.path, output_path, quality)
        
        # Create new video record for quality version
        duration = video_processor.get_video_duration(output_path)
        size = video_processor.get_video_size(output_path)
        
        new_video = crud.create_video(
            db, 
            filename=output_filename,
            original_filename=f"{quality}_{video.original_filename}",
            duration=duration,
            size=size,
            path=output_path,
            parent_id=video.id,
            quality=quality
        )
        
        # Update job status
        crud.update_job_status(db, job_id, "completed", {"new_video_id": new_video.id})
    except Exception as e:
        crud.update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()

@celery_app.task
def process_b_roll_overlay(base_video_path, b_roll_path, output_path, position, start_time, end_time, job_id):
    """Process B-roll overlay"""
    db = SessionLocal()
    try:
        crud.update_job_status(db, job_id, "processing")
        # Add B-roll overlay
        video_processor.add_b_roll_overlay(
            base_video_path, b_roll_path, output_path, 
            position, start_time, end_time
        )
        
        # Create new video record
        duration = video_processor.get_video_duration(output_path)
        size = video_processor.get_video_size(output_path)
        
        # Get base video ID from job
        job = crud.get_job(db, job_id)
        base_video_id = job.video_id
        
        new_video = crud.create_video(
            db, 
            filename=os.path.basename(output_path),
            original_filename=f"with_broll_{os.path.basename(base_video_path)}",
            duration=duration,
            size=size,
            path=output_path,
            is_processed=True,
            parent_id=base_video_id
        )
        
        # Update job status
        crud.update_job_status(db, job_id, "completed", {"new_video_id": new_video.id})
    except Exception as e:
        crud.update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()

@celery_app.task
def process_image_overlay(base_video_path, image_path, output_path, position, start_time, end_time, job_id):
    """Process image overlay"""
    db = SessionLocal()
    try:
        crud.update_job_status(db, job_id, "processing")
        # Add image overlay
        video_processor.add_image_overlay(
            base_video_path, image_path, output_path, 
            position, start_time, end_time
        )
        
        # Create new video record
        duration = video_processor.get_video_duration(output_path)
        size = video_processor.get_video_size(output_path)
        
        # Get base video ID from job
        job = crud.get_job(db, job_id)
        base_video_id = job.video_id
        
        new_video = crud.create_video(
            db, 
            filename=os.path.basename(output_path),
            original_filename=f"with_image_{os.path.basename(base_video_path)}",
            duration=duration,
            size=size,
            path=output_path,
            is_processed=True,
            parent_id=base_video_id
        )
        
        # Update job status
        crud.update_job_status(db, job_id, "completed", {"new_video_id": new_video.id})
    except Exception as e:
        crud.update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()   

@celery_app.task
def process_watermark(base_video_path, watermark_path, output_path, position, job_id):
    """Process adding an image watermark to a video"""
    db = SessionLocal()
    try:
        crud.update_job_status(db, job_id, "processing")
        # Add watermark
        video_processor.add_watermark(
            base_video_path, output_path, watermark_path, position
        )
        
        # Create new video record
        duration = video_processor.get_video_duration(output_path)
        size = video_processor.get_video_size(output_path)
        
        # Get base video ID from job
        job = crud.get_job(db, job_id)
        base_video_id = job.video_id
        
        new_video = crud.create_video(
            db,
            filename=os.path.basename(output_path),
            original_filename=f"with_watermark_{os.path.basename(base_video_path)}",
            duration=duration,
            size=size,
            path=output_path,
            is_processed=True,
            parent_id=base_video_id
        )
        
        # Update job status
        crud.update_job_status(db, job_id, "completed", {"new_video_id": new_video.id})
    except Exception as e:
        crud.update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()
