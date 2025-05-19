import os
from flask import Flask, render_template, abort, request, redirect, url_for, send_file, make_response
from urllib.parse import urlparse
import re

app = Flask(__name__)

# Add CORS headers for Discord
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def load_videos_from_file(filename):
    """Load videos from a text file with format: 'Title URL'"""
    videos = []
    try:
        with open(filename, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Split on the last space to handle titles with spaces
                parts = line.rsplit(" ", 1)
                if len(parts) != 2:
                    continue
                title, url = parts
                
                # Extract episode number for better organization
                episode_match = re.search(r'Odcinek (\d+)', title)
                episode_num = int(episode_match.group(1)) if episode_match else 0
                
                videos.append({
                    "title": title,
                    "url": url.strip(),
                    "episode_num": episode_num
                })
        
        # Sort videos by episode number
        videos.sort(key=lambda x: x["episode_num"])
        
        print(f"Loaded {len(videos)} videos from {filename}")
    except FileNotFoundError:
        print(f"Warning: {filename} not found. No videos loaded.")
    
    return videos

def is_valid_video_url(url):
    """Check if the URL points to a valid video file format"""
    video_extensions = ['.mp4', '.webm', '.ogg', '.mov', '.m4v']
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    return any(path.endswith(ext) for ext in video_extensions)

def get_base_url(request):
    """Get the base URL for the application"""
    # For production, use HTTPS
    if request.host != '0.0.0.0:8080' and request.host != 'localhost:8080':
        return f"https://{request.host}"
    else:
        # For local development
        return f"http://{request.host}"

# Load videos from the file
videos = load_videos_from_file("message(4).txt")

@app.route("/")
def index():
    """Render the index page with a list of all videos"""
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of videos per page
    
    # Calculate pagination
    total_pages = (len(videos) + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(videos))
    
    current_videos = videos[start_idx:end_idx]
    
    return render_template(
        "index.html", 
        videos=current_videos,
        total_videos=len(videos),
        current_page=page,
        total_pages=total_pages,
        min=min
    )

@app.route("/odc/<int:episode_id>")
def episode(episode_id):
    """Render a specific video episode page"""
    # Find the video with matching episode number
    video = next((v for v in videos if v["episode_num"] == episode_id), None)
    
    if video:
        base_url = get_base_url(request)
        
        # For Discord embeds, we need the direct video file URL
        video_file_url = f"{base_url}/odc_file/{episode_id}"
        
        # Get next and previous episode IDs
        current_index = videos.index(video)
        prev_video = videos[current_index - 1] if current_index > 0 else None
        next_video = videos[current_index + 1] if current_index < len(videos) - 1 else None
        
        prev_id = prev_video["episode_num"] if prev_video else None
        next_id = next_video["episode_num"] if next_video else None
        
        return render_template(
            "episode.html", 
            video=video, 
            episode_id=episode_id,
            video_file_url=video_file_url,
            prev_id=prev_id,
            next_id=next_id,
            total_episodes=len(videos)
        )
    else:
        abort(404)

@app.route("/odc_file/<int:episode_id>")
def video_file(episode_id):
    """Serve the video file directly with proper headers for Discord"""
    # Find the video with matching episode number
    video = next((v for v in videos if v["episode_num"] == episode_id), None)
    
    if video:
        video_url = video["url"]
        
        # If the URL is a local file path
        if os.path.exists(video_url):
            # Get file size for Content-Length header
            file_size = os.path.getsize(video_url)
            
            def generate():
                with open(video_url, 'rb') as f:
                    while True:
                        data = f.read(4096)
                        if not data:
                            break
                        yield data
            
            response = make_response(generate())
            response.headers['Content-Type'] = 'video/mp4'
            response.headers['Content-Length'] = str(file_size)
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            
            # Handle range requests for video seeking
            range_header = request.headers.get('Range', None)
            if range_header:
                byte_start = 0
                byte_end = file_size - 1
                
                if range_header:
                    match = re.search(r'bytes=(\d+)-(\d*)', range_header)
                    if match:
                        byte_start = int(match.group(1))
                        if match.group(2):
                            byte_end = int(match.group(2))
                
                content_length = byte_end - byte_start + 1
                
                def generate_range():
                    with open(video_url, 'rb') as f:
                        f.seek(byte_start)
                        remaining = content_length
                        while remaining:
                            chunk_size = min(4096, remaining)
                            data = f.read(chunk_size)
                            if not data:
                                break
                            remaining -= len(data)
                            yield data
                
                response = make_response(generate_range())
                response.headers['Content-Type'] = 'video/mp4'
                response.headers['Content-Range'] = f'bytes {byte_start}-{byte_end}/{file_size}'
                response.headers['Content-Length'] = str(content_length)
                response.headers['Accept-Ranges'] = 'bytes'
                response.status_code = 206
            
            return response
        
        # If it's a remote URL, redirect to it
        return redirect(video_url)
    else:
        abort(404)

@app.route("/search")
def search():
    """Search for videos by title"""
    query = request.args.get('q', '').lower()
    if not query:
        return redirect(url_for('index'))
    
    results = [
        video for video in videos 
        if query in video["title"].lower()
    ]
    
    return render_template(
        "search_results.html", 
        videos=results,
        query=query,
        total_results=len(results)
    )

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)