# G.H.O.S.T. - Discord Remote Access Tool (Educational / PoC)

**G.H.O.S.T.** (Ghost Hidden Operator Stealth Tool) is a proof-of-concept Discord bot that provides remote access and control over a Windows machine via Discord messages.

**DISCLAIMER**  
This tool is intended **ONLY for educational purposes, security research, and authorized testing** on systems you own or have explicit written permission to access.  
Unauthorized use on any system is illegal in most jurisdictions (e.g., unauthorized access, computer fraud, privacy violations).  
The author is not responsible for any misuse, damage, or legal consequences resulting from this code.

## Features

- Loads Discord bot token from `.env` (no hard-coded token)
- Creates a private control channel named `control-<your-public-ip>`
- Executes arbitrary **PowerShell commands** directly in the control channel (no prefix needed)
- Downloads files from Discord messages to the target PC (`!load [optional_folder]`)
- Uploads files from the target PC to Discord (`!download <path>`)
- Captures and uploads screenshots (`!screenshot`)
- Non-blocking command execution with **timeout** to prevent freezing
- Stealth-oriented (no console window when built as executable)

## Requirements

- Windows (tested on Windows 10/11)
- Python 3.10+
- Internet connection

Install dependencies:

```bash
pip install -r requirements.txt
```


## Installation

1) Clone or download the project files

```bash
git clone https://github.com/MattiaAlessi/DS_RAT_GHOST.git

#copy and add your credentials
cp .env.example .env
```

N.B. Get your token from: https://discord.com/developers/applications

2) Run the bot:

```bash
python main.py
```


## Available Commands
  In any channel:

- !commands → Show command list
- !screenshot → Capture and upload desktop screenshot
- !load [folder] → Save attachments from the message to the PC
- !download <path> → Upload file from PC to Discord

In the control channel (control-xxx.xxx.xxx.xxx):

- Any valid PowerShell command directly (no prefix needed)
  Examples:
- whoami
- Get-Process
- dir
- Start-Sleep -s 10


Persistence
The script runs only while active.
Persistence (auto-start on boot/login) is not included by default.
Common methods to add it manually:

Copy the script/exe to Startup folder
Add to Registry (HKCU\Software\Microsoft\Windows\CurrentVersion\Run)
Create a scheduled task (schtasks)

Security & Legal Notes

Use responsibly — only on systems you own or have clear authorization for
Always test in a clean virtual machine first

License
For educational and research purposes only.
No license granted for malicious or unauthorized use.
Use at your own risk.
