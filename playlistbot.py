import os
from pyrogram import Client, filters
from yt_dlp import YoutubeDL
from pathlib import Path
import asyncio

API_ID = 18100193
API_HASH = "a27360d3fcef230d33af8e8c4c4c7de6"
BOT_TOKEN = "7808004159:AAFmPUIWjzxmK1kHad3Yp9Mw9VbAZB5jpJk"

app = Client("playlist_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "%(title)s.%(ext)s",
    "quiet": True,
    "noplaylist": False,
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}

@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text("🎵 Send a YouTube playlist link and I’ll send the songs in the group.")

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_playlist(_, message):
    url = message.text.strip()
    status = await message.reply_text("🔍 Checking playlist...")

    if "list=" not in url:
        await status.edit("❌ Please send a valid YouTube playlist link.")
        return

    try:
        with YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(url, download=False)
            entries = playlist_info.get("entries", [])

            if not entries:
                await status.edit("❌ No songs found.")
                return

            await status.edit(f"📜 Found {len(entries)} songs. Sending...")

            for index, entry in enumerate(entries, start=1):
                try:
                    info = ydl.extract_info(entry['webpage_url'], download=True)
                    file_path = ydl.prepare_filename(info)
                    mp3_file = Path(file_path).with_suffix(".mp3")

                    if mp3_file.exists():
                        await message.reply_audio(
                            audio=str(mp3_file),
                            title=info.get("title"),
                            performer=info.get("uploader"),
                            caption=f"🎶 {info.get('title')}"
                        )
                        mp3_file.unlink()
                        await asyncio.sleep(1.5)
                    else:
                        await message.reply_text(f"⚠️ File not found for: {info.get('title')}")
                except Exception as e:
                    await message.reply_text(f"❌ Error on song #{index}: `{e}`")

            await status.edit("✅ All done!")
    except Exception as e:
        await status.edit(f"❌ Playlist error:\n`{e}`")

app.run()
