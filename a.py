import requests

BOT_TOKEN = "8842185175:AAFMfkZuliM0aPLg78LpCse5XPJhnGeZKX0"  # e.g., "7123456789:AAFg..."
RENDER_URL = "https://youtube-stats-4pi1.onrender.com/"  # Your Render URL ending with /

res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={RENDER_URL}").json()
print(res)