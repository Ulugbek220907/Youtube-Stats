import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Config - Use environment variables for security
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "YOUR_YOUTUBE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

def parse_channel_input(user_input):
    user_input = user_input.strip()
    if "youtube.com/" in user_input or "youtu.be/" in user_input:
        if "/channel/" in user_input:
            user_input = user_input.split("/channel/")[1].split("/")[0].split("?")[0]
        elif "/@" in user_input:
            user_input = "@" + user_input.split("/@")[1].split("/")[0].split("?")[0]
        elif "/c/" in user_input:
            user_input = user_input.split("/c/")[1].split("/")[0].split("?")[0]
    return user_input

def get_channel_data(channel_input):
    clean_input = parse_channel_input(channel_input)

    # Direct Channel ID
    if clean_input.startswith("UC") and len(clean_input) == 24:
        url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&id={clean_input}&key={YOUTUBE_API_KEY}"
        res = requests.get(url).json()
        if res.get("items"):
            return res["items"][0]

    # Handle lookup (@handle)
    handle = clean_input if clean_input.startswith("@") else f"@{clean_input}"
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&forHandle={handle}&key={YOUTUBE_API_KEY}"
    res = requests.get(url).json()
    if res.get("items"):
        return res["items"][0]

    # Fallback search
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=id&type=channel&q={clean_input}&maxResults=1&key={YOUTUBE_API_KEY}"
    search_res = requests.get(search_url).json()
    if search_res.get("items"):
        channel_id = search_res["items"][0]["id"]["channelId"]
        url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&id={channel_id}&key={YOUTUBE_API_KEY}"
        res = requests.get(url).json()
        if res.get("items"):
            return res["items"][0]

    return None

def fetch_youtube_report(channel_input):
    channel_data = get_channel_data(channel_input)
    if not channel_data:
        return f"❌ Could not find channel matching: <b>{channel_input}</b>"

    channel_title = channel_data["snippet"]["title"]
    subscribers = int(channel_data["statistics"].get("subscriberCount", 0))
    total_views = int(channel_data["statistics"].get("viewCount", 0))
    video_count = int(channel_data["statistics"].get("videoCount", 0))
    uploads_playlist_id = channel_data["contentDetails"]["relatedPlaylists"]["uploads"]

    # Fetch last 5 videos
    playlist_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={uploads_playlist_id}&maxResults=5&key={YOUTUBE_API_KEY}"
    playlist_res = requests.get(playlist_url).json()
    video_ids = [item["contentDetails"]["videoId"] for item in playlist_res.get("items", [])]

    message = f"📊 <b>YouTube Channel Report: {channel_title}</b>\n"
    message += f"👥 <b>Subscribers:</b> {subscribers:,}\n"
    message += f"👁 <b>Total Views:</b> {total_views:,}\n"
    message += f"🎥 <b>Total Videos:</b> {video_count:,}\n\n"

    if not video_ids:
        message += "<i>No uploaded videos found.</i>"
        return message

    videos_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={','.join(video_ids)}&key={YOUTUBE_API_KEY}"
    videos_res = requests.get(videos_url).json()

    message += "🎬 <b>Last 5 Uploads:</b>\n-------------------------------------\n"

    for idx, video in enumerate(videos_res.get("items", []), start=1):
        v_title = video["snippet"]["title"]
        v_id = video["id"]
        v_stats = video["statistics"]
        views = int(v_stats.get("viewCount", 0))
        likes = int(v_stats.get("likeCount", 0))
        comments = int(v_stats.get("commentCount", 0))

        message += f"<b>{idx}. {v_title}</b>\n🔗 https://youtu.be/{v_id}\n👁 Views: <b>{views:,}</b> | 👍 Likes: <b>{likes:,}</b> | 💬 Comments: <b>{comments:,}</b>\n\n"

    return message

def send_telegram_message(text, chat_id):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(telegram_url, json=payload)

@app.route("/", methods=["POST"])
def telegram_webhook():
    """Telegram sends HTTP POST requests here whenever a user sends a message."""
    data = request.get_json()
    
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text_query = data["message"]["text"].strip()

        send_telegram_message("🔎 Fetching YouTube channel stats...", chat_id)
        report = fetch_youtube_report(text_query)
        send_telegram_message(report, chat_id)

    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def health_check():
    return "Bot is live and waiting for Telegram webhooks!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))