from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
import datetime
from .config import DATABASE_URL

# SQLAlchemy base and engine/session setup
Base = declarative_base()

# Create engine from DATABASE_URL (supports Neon/PostgreSQL). For SQLite, add thread arg.
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, **engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    original_filename = Column(String)
    duration = Column(Float)  # in seconds
    size = Column(Integer)    # in bytes
    upload_time = Column(DateTime, default=datetime.datetime.utcnow)
    path = Column(String)     # storage path
    is_processed = Column(Boolean, default=False)
    quality = Column(String, default="original")  # original, 1080p, 720p, 480p
    parent_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    
    # Relationship to parent video (for trimmed versions)
    parent = relationship("Video", remote_side=[id])
    
    # Relationship to processing jobs
    jobs = relationship("Job", back_populates="video")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"))
    type = Column(String)  # upload, trim, overlay, watermark, quality
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    parameters = Column(JSON)  # store job-specific parameters
    
    # Relationship to video
    video = relationship("Video", back_populates="jobs")

class Overlay(Base):
    __tablename__ = "overlays"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"))
    type = Column(String)  # text, image, video
    content = Column(String)  # text content or file path
    position = Column(String)  # top-left, top-right, center, etc.
    start_time = Column(Float)  # in seconds
    end_time = Column(Float)    # in seconds
    size = Column(Integer, nullable=True)  # font size or overlay size
    
    # Relationship to video
    video = relationship("Video")