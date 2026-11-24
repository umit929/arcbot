import os
import sys
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import tasks, commands
import requests
from aiohttp import web

sys.stdout.reconfigure(line_buffering=True)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
# Kanal ID'sinin (UC...) başındaki UC yerine UU yazınca doğrudan Yüklemeler listesi alınır
UPLOADS_PLAYLIST_ID = 'UURlsFZE_4iXGyi2Dhxcduhg'
DISCORD_CHANNEL_ID = 1551892041737183332
YOUTUBE_ROLE_ID = "1554137072003190794"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
seen_video_ids = set()
is_initial_check = True

async def handle_ping(request):
    return web.Response(text="ArcBot 7/24 Aktif!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

@bot.event
async def setup_hook():
    bot.loop.create_task(start_web_server())
    check_youtube.start()

@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} YouTube nöbetine başladı!', flush=True)

def parse_yt_time(time_str):
    return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

@tasks.loop(minutes=3)
async def check_youtube():
    global seen_video_ids, is_initial_check
    if not YOUTUBE_API_KEY:
        return

    playlist_url = f"https://www.googleapis.com/youtube/v3/playlistItems?key={YOUTUBE_API_KEY}&playlistId={UPLOADS_PLAYLIST_ID}&part=snippet&maxResults=5"
    
    try:
        response = requests.get(playlist_url).json()
        if "items" not in response:
            return

        candidate_ids = []
        for item in response["items"]:
            v_id = item["snippet"]["resourceId"].get("videoId")
            if v_id and v_id not in seen_video_ids:
                candidate_ids.append(v_id)

        if not candidate_ids:
            is_initial_check = False
            return

        # Tüm yeni adayların kesin yayın durumunu tek istekte sorgula
        ids_param = ",".join(candidate_ids)
        detail_url = f"https://www.googleapis.com/youtube/v3/videos?key={YOUTUBE_API_KEY}&id={ids_param}&part=snippet,liveStreamingDetails"
        detail_res = requests.get(detail_url).json()

        now_utc = datetime.now(timezone.utc)

        for v_item in detail_res.get("items", []):
            video_id = v_item["id"]
            snippet = v_item["snippet"]
            live_status = snippet.get("liveBroadcastContent") # 'upcoming', 'live' veya 'none'
            live_details = v_item.get("liveStreamingDetails", {})

            # Yayın henüz planlama aşamasındaysa bekle, hafızaya alma
            if live_status == "upcoming":
                continue

            # Bot ilk açıldığında mevcut içerikleri hafızaya al ve geç
            if is_initial_check:
                seen_video_ids.add(video_id)
                continue

            # Bitmiş canlı yayın tekrarıysa (VOD) atla
            if "actualEndTime" in live_details:
                seen_video_ids.add(video_id)
                continue

            # Tarih kontrolü: 2 saatten eski hiçbir içeriği paylaşma
            time_str = live_details.get("actualStartTime") if live_status == "live" else snippet.get("publishedAt")
            if time_str:
                content_time = parse_yt_time(time_str)
                if (now_utc - content_time) > timedelta(hours=2):
                    seen_video_ids.add(video_id)
                    print(f"Eski içerik engellendi ({time_str}): {video_id}", flush=True)
                    continue

            # Shorts kontrolü
            shorts_check_url = f"https://www.youtube.com/shorts/{video_id}"
            shorts_res = requests.head(shorts_check_url, allow_redirects=False)
            if shorts_res.status_code == 200:
                seen_video_ids.add(video_id)
                print(f"Shorts atlandı: {video_id}", flush=True)
                continue

            # Bildirimi gönder
            target_channel = bot.get_channel(DISCORD_CHANNEL_ID)
            if target_channel:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                if live_status == "live":
                    await target_channel.send(f"🔴 **YOUTUBE'DA CANLI YAYIN BAŞLADI!**\n{video_url}\n<@&{YOUTUBE_ROLE_ID}>")
                else:
                    await target_channel.send(f"🎬 **YENİ VİDEO YAYINDA!**\n{video_url}\n<@&{YOUTUBE_ROLE_ID}>")

            seen_video_ids.add(video_id)

        is_initial_check = False
    except Exception as e:
        print(f"Hata: {e}", flush=True)

bot.run(BOT_TOKEN)