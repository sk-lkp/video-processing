import os
import subprocess
import uuid
from pathlib import Path

def get_video_duration(file_path):
    """Get video duration using ffprobe"""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 
        'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout)

def get_video_size(file_path):
    """Get video file size"""
    return os.path.getsize(file_path)

def trim_video(input_path, output_path, start_time, end_time):
    """Trim video using ffmpeg"""
    cmd = [
        'ffmpeg', '-i', input_path, '-ss', str(start_time), 
        '-to', str(end_time), '-c', 'copy', output_path
    ]
    subprocess.run(cmd, check=True)

def add_watermark(input_path, output_path, watermark_path, position="top-left"):
    """Add watermark to video"""
    # Calculate position based on input
    if position == "top-left":
        overlay = "10:10"
    elif position == "top-right":
        overlay = "main_w-overlay_w-10:10"
    elif position == "bottom-left":
        overlay = "10:main_h-overlay_h-10"
    elif position == "bottom-right":
        overlay = "main_w-overlay_w-10:main_h-overlay_h-10"
    else:  # center
        overlay = "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
    
    cmd = [
        'ffmpeg', '-i', input_path, '-i', watermark_path,
        '-filter_complex', f'overlay={overlay}', '-codec:a', 'copy', output_path
    ]
    subprocess.run(cmd, check=True)

def add_text_overlay(input_path, output_path, text, position="top-left", fontsize=24, fontcolor="white"):
    """Add text overlay to video"""
    # Calculate position based on input
    if position == "top-left":
        xy = "10:10"
    elif position == "top-right":
        xy = "w-text_w-10:10"
    elif position == "bottom-left":
        xy = "10:h-text_h-10"
    elif position == "bottom-right":
        xy = "w-text_w-10:h-text_h-10"
    else:  # center
        xy = "(w-text_w)/2:(h-text_h)/2"
    
    # Handle different Indian language fonts
    font_path = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"  # Default, can be customized
    
    cmd = [
        'ffmpeg', '-i', input_path,
        '-vf', f"drawtext=text='{text}':fontfile={font_path}:fontsize={fontsize}:fontcolor={fontcolor}:x={xy}",
        '-codec:a', 'copy', output_path
    ]
    subprocess.run(cmd, check=True)

def change_quality(input_path, output_path, quality):
    """Change video quality"""
    if quality == "1080p":
        resolution = "1920x1080"
        bitrate = "4000k"
    elif quality == "720p":
        resolution = "1280x720"
        bitrate = "2500k"
    elif quality == "480p":
        resolution = "854x480"
        bitrate = "1000k"
    else:
        resolution = "1920x1080"
        bitrate = "4000k"
    
    cmd = [
        'ffmpeg', '-i', input_path, '-s', resolution, 
        '-b:v', bitrate, '-c:a', 'copy', output_path
    ]
    subprocess.run(cmd, check=True)

def add_b_roll_overlay(input_path, b_roll_path, output_path, position="top-right", start_time=0, end_time=None):
    """Add B-roll video overlay with timing"""
    # Calculate position
    if position == "top-left":
        overlay = "10:10"
    elif position == "top-right":
        overlay = "main_w-overlay_w-10:10"
    elif position == "bottom-left":
        overlay = "10:main_h-overlay_h-10"
    elif position == "bottom-right":
        overlay = "main_w-overlay_w-10:main_h-overlay_h-10"
    else:  # center
        overlay = "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
    
    # Add timing if specified
    if end_time is not None:
        filter_complex = f"[0:v][1:v] overlay={overlay}:enable='between(t,{start_time},{end_time})' [v]"
    else:
        filter_complex = f"[0:v][1:v] overlay={overlay} [v]"
    
    cmd = [
        'ffmpeg', '-i', input_path, '-i', b_roll_path,
        '-filter_complex', filter_complex,
        '-map', '[v]', '-map', '0:a', '-c:a', 'copy', output_path
    ]
    subprocess.run(cmd, check=True)

def add_image_overlay(input_path, image_path, output_path, position="bottom-right", start_time=0, end_time=None):
    """Add image overlay with timing"""
    # Calculate position
    if position == "top-left":
        overlay = "10:10"
    elif position == "top-right":
        overlay = "main_w-overlay_w-10:10"
    elif position == "bottom-left":
        overlay = "10:main_h-overlay_h-10"
    elif position == "bottom-right":
        overlay = "main_w-overlay_w-10:main_h-overlay_h-10"
    else:  # center
        overlay = "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
    
    # Add timing if specified
    if end_time is not None:
        filter_complex = f"[0:v][1:v] overlay={overlay}:enable='between(t,{start_time},{end_time})' [v]"
    else:
        filter_complex = f"[0:v][1:v] overlay={overlay} [v]"
    
    cmd = [
        'ffmpeg', '-i', input_path, '-i', image_path,
        '-filter_complex', filter_complex,
        '-map', '[v]', '-map', '0:a', '-c:a', 'copy', output_path
    ]
    subprocess.run(cmd, check=True) 
