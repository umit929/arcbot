import os
import threading
import discord
from discord.ext import tasks, commands
import requests
import cloudscraper
from flask import Flask

# --- GÜVENLİ WEBSERVER (Sadece 200 OK yanıtı döner, dosya sunmaz) ---
app = Flask(__name__)

@app.route('/')
def ping_check():
    return "ArcBot OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Sunucuyu arka planda bağımsız başlat
threading.Thread(target=run_flask, daemon=True).start()

# --- BOT AYARLARI ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
YOUTUBE_CHANNEL_ID = 'UCRlsFZE_4iXGyi2Dhxcduhg'
KICK_USERNAME = 'arctune12'
DISCORD_CHANNEL_ID = 1551892041737183332 

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

last_video_id = None
is_kick_live = False

scraper = cloudscraper.create_scraper()

# --- YOUTUBE KONTROLÜ ---
@tasks.loop(minutes=5)
async def check_youtube():
    global last_video_id
    print("[YOUTUBE CHECK] YouTube kontrol ediliyor...")
    if not YOUTUBE_API_KEY:
        print("[YOUTUBE CHECK] HATA: YouTube API Key bulunamadı!")
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
        print(f"[YOUTUBE CHECK] Hata: {e}")

# --- KICK KONTROLÜ ---
@tasks.loop(minutes=3)
async def check_kick():
    global is_kick_live
    url = f"https://kick.com/api/v1/channels/{KICK_USERNAME}"
    
    print(f"[KICK CHECK] {KICK_USERNAME} kontrol ediliyor...")
    
    try:
        response = scraper.get(url)
        print(f"[KICK CHECK] HTTP Yanıt Kodu: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            livestream = data.get("livestream")
            
            is_live_now = livestream is not None
            print(f"[KICK CHECK] Livestream Var mı?: {is_live_now} | Önceden Canlı mıydı (is_kick_live)?: {is_kick_live}")
            
            if is_live_now and not is_kick_live:
                is_kick_live = True
                target_channel = bot.get_channel(DISCORD_CHANNEL_ID)
                
                if target_channel:
                    stream_title = livestream.get("session_title", "Kick Canlı Yayını")
                    
                    category = "Genel"
                    categories = livestream.get("categories")
                    if isinstance(categories, list) and len(categories) > 0:
                        category = categories[0].get("name", "Genel")
                    elif isinstance(categories, dict):
                        category = categories.get("name", "Genel")
                        
                    kick_url = f"https://kick.com/{KICK_USERNAME}"
                    
                    await target_channel.send(
                        f"🟢 **KICK'TE CANLI YAYIN BAŞLADI!**\n"
                        f"**Başlık:** {stream_title}\n"
                        f"**Kategori:** {category}\n"
                        f"Aramıza katılın: {kick_url}"
                    )
                    print("[KICK CHECK] 🎉 Bildirim mesajı Discord kanalına başarıyla atıldı!")
                else:
                    print(f"[KICK CHECK] ❌ HATA: {DISCORD_CHANNEL_ID} ID'li Discord kanalı bulunamadı!")
            elif not is_live_now:
                is_kick_live = False
        else:
            print(f"[KICK CHECK] ❌ Kick API Hatası: Status Code {response.status_code}")
    except Exception as e:
        print(f"[KICK CHECK] ❌ İstek Hatası: {e}")

@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} başarıyla aktif oldu!')
    if not check_kick.is_running():
        check_kick.start()
        print("[SİSTEM] Kick döngüsü başlatıldı.")
    if not check_youtube.is_running():
        check_youtube.start()
        print("[SİSTEM] YouTube döngüsü başlatıldı.")

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! 🏓 ArcBot çalışıyor.')

@bot.command()
async def kicktest(ctx):
    global is_kick_live
    is_kick_live = False
    await ctx.send('🔄 Kick durum kontrolü sıfırlandı.')

bot.run(BOT_TOKEN)