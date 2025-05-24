import os
from pyrogram import Client, filters
from yt_dlp import YoutubeDL
from pathlib import Path
import asyncio

API_ID = 18100193
API_HASH = "a27360d3fcef230d33af8e8c4c4c7de6"
BOT_TOKEN = "7808004159:AAFmPUIWjzxmK1kHad3Yp9Mw9VbAZB5jpJk"

app = Client("playlist_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

base_ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "%(title)s.%(ext)s",
    "quiet": True,
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}

@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(
        "🎵 Send me a **YouTube link** (single video or playlist), and I’ll download and send the song(s) here."
    )

@app.on_message(filters.text & ~filters.command(["start"]))
async def download_music(_, message):
    url = message.text.strip()
    status = await message.reply_text("🔍 Processing...")

    if "youtube.com" not in url and "youtu.be" not in url:
        await status.edit("❌ Please send a valid YouTube link.")
        return

    # Check if it's a playlist
    is_playlist = "list=" in url

    ydl_opts = base_ydl_opts.copy()
    ydl_opts["noplaylist"] = not is_playlist  # Playlists ON if it's a playlist link

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Handle single song
            if not is_playlist or "entries" not in info:
                await status.edit("🎶 Downloading single song...")
                info = ydl.extract_info(url, download=True)
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
                else:
                    await message.reply_text("⚠️ File not found.")

            # Handle full playlist
            else:
                entries = info.get("entries", [])
                await status.edit(f"📜 Found {len(entries)} songs. Downloading...")

                for index, entry in enumerate(entries, start=1):
                    try:
                        song_info = ydl.extract_info(entry['webpage_url'], download=True)
                        file_path = ydl.prepare_filename(song_info)
                        mp3_file = Path(file_path).with_suffix(".mp3")

                        if mp3_file.exists():
                            await message.reply_audio(
                                audio=str(mp3_file),
                                title=song_info.get("title"),
                                performer=song_info.get("uploader"),
                                caption=f"🎶 {song_info.get('title')}"
                            )
                            mp3_file.unlink()
                            await asyncio.sleep(1.5)
                        else:
                            await message.reply_text(f"⚠️ File not found for: {song_info.get('title')}")
                    except Exception as e:
                        await message.reply_text(f"❌ Error in song #{index}: `{e}`")

                await status.edit("✅ Playlist complete!")

    except Exception as e:
        await status.edit(f"❌ Error:\n`{e}`")

app.run()
