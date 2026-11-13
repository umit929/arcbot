import os
import sys
import discord
from discord.ext import tasks, commands
import requests
from aiohttp import web

sys.stdout.reconfigure(line_buffering=True)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
YOUTUBE_CHANNEL_ID = 'UCRlsFZE_4iXGyi2Dhxcduhg'
DISCORD_CHANNEL_ID = 1551892041737183332
YOUTUBE_ROLE_ID = "1554137072003190794"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
seen_video_ids = set()
is_initial_check = True

# Render uyku moduna geçmesin diye sahte web sunucusu (7/24 aktif kalmasını sağlar)
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

# 15 dakika yaptık ki günlük API kotan asla dolmasın
@tasks.loop(minutes=15)
async def check_youtube():
    global seen_video_ids, is_initial_check
    if not YOUTUBE_API_KEY:
        return

    url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={YOUTUBE_CHANNEL_ID}&part=snippet,id&order=date&maxResults=3"
    
    try:
        response = requests.get(url).json()
        if "items" not in response:
            return

        for item in response["items"]:
            video_id = item["id"].get("videoId")
            if not video_id:
                continue
            
            # BÜYÜK BUG ÇÖZÜMÜ: Bot ilk açıldığında videoları sadece hafızaya alır, mesaj atmaz
            if is_initial_check:
                seen_video_ids.add(video_id)
                continue

            if video_id in seen_video_ids:
                continue
                
            # Kendi yazdığın o harika Shorts engelleme kontrolü
            shorts_check_url = f"https://www.youtube.com/shorts/{video_id}"
            shorts_res = requests.head(shorts_check_url, allow_redirects=False)
            if shorts_res.status_code == 200:
                seen_video_ids.add(video_id)
                print(f"Shorts atlandı: {video_id}", flush=True)
                continue

            # Normal video veya Canlı Yayın geldiğinde çalışacak kısım
            target_channel = bot.get_channel(DISCORD_CHANNEL_ID)
            if target_channel:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                live_broadcast = item["snippet"].get("liveBroadcastContent")
                
                if live_broadcast == "live":
                    await target_channel.send(f"🔴 **YOUTUBE'DA CANLI YAYIN BAŞLADI!**\n{video_url}\n<@&{YOUTUBE_ROLE_ID}>")
                else:
                    await target_channel.send(f"🎬 **YENİ VİDEO YAYINDA!**\n{video_url}\n<@&{YOUTUBE_ROLE_ID}>")
                
            seen_video_ids.add(video_id)
            
        is_initial_check = False
    except Exception as e:
        print(f"Hata: {e}", flush=True)

bot.run(BOT_TOKEN)