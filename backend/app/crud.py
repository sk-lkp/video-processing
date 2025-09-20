from sqlalchemy.orm import Session
import datetime
from .database import Video, Job

def get_job(db: Session, job_id: int):
    """Fetch a Job by its primary key ID."""
    return db.query(Job).filter(Job.id == job_id).first()

def get_video(db: Session, video_id: int):
    return db.query(Video).filter(Video.id == video_id).first()

def get_videos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Video).offset(skip).limit(limit).all()

def create_video(db: Session, **video_fields):
    db_video = Video(**video_fields)
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

def update_video_metadata(db: Session, video_id: int, duration: float, size: int):
    db_video = db.query(Video).filter(Video.id == video_id).first()
    if db_video:
        db_video.duration = duration
        db_video.size = size
        db_video.is_processed = True
        db.commit()
        db.refresh(db_video)
    return db_video

def get_job_by_job_id(db: Session, job_id: str):
    return db.query(Job).filter(Job.job_id == job_id).first()

def create_job(db: Session, **job_fields):
    # Ensure parameters is a dict, not None
    if "parameters" not in job_fields or job_fields["parameters"] is None:
        job_fields["parameters"] = {}
    db_job = Job(**job_fields)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def update_job_status(db: Session, job_id: int, status: str, result: dict = None):
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if db_job:
        db_job.status = status
        if status == "completed":
            db_job.completed_at = datetime.datetime.utcnow()
        if result:
            existing = db_job.parameters or {}
            db_job.parameters = {**existing, **result}
        db.commit()
        db.refresh(db_job)
    return db_job