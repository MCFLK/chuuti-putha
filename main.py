import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
import aiohttp

# --- Health Check Server (for Koyeb) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check_server():
    port = int(os.getenv("PORT", 8000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# --- Bot Setup ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=".", intents=intents)

WELCOME_CHANNEL_ID = 1549272703750377472

# ⚠️ REPLACE THIS with your own self-hosted Cobalt URL
COBALT_API_URL = "https://your-cobalt-instance.onrender.com"

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

processing_lock = asyncio.Lock()

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
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Usage: `.play <YouTube URL>`")
    else:
        await ctx.send(f"❌ An error occurred: `{str(error)}`")
        print(f"Command error: {error}")

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

# --- Music Commands ---

async def get_audio_stream_from_cobalt(video_url: str) -> str:
    """Send a request to the self-hosted Cobalt API to get a streamable audio URL."""
    payload = {
        "url": video_url,
        "downloadMode": "audio",
        "audioFormat": "mp3",
        "audioBitrate": "128"
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{COBALT_API_URL}/", json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Cobalt API responded with status {resp.status}: {error_text}")
            data = await resp.json()
            
            if data.get("status") in ("redirect", "tunnel"):
                return data["url"]
            else:
                error_msg = data.get("error", {}).get("code", "Unknown error")
                raise Exception(f"Cobalt error: {error_msg}")

@bot.command(name="play")
async def play(ctx, *, query: str):
    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a Voice Channel to use this command!")
        return

    voice_channel = ctx.author.voice.channel

    try:
        if ctx.voice_client is None:
            await voice_channel.connect(timeout=60.0, reconnect=True)
        elif ctx.voice_client.channel != voice_channel:
            await ctx.voice_client.move_to(voice_channel)
    except asyncio.TimeoutError:
        await ctx.send("❌ Failed to connect to voice. This is a UDP network issue with the hosting provider.")
        return

    async with ctx.typing():
        async with processing_lock:
            try:
                if not query.startswith("http"):
                    await ctx.send("⚠️ Please provide a direct YouTube URL. Searching by text is not supported.")
                    return
                
                video_url = query
                stream_url = await get_audio_stream_from_cobalt(video_url)

                if ctx.voice_client.is_playing():
                    ctx.voice_client.stop()

                source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
                ctx.voice_client.play(
                    source,
                    after=lambda e: print(f'Finished playing: {e}') if e else None
                )

                await ctx.send(f"🎵 Now playing: **{video_url}**")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: `{str(e)}`")
                print(f"Error in play command: {e}")

@bot.command(name="leave")
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Disconnected.")
    else:
        await ctx.send("❌ I am not connected to a voice channel.")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ ERROR: DISCORD_TOKEN environment variable is missing!")
else:
    bot.run(TOKEN)
