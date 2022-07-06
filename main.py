import base64
import datetime
import logging
import os

import dotenv
import httpx
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

dotenv.load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DEEP_AI_API_KEY = os.getenv("DEEP_AI_API_KEY")
CRAIYON_ENDPOINT = "https://backend.craiyon.com/generate"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hi. This command does NOTHING.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Somebody please HELP ME!")


async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        text = "Command needs a prompt."
        await update.message.reply_text(text=text)
        return

    command_text = " ".join(context.args)

    print(update.message.chat.full_name)
    print(update.message.from_user.full_name)
    print(command_text)

    text = f'Generating:\n"{command_text}"\nPlease wait...'

    if "requests" not in context.bot_data:
        context.bot_data["requests"] = []
    context.bot_data["requests"].append(datetime.datetime.now())

    all_requests: list[datetime.datetime] = context.bot_data["requests"]

    last_1min = len(
        [
            dt
            for dt in all_requests
            if dt > datetime.datetime.now() - datetime.timedelta(minutes=1)
        ]
    )
    last_5min = len(
        [
            dt
            for dt in all_requests
            if dt > datetime.datetime.now() - datetime.timedelta(minutes=5)
        ]
    )
    last_10min = len(
        [
            dt
            for dt in all_requests
            if dt > datetime.datetime.now() - datetime.timedelta(minutes=10)
        ]
    )
    last_30min = len(
        [
            dt
            for dt in all_requests
            if dt > datetime.datetime.now() - datetime.timedelta(minutes=30)
        ]
    )

    text += f"\n\nAmmount of requests in the past:\n1min: {last_1min}\n5min: {last_5min}\n10min: {last_10min}\n30min: {last_30min}"

    await update.message.reply_text(text=text)

    try:
        images = await generate_images(command_text)
    except Exception as error:
        text = "Error happened. I'm very sorry."
        await update.message.reply_text(text=text)
        logger.error(error)
        return

    media_photos = []
    for img_str in images:
        decoded_image_bytes = await decode_image_as_bytes(img_str)
        media_photo = telegram.InputMediaPhoto(media=decoded_image_bytes)
        media_photos.append(media_photo)

    retry = True
    i = 1

    while retry:
        try:
    await update.message.reply_media_group(media=media_photos)
            retry = False
        except Exception:
            seconds = random.randint(30, 60)
            print(f"{command_text} - Timeout happened, retrying in {seconds}s... ({i} attempt)")
            i += 1
            await asyncio.sleep(seconds)


async def generate_images(prompt: str) -> list[str]:
    data = {"prompt": prompt}

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(url=CRAIYON_ENDPOINT, json=data, timeout=None)
            response_json = response.json()
    except Exception as error:
        raise error

    return response_json["images"]


async def decode_image_as_bytes(base64_str: str):
    return base64.decodebytes(bytes(base64_str, "utf-8"))

async def waifu2x(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message.reply_to_message is None:
        text = "Reply to an image, pelase."
        await update.message.reply_text(text=text)
        return
    if update.effective_message.reply_to_message.photo is None:
        text = "Reply to an image, pelase."
        await update.message.reply_text(text=text)
        return

    photo_file_id = update.effective_message.reply_to_message.photo[-1].file_id
    file_url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={photo_file_id}"

    
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.get(url=file_url)
            response_json = response.json()
    except Exception as error:
        raise error

    file_download_url = f"https://api.telegram.org/file/bot{TOKEN}/{response_json['result']['file_path']}"

    print(file_url)
    print(response_json)
    print(file_download_url)



    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                "https://api.deepai.org/api/waifu2x",
                data={
                    "image": file_download_url,
                },
                headers={"api-key": DEEP_AI_API_KEY},
                timeout=None,
            )
            response_json = response.json()
    except Exception as error:
        raise error

    upscaled_url = response.json()["output_url"]
    print(upscaled_url)

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.get(upscaled_url, timeout=None)
            
    except Exception as error:
        raise error
    

    response_bytes = await response.aread()

    media_photos = []
    media_photo = telegram.InputMediaPhoto(media=response_bytes)
    media_photos.append(media_photo)

    await update.message.reply_media_group(media=media_photos)




def main() -> None:
    application = (
        Application.builder()
        .token(TOKEN)
        .concurrent_updates(True)
        .connection_pool_size(1024)
        .write_timeout(None)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("generate", generate, block=False))
    application.add_handler(CommandHandler("waifu2x", waifu2x, block=False))

    application.run_polling()


if __name__ == "__main__":
    main()
