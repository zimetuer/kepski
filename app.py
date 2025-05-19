from flask import Flask, render_template, abort

app = Flask(__name__)

def load_videos_from_file(filename):
    videos = []
    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Split on last space to separate title and URL
            # Because title may contain spaces, URL is last token
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                continue  # skip malformed lines
            title, url = parts
            videos.append({"title": title, "url": url})
    return videos

videos = load_videos_from_file("message(4).txt")

@app.route("/")
def index():
    return render_template("index.html", videos=videos)

@app.route("/<int:episode_id>")
def episode(episode_id):
    if 1 <= episode_id <= len(videos):
        video = videos[episode_id - 1]
        return render_template("episode.html", video=video, episode_id=episode_id)
    else:
        abort(404)

if __name__ == "__main__":
    app.run(debug=True)
