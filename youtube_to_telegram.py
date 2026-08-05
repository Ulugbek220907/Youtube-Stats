import sys
import time
import requests

#CHANNEL_ID = "UCG3o2XkdNP_89jr7LTwLjOQ"


# Config
YOUTUBE_API_KEY = "AIzaSyCscZK6f3HCqJqcvLlW0Vf4T7U_IxE5RxI"
TELEGRAM_BOT_TOKEN = "8842185175:AAFMfkZuliM0aPLg78LpCse5XPJhnGeZKX0"
TELEGRAM_CHAT_ID = "7938793919"


def parse_channel_input(user_input):
    """Extract handle, custom URL name, or channel ID from raw string or full URL."""
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
    """Resolves channel ID, handle, or search query to YouTube channel data."""
    clean_input = parse_channel_input(channel_input)

    # 1. Direct Channel ID (starts with UC and is 24 characters)
    if clean_input.startswith("UC") and len(clean_input) == 24:
        url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&id={clean_input}&key={YOUTUBE_API_KEY}"
        res = requests.get(url).json()
        if res.get("items"):
            return res["items"][0]

    # 2. Lookup by Handle (@handle or handle)
    handle = clean_input if clean_input.startswith("@") else f"@{clean_input}"
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&forHandle={handle}&key={YOUTUBE_API_KEY}"
    res = requests.get(url).json()
    if res.get("items"):
        return res["items"][0]

    # 3. Fallback: Search by name
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

    # Fetch last 5 video IDs
    playlist_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={uploads_playlist_id}&maxResults=5&key={YOUTUBE_API_KEY}"
    playlist_res = requests.get(playlist_url).json()
    
    video_ids = [item["contentDetails"]["videoId"] for item in playlist_res.get("items", [])]

    # Build Header
    message = f"📊 <b>YouTube Channel Report: {channel_title}</b>\n"
    message += f"👥 <b>Subscribers:</b> {subscribers:,}\n"
    message += f"👁 <b>Total Views:</b> {total_views:,}\n"
    message += f"🎥 <b>Total Videos:</b> {video_count:,}\n\n"

    if not video_ids:
        message += "<i>No uploaded videos found.</i>"
        return message

    # Fetch Stats for Videos
    videos_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={','.join(video_ids)}&key={YOUTUBE_API_KEY}"
    videos_res = requests.get(videos_url).json()

    message += "🎬 <b>Last 5 Uploads:</b>\n"
    message += "-------------------------------------\n"

    for idx, video in enumerate(videos_res.get("items", []), start=1):
        v_title = video["snippet"]["title"]
        v_id = video["id"]
        v_stats = video["statistics"]
        
        views = int(v_stats.get("viewCount", 0))
        likes = int(v_stats.get("likeCount", 0))
        comments = int(v_stats.get("commentCount", 0))

        message += f"<b>{idx}. {v_title}</b>\n"
        message += f"🔗 https://youtu.be/{v_id}\n"
        message += f"👁 Views: <b>{views:,}</b> | 👍 Likes: <b>{likes:,}</b> | 💬 Comments: <b>{comments:,}</b>\n\n"

    return message

def send_telegram_message(text, chat_id=TELEGRAM_CHAT_ID):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    return requests.post(telegram_url, json=payload).json()

def start_telegram_bot_listener():
    """Listens for incoming messages in Telegram and replies with requested channel stats."""
    print("🤖 Telegram Bot listener active! Send any channel handle/URL to your bot in Telegram.")
    last_update_id = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            res = requests.get(url).json()

            for update in res.get("result", []):
                last_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    chat_id = update["message"]["chat"]["id"]
                    text_query = update["message"]["text"].strip()

                    send_telegram_message("🔎 Fetching YouTube channel stats...", chat_id=chat_id)
                    report = fetch_youtube_report(text_query)
                    send_telegram_message(report, chat_id=chat_id)

        except Exception as e:
            print("Error in bot listener loop:", e)
            time.sleep(3)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg.lower() == "bot":
            start_telegram_bot_listener()
        else:
            print(f"Fetching report for '{arg}'...")
            report = fetch_youtube_report(arg)
            send_telegram_message(report)
            print("Done!")
    else:
        channel_input = input("Enter YouTube channel handle, URL, or ID (e.g. @mkbhd): ")
        print("Fetching stats...")
        report = fetch_youtube_report(channel_input)
        send_telegram_message(report)
        print("Report sent to Telegram!")