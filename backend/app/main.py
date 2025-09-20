from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List
import uuid
import os
import shutil
from pathlib import Path

from .database import SessionLocal, engine, Base
from . import crud, schemas, video_processor
from .celery_worker import process_video_upload, process_video_trim, process_quality_change, process_b_roll_overlay, process_image_overlay, process_watermark

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Video Processing API", version="1.0.0")

# Create static directories if they don't exist
Path("static/videos").mkdir(parents=True, exist_ok=True)
Path("static/watermarks").mkdir(parents=True, exist_ok=True)
Path("static/assets/base_videos").mkdir(parents=True, exist_ok=True)
Path("static/assets/overlay_videos").mkdir(parents=True, exist_ok=True)
Path("static/assets/overlay_images").mkdir(parents=True, exist_ok=True)

@app.post("/upload", response_model=schemas.Job)
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file"""
    db = SessionLocal()
    try:
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join("static", "videos", filename)
        
        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Create video record
        video = crud.create_video(
            db, 
            filename=filename,
            original_filename=file.filename,
            duration=0,  # Will be updated by celery task
            size=0,      # Will be updated by celery task
            path=file_path
        )
        
        # Create job record
        job = crud.create_job(
            db,
            job_id=str(uuid.uuid4()),
            video_id=video.id,
            type="upload"
        )
        
        # Process video metadata asynchronously
        process_video_upload.delay(file_path, file.filename, video.id, job.id)
        
        return job
    except HTTPException as e:
        # Propagate HTTP errors (e.g., 4xx) as-is
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/upload/base-video")
async def upload_base_video():
    """Upload the provided base video (A-roll.mp4)"""
    base_video_path = "static/assets/base_videos/A-roll.mp4"
    
    if not os.path.exists(base_video_path):
        raise HTTPException(status_code=404, detail="Base video not found")
    
    # Copy to uploads directory
    filename = f"base_{uuid.uuid4().hex}.mp4"
    file_path = os.path.join("static", "videos", filename)
    
    shutil.copy(base_video_path, file_path)
    
    # Create video record
    db = SessionLocal()
    try:
        duration = video_processor.get_video_duration(file_path)
        size = video_processor.get_video_size(file_path)
        
        video = crud.create_video(
            db, 
            filename=filename,
            original_filename="A-roll.mp4",
            duration=duration,
            size=size,
            path=file_path,
            is_processed=True
        )
        
        return video
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/videos", response_model=List[schemas.Video])
def list_videos(skip: int = 0, limit: int = 100):
    """List all uploaded videos"""
    db = SessionLocal()
    try:
        videos = crud.get_videos(db, skip=skip, limit=limit)
        return videos
    finally:
        db.close()

@app.post("/trim", response_model=schemas.Job)
def trim_video(request: schemas.TrimRequest):
    """Trim a video"""
    db = SessionLocal()
    try:
        # Check if video exists
        video = crud.get_video(db, request.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Create job record
        job = crud.create_job(
            db,
            job_id=str(uuid.uuid4()),
            video_id=video.id,
            type="trim",
            parameters={
                "start_time": request.start_time,
                "end_time": request.end_time
            }
        )
        
        # Process trimming asynchronously
        process_video_trim.delay(video.id, request.start_time, request.end_time, job.id)
        
        return job
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/quality", response_model=schemas.Job)
def change_quality(request: schemas.QualityRequest):
    """Change video quality"""
    db = SessionLocal()
    try:
        # Check if video exists
        video = crud.get_video(db, request.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Validate quality parameter
        if request.quality not in ["1080p", "720p", "480p"]:
            raise HTTPException(status_code=400, detail="Invalid quality parameter")
        
        # Create job record
        job = crud.create_job(
            db,
            job_id=str(uuid.uuid4()),
            video_id=video.id,
            type="quality",
            parameters={
                "quality": request.quality
            }
        )
        
        # Process quality change asynchronously
        process_quality_change.delay(video.id, request.quality, job.id)
        
        return job
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/overlay/b-roll/{video_id}")
async def add_b_roll_overlay_endpoint(
    video_id: int, 
    b_roll_name: str = "B-roll 1",  # Can be "B-roll 1" or "B-roll 2"
    position: str = "top-right",
    start_time: float = 0,
    end_time: float = None
):
    """Add a B-roll video overlay using provided assets"""
    db = SessionLocal()
    try:
        # Get base video
        base_video = crud.get_video(db, video_id)
        if not base_video:
            raise HTTPException(status_code=404, detail="Base video not found")
        
        # Determine B-roll path
        b_roll_path = f"static/assets/overlay_videos/{b_roll_name}.mp4"
        if not os.path.exists(b_roll_path):
            raise HTTPException(status_code=404, detail="B-roll video not found")
        
        # Create output filename
        output_filename = f"with_{b_roll_name}_{uuid.uuid4().hex}.mp4"
        output_path = os.path.join("static", "videos", output_filename)
        
        # Create job record
        job = crud.create_job(
            db,
            job_id=str(uuid.uuid4()),
            video_id=video_id,
            type="b_roll_overlay",
            parameters={
                "b_roll_name": b_roll_name,
                "position": position,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        
        # Process asynchronously
        process_b_roll_overlay.delay(
            base_video.path, 
            b_roll_path, 
            output_path, 
            position, 
            start_time, 
            end_time, 
            job.id
        )
        
        return job
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/overlay/image/{video_id}")
async def add_image_overlay_endpoint(
    video_id: int, 
    position: str = "bottom-right",
    start_time: float = 0,
    end_time: float = None
):
    """Add image overlay using provided asset"""
    db = SessionLocal()
    try:
        # Get base video
        base_video = crud.get_video(db, video_id)
        if not base_video:
            raise HTTPException(status_code=404, detail="Base video not found")
        
        # Determine image path
        image_path = "static/assets/overlay_images/image overlay.png"
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image overlay not found")
        
        # Create output filename
        output_filename = f"with_image_overlay_{uuid.uuid4().hex}.mp4"
        output_path = os.path.join("static", "videos", output_filename)
        
        # Create job record
        job = crud.create_job(
            db,
            job_id=str(uuid.uuid4()),
            video_id=video_id,
            type="image_overlay",
            parameters={
                "position": position,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        
        # Process asynchronously
        process_image_overlay.delay(
            base_video.path, 
            image_path, 
            output_path, 
            position, 
            start_time, 
            end_time, 
            job.id
        )
        
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/status/{job_id}", response_model=schemas.Job)
def get_job_status(job_id: str):
    """Get job status"""
    db = SessionLocal()
    try:
        job = crud.get_job_by_job_id(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    finally:
        db.close()

@app.get("/download/{video_id}")
def download_video(video_id: int):
    """Download a video"""
    db = SessionLocal()
    try:
        video = crud.get_video(db, video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if not os.path.exists(video.path):
            raise HTTPException(status_code=404, detail="Video file not found")
        
        return FileResponse(
            video.path, 
            media_type="video/mp4",
            filename=video.original_filename
        )
    finally:
        db.close()

@app.get("/available-assets")
def get_available_assets():
    """Get list of available assets for processing"""
    assets = {
        "base_videos": ["A-roll.mp4"],
        "overlay_videos": ["B-roll 1.mp4", "B-roll 2.mp4"],
        "overlay_images": ["image overlay.png"]
    }
    return assets

@app.post("/demo/full-processing")
async def demo_full_processing():
    """Demo endpoint that showcases all processing capabilities with your assets"""
    db = SessionLocal()
    try:
        # Step 1: Upload base video
        base_video = await upload_base_video()
        
        # Step 2: Add B-roll 1 overlay
        broll1_job = await add_b_roll_overlay_endpoint(
            base_video.id, 
            "B-roll 1", 
            "top-right", 
            5,  # start at 5 seconds
            15   # end at 15 seconds
        )
        
        # Step 3: Add B-roll 2 overlay
        broll2_job = await add_b_roll_overlay_endpoint(
            base_video.id, 
            "B-roll 2", 
            "bottom-left", 
            10,  # start at 10 seconds
            20   # end at 20 seconds
        )
        
        # Step 4: Add image overlay
        image_job = await add_image_overlay_endpoint(
            base_video.id,
            "bottom-right",
            0,   # start at beginning
            None  # show throughout video
        )
        
        return {
            "message": "Full processing demo started",
            "base_video_id": base_video.id,
            "jobs": {
                "broll1": broll1_job.job_id,
                "broll2": broll2_job.job_id,
                "image": image_job.job_id
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/watermark")
def add_watermark_to_video(video_id: int, watermark_file: UploadFile = File(...), position: str = "top-right"):
    """Add watermark to video"""
    db = SessionLocal()
    try:
        # Validate base video
        video = crud.get_video(db, video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Save uploaded watermark file to static/watermarks
        file_ext = os.path.splitext(watermark_file.filename)[1]
        watermark_filename = f"watermark_{uuid.uuid4().hex}{file_ext}"
        watermark_path = os.path.join("static", "watermarks", watermark_filename)
        with open(watermark_path, "wb") as f:
            content = watermark_file.file.read()
            f.write(content)

        # Prepare output
        output_filename = f"with_watermark_{uuid.uuid4().hex}.mp4"
        output_path = os.path.join("static", "videos", output_filename)

        # Create job
        job = crud.create_job(
            db,
            job_id=str(uuid.uuid4()),
            video_id=video.id,
            type="watermark",
            parameters={
                "position": position
            }
        )

        # Enqueue processing
        process_watermark.delay(
            video.path,
            watermark_path,
            output_path,
            position,
            job.id
        )

        return job
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/overlay/text")
def add_text_overlay_to_video(video_id: int, text: str, position: str = "top-left", fontsize: int = 24):
    """Add text overlay to video"""
    # Implementation similar to other endpoints
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



'''from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List
import uuid
import os
from pathlib import Path

from .database import SessionLocal, engine, Base
from . import crud, schemas, video_processor
from .celery_worker import process_video_upload, process_video_trim, process_quality_change

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Video Processing API", version="1.0.0")

# Create static directories if they don't exist
Path("static/videos").mkdir(parents=True, exist_ok=True)
Path("static/watermarks").mkdir(parents=True, exist_ok=True)

@app.post("/upload", response_model=schemas.Job)
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file"""
    db = SessionLocal()
    try:
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join("static", "videos", filename)
        
        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Create video record
        video = crud.create_video(
            db, 
            filename=filename,
            original_filename=file.filename,
            duration=0,  # Will be updated by celery task
            size=0,      # Will be updated by celery task
            path=file_path
        )
        
        # Create job record
        job = crud.create_job(
            db,
            job_id=str(uuid.uuid4()),
            video_id=video.id,
            type="upload"
        )
        
        # Process video metadata asynchronously
        process_video_upload.delay(file_path, file.filename, video.id, job.id)
        
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/videos", response_model=List[schemas.Video])
def list_videos(skip: int = 0, limit: int = 100):
    """List all uploaded videos"""
    db = SessionLocal()
    try:
        videos = crud.get_videos(db, skip=skip, limit=limit)
        return videos
    finally:
        db.close()

@app.post("/trim", response_model=schemas.Job)
def trim_video(request: schemas.TrimRequest):
    """Trim a video"""
    db = SessionLocal()
    try:
        # Check if video exists
        video = crud.get_video(db, request.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Create job record
        job = crud.create_job(
            db,
            job_id=str(uuid.uuid4()),
            video_id=video.id,
            type="trim",
            parameters={
                "start_time": request.start_time,
                "end_time": request.end_time
            }
        )
        
        # Process trimming asynchronously
        process_video_trim.delay(video.id, request.start_time, request.end_time, job.id)
        
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/quality", response_model=schemas.Job)
def change_quality(request: schemas.QualityRequest):
    """Change video quality"""
    db = SessionLocal()
    try:
        # Check if video exists
        video = crud.get_video(db, request.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Validate quality parameter
        if request.quality not in ["1080p", "720p", "480p"]:
            raise HTTPException(status_code=400, detail="Invalid quality parameter")
        
        # Create job record
        job = crud.create_job(
            db,
            job_id=str(uuid.uuid4()),
            video_id=video.id,
            type="quality",
            parameters={
                "quality": request.quality
            }
        )
        
        # Process quality change asynchronously
        process_quality_change.delay(video.id, request.quality, job.id)
        
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/status/{job_id}", response_model=schemas.Job)
def get_job_status(job_id: str):
    """Get job status"""
    db = SessionLocal()
    try:
        job = crud.get_job_by_job_id(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    finally:
        db.close()

@app.get("/download/{video_id}")
def download_video(video_id: int):
    """Download a video"""
    db = SessionLocal()
    try:
        video = crud.get_video(db, video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if not os.path.exists(video.path):
            raise HTTPException(status_code=404, detail="Video file not found")
        
        return FileResponse(
            video.path, 
            media_type="video/mp4",
            filename=video.original_filename
        )
    finally:
        db.close()

@app.post("/watermark")
def add_watermark_to_video(video_id: int, watermark_file: UploadFile = File(...), position: str = "top-right"):
    """Add watermark to video"""
    # Implementation similar to other endpoints
    pass

@app.post("/overlay/text")
def add_text_overlay_to_video(video_id: int, text: str, position: str = "top-left", fontsize: int = 24):
    """Add text overlay to video"""
    # Implementation similar to other endpoints
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)'''