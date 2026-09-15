import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
import yt_dlp

# Dummy web server to satisfy Koyeb port 8000 health check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check_server():
    server = HTTPServer(('0.0.0.0', 8000), HealthCheckHandler)
    server.serve_forever()

# Start health check server on a background thread
threading.Thread(target=run_health_check_server, daemon=True).start()

# ... rest of your main.py code below ...

# Enable gateway intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=".", intents=intents)

WELCOME_CHANNEL_ID = 1549272703750377472

# yt-dlp configuration
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

def get_ordinal(n: int) -> str:
    formatted_num = f"{n:02d}"
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{formatted_num}{suffix}"

@bot.event
async def on_ready():
    print(f"⚡ Bot is online as {bot.user.name}")

@bot.event
async def on_member_join(member: discord.Member):
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return

    member_count = member.guild.member_count
    ordinal_count = get_ordinal(member_count)

    embed = discord.Embed(
        title=f"👋 Welcome to {member.guild.name}!",
        description=(
            f"Hey {member.mention}, welcome to the network!\n\n"
            f"🎉 You are our **{ordinal_count}** member!\n\n"
            f"└ Make sure to check out the server channels and grab your roles."
        ),
        color=discord.Color.from_rgb(0, 240, 255)
    )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    if member.guild.icon:
        embed.set_footer(text="RedHat' SMP System", icon_url=member.guild.icon.url)
    else:
        embed.set_footer(text="RedHat' SMP System")

    await channel.send(content=f"Welcome {member.mention}!", embed=embed)

# ----------------- MUSIC COMMANDS ----------------- #

@bot.command(name="play")
async def play(ctx, url: str):
    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a Voice Channel to use this command!")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    async with ctx.typing():
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        
        if 'entries' in data:
            data = data['entries'][0]

        stream_url = data['url']
        title = data.get('title', 'Audio Track')

        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(source, after=lambda e: print(f'Finished playing: {e}') if e else None)

    await ctx.send(f"🎵 Now playing: **{title}**")

@bot.command(name="leave")
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Disconnected from voice channel.")
    else:
        await ctx.send("❌ I am not connected to a voice channel.")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
