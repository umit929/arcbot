import os
import discord
from discord.ext import tasks, commands
import requests
from flask import Flask
from threading import Thread

# --- RENDER KAPANMA ENGELLEYİCİ (WEB SUNUCUSU) ---
app = Flask('')

@app.route('/')
def home():
    return "ArcBot 7/24 Aktif!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT AYARLARI ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
YOUTUBE_API_KEY = 'AIzaSyAeasnXLf9w2h2_GlEfI8P_Tyfc479nKTI'
YOUTUBE_CHANNEL_ID = 'UCRlsFZE_4iXGyi2Dhxcduhg'
KICK_USERNAME = 'arctune12'
DISCORD_CHANNEL_ID = 1551892041737183332

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

last_video_id = None
is_kick_live = False

# --- YOUTUBE KONTROLÜ (Shorts Engellemeli) ---
@tasks.loop(minutes=5)
async def check_youtube():
    global last_video_id
    url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={YOUTUBE_CHANNEL_ID}&part=snippet,id&order=date&maxResults=5"
    
    try:
        response = requests.get(url).json()
        if "items" in response:
            for item in response["items"]:
                video_id = item["id"].get("videoId")
                if not video_id:
                    continue
                
                # Shorts Kontrolü
                shorts_check_url = f"https://www.youtube.com/shorts/{video_id}"
                shorts_res = requests.head(shorts_check_url, allow_redirects=False)
                
                if shorts_res.status_code == 200:
                    continue  # Shorts ise atla
                
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
        print(f"YouTube kontrol hatası: {e}")

# --- KICK KONTROLÜ ---
@tasks.loop(minutes=3)
async def check_kick():
    global is_kick_live
    url = f"https://kick.com/api/v1/channels/{KICK_USERNAME}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            livestream = data.get("livestream")
            
            if livestream is not None and not is_kick_live:
                is_kick_live = True
                target_channel = bot.get_channel(DISCORD_CHANNEL_ID)
                
                if target_channel:
                    stream_title = livestream.get("session_title", "Kick Canlı Yayını")
                    category = livestream.get("categories", [{}])[0].get("name", "Genel")
                    kick_url = f"https://kick.com/{KICK_USERNAME}"
                    
                    await target_channel.send(
                        f"🟢 **KICK'TE CANLI YAYIN BAŞLADI!**\n"
                        f"**Başlık:** {stream_title}\n"
                        f"**Kategori:** {category}\n"
                        f"Aramıza katılın: {kick_url}"
                    )
            elif livestream is None:
                is_kick_live = False
    except Exception as e:
        print(f"Kick kontrol hatası: {e}")

@bot.event
async def on_ready():
    print(f'{bot.user.name} başarıyla aktif oldu!')
    check_youtube.start()
    check_kick.start()

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! 🏓 ArcBot çalışıyor.')

# Web sunucusunu başlatıp ardından botu çalıştırıyoruz
keep_alive()
bot.run(BOT_TOKEN)