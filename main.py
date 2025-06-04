import os
import time
import asyncio
import re
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from yt_dlp import YoutubeDL
from pyrogram.errors import FloodWait

API_ID = 18100193
API_HASH = "a27360d3fcef230d33af8e8c4c4c7de6"
BOT_TOKEN = "7290550046:AAE0SSr9tubBo9uL4IkzgT9O1ve39MF5dFg"

app = Client("playlist_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name)

# Store active chats
active_chats = set()

@app.on_message(filters.command("start"))
async def start(_, message):
    active_chats.add(message.chat.id)
    await message.reply_text(
        "🎶 **YouTube Playlist Downloader Bot**\n\n"
        "इस बोट की मदद से आप YouTube से गाने डाउनलोड कर सकते हैं।\n\n"
        "command का उपयोग करें:\n\n"
        "`/start` - बोट चालू करें\n"
        "`/stop` - बोट बंद करें\n\n"
        "🎵 Send me a YouTube video or playlist link or just a song name.\n\n\n"
        "I'll download audio (mp3) or video (mp4) and send it to you.\n\n\n"
        "अगर आप लिंक नहीं भेजेंगे तो मैं गाने के नाम से YouTube सर्च करके सबसे ज़्यादा व्यूज़ वाला या पहला मिलने वाला गाना डाउनलोड कर सकता हूँ।\n\n\n\n"
        "👇 गाने का नाम भेजें और फिर ऑप्शन चुनें।"
    )

@app.on_message(filters.command("stop"))
async def stop(_, message):
    active_chats.discard(message.chat.id)
    await message.reply_text("🛑 बोट इस चैट में बंद कर दिया गया है। `/start` भेजें दोबारा चालू करने के लिए।")

user_searches = {}

@app.on_message(filters.text & ~filters.command(["start", "stop"]))
async def ask_user_choice(_, message: Message):
    if message.chat.id not in active_chats:
        return  # Ignore if chat not activated

    user_input = message.text.strip()
    user_searches[message.chat.id] = user_input

    buttons = [
        [
            InlineKeyboardButton("🔝 Highest Viewed", callback_data="search_top"),
            InlineKeyboardButton("🔍 First Result", callback_data="search_first"),
        ],
        [
            InlineKeyboardButton("🎵 Ringtone", callback_data="search_ringtone"),
        ]
    ]

    await message.reply_text(
        f"आपने भेजा: **{user_input}**\n\n"
        "अब चुनें कि आपको किस तरह का रिज़ल्ट चाहिए:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query()
async def handle_choice(_, query: CallbackQuery):
    if query.message.chat.id not in active_chats:
        await query.answer("⛔️ यह चैट बंद है। पहले /start भेजें।", show_alert=True)
        return

    user_id = query.message.chat.id
    user_input = user_searches.get(user_id)

    if not user_input:
        await query.answer("❌ सर्च क्वेरी नहीं मिली। पहले कोई सॉन्ग भेजें।", show_alert=True)
        return

    await query.answer()  # remove loading state
    await query.message.edit_text("🔎 YouTube पर सर्च कर रहा हूँ, कृपया प्रतीक्षा करें...<br> कृपया 5 मिनट (min) रुकिए।")

    try:
        if user_input.startswith("http") and ("youtube.com" in user_input or "youtu.be" in user_input):
            url = user_input
            pick_best = False
        else:
            if query.data == "search_top":
                search_url = f"ytsearch10:{user_input}"
                pick_best = True
            elif query.data == "search_first":
                search_url = f"ytsearch1:{user_input}"
                pick_best = False
            elif query.data == "search_ringtone":
                search_url = f"ytsearch1:{user_input} ringtone"
                pick_best = False
            else:
                await query.message.edit_text("❌ Invalid option.")
                return

            ydl_opts_search = {"quiet": True, "skip_download": True}
            with YoutubeDL(ydl_opts_search) as ydl:
                result = ydl.extract_info(search_url, download=False)

            if "entries" not in result or not result["entries"]:
                await query.message.edit_text("❌ कोई रिज़ल्ट नहीं मिला।")
                return

            info = max(result["entries"], key=lambda e: e.get("view_count", 0)) if pick_best else result["entries"][0]
            url = info["webpage_url"]

        ydl_opts_info = {"quiet": True, "skip_download": True}
        with YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)

        title = sanitize_filename(info.get("title", "song"))
        download_dir = Path("downloads")
        download_dir.mkdir(parents=True, exist_ok=True)
        local_file = download_dir / f"{title}.mp3"

        if local_file.exists():
            try:
                await app.send_audio(
                    chat_id=query.message.chat.id,
                    audio=str(local_file),
                    title=title,
                    caption=f"🎧 Already in library: {title}"
                )
                await query.message.edit_text("✅ गाना पहले से मौजूद था, भेज दिया गया।")
            except FloodWait as e:
                await query.message.edit_text(f"⚠️ Flood wait: कृपया {e.x} सेकंड इंतजार करें।")
                await asyncio.sleep(e.x)
                # Retry sending after wait
                await app.send_audio(
                    chat_id=query.message.chat.id,
                    audio=str(local_file),
                    title=title,
                    caption=f"🎧 Already in library: {title}"
                )
                await query.message.edit_text("✅ गाना भेज दिया गया!")
            return

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(download_dir / f"{title}.%(ext)s"),
            "quiet": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        await query.message.edit_text(f"🎶 '{title}' को डाउनलोड किया जा रहा है.. <br> कृपया 5 मिनट (min) रुकिए।")

        start_time = time.time()
        with YoutubeDL(ydl_opts) as ydl:
            song_info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(song_info)
            mp3_file = Path(file_path).with_suffix(".mp3")
        duration = time.time() - start_time

        if mp3_file.exists():
            try:
                await app.send_audio(
                    chat_id=query.message.chat.id,
                    audio=str(mp3_file),
                    title=title,
                    caption=f"✅ Downloaded in {duration:.1f} sec\n\n🎧 Now Playing: {title}"
                )
                await query.message.edit_text("✅ गाना भेज दिया गया!")
            except FloodWait as e:
                await query.message.edit_text(f"⚠️ Flood wait: कृपया {e.x} सेकंड इंतजार करें।")
                await asyncio.sleep(e.x)
                await app.send_audio(
                    chat_id=query.message.chat.id,
                    audio=str(mp3_file),
                    title=title,
                    caption=f"✅ Downloaded in {duration:.1f} sec\n\n🎧 Now Playing: {title}"
                )
                await query.message.edit_text("✅ गाना भेज दिया गया!")
        else:
            await query.message.edit_text("⚠️ गाना डाउनलोड नहीं हो पाया।")

    except Exception as e:
        await query.message.edit_text(f"❌ Error: {e}")

print("🚀 Bot is running...")
app.run()
