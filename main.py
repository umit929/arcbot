import os
import sys
import asyncio
import discord
from discord.ext import tasks, commands
import requests
from aiohttp import web

# Print çıktılarını konsola anında basmaya zorluyoruz
sys.stdout.reconfigure(line_buffering=True)

# --- BOT AYARLARI ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
YOUTUBE_CHANNEL_ID = 'UCRlsFZE_4iXGyi2Dhxcduhg'
KICK_USERNAME = 'arctune12'
DISCORD_CHANNEL_ID = 1551892041737183332

intents = discord.Intents.default()
intents.message_content = True

last_video_id = None
is_kick_live = False

# --- WEBHOOK VE WEB SUNUCUSU (AIOHTTP) ---
async def handle_ping(request):
    return web.Response(text="ArcBot 7/24 Aktif!")

async def handle_kick_webhook(request):
    global is_kick_live
    try:
        data = await request.json()
        print(f"[WEBHOOK] Kick bildirimi alındı: {data}", flush=True)
        
        is_live = data.get("is_live", False)
        stream_title = data.get("title", f"{KICK_USERNAME} Kick Canlı Yayını")
        
        if is_live and not is_kick_live:
            is_kick_live = True
            target_channel = bot.get_channel(DISCORD_CHANNEL_ID)
            if target_channel:
                kick_url = f"https://kick.com/{KICK_USERNAME}"
                await target_channel.send(
                    f"🟢 **KICK'TE CANLI YAYIN BAŞLADI!**\n"
                    f"**Başlık:** {stream_title}\n"
                    f"Aramıza katılın: {kick_url}"
                )
                print("[WEBHOOK] 🎉 Discord kanalına bildirim gönderildi!", flush=True)
        elif not is_live:
            is_kick_live = False
            
        return web.Response(text="OK", status=200)
    except Exception as e:
        print(f"[WEBHOOK HATA] {e}", flush=True)
        return web.Response(text="Error", status=400)

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_post('/kick-webhook', handle_kick_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"[WEB SERVER] {port} portunda Webhook dinleyici aktif!", flush=True)

# --- CUSTOM BOT CLASS ---
class ArcBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.loop.create_task(start_web_server())
        
        if not check_youtube.is_running():
            check_youtube.start()
            print("[SİSTEM] YouTube kontrol döngüsü başlatıldı.", flush=True)

bot = ArcBot()

# --- YOUTUBE KONTROLÜ ---
@tasks.loop(minutes=5)
async def check_youtube():
    global last_video_id
    print("[YOUTUBE CHECK] YouTube kontrol ediliyor...", flush=True)
    if not YOUTUBE_API_KEY:
        print("[YOUTUBE CHECK] HATA: YouTube API Key bulunamadı!", flush=True)
        return

    url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={YOUTUBE_CHANNEL_ID}&part=snippet,id&order=date&maxResults=5"
    
    try:
        response = requests.get(url).json()
        if "items" in response:
            for item in response["items"]:
                video_id = item["id"].get("videoId")
                if not video_id:
                    continue
                
                shorts_check_url = f"https://www.youtube.com/shorts/{video_id}"
                shorts_res = requests.head(shorts_check_url, allow_redirects=False)
                
                if shorts_res.status_code == 200:
                    continue
                
                if video_id != last_video_id:
                    if last_video_id is None:
                        last_video_id = video_id
                        break
                    
                    last_video_id = video_id
                    target_channel = bot.get_channel(DISCORD_CHANNEL_ID)
                    
                    if target_channel:
                        live_broadcast = item["snippet"].get("liveBroadcastContent")
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        if live_broadcast == "live":
                            await target_channel.send(f"🔴 **YOUTUBE'DA CANLI YAYIN BAŞLADI!**\nYayın açıldı, kaçırmayın!\n{video_url}")
                        else:
                            await target_channel.send(f"🎬 **YENİ YOUTUBE VİDEOSU YAYINDA!**\nYeni video geldi, iyi seyirler!\n{video_url}")
                    break
    except Exception as e:
        print(f"[YOUTUBE CHECK] Hata: {e}", flush=True)

@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} başarıyla aktif oldu!', flush=True)

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! 🏓 ArcBot çalışıyor.')

@bot.command()
async def kicktest(ctx):
    global is_kick_live
    is_kick_live = False
    await ctx.send('🔄 Kick durum kontrolü sıfırlandı.')

bot.run(BOT_TOKEN)