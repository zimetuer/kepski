import os
from flask import Flask, render_template, abort, request, redirect, url_for
from urllib.parse import urlparse
import re

app = Flask(__name__)

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

@app.route("/video/<int:episode_id>")
def episode(episode_id):
    """Render a specific video episode page"""
    if 1 <= episode_id <= len(videos):
        video = videos[episode_id - 1]
        
        # Get current absolute URL for OpenGraph tags
        if request.host == '0.0.0.0:8080':
            # Local development
            base_url = f"http://{request.host}"
        else:
            # Production
            base_url = f"https://{request.host}"
        
        video_url = f"{base_url}/video/{episode_id}"
        
        # Get next and previous episode IDs
        prev_id = episode_id - 1 if episode_id > 1 else None
        next_id = episode_id + 1 if episode_id < len(videos) else None
        
        return render_template(
            "episode.html", 
            video=video, 
            episode_id=episode_id,
            video_url=video_url,
            prev_id=prev_id,
            next_id=next_id,
            total_episodes=len(videos)
        )
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