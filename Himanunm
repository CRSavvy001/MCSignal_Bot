import os
import re
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
SOURCE_CHAT_ID = int(os.environ["SOURCE_CHAT_ID"])
DEST_CHAT_ID = int(os.environ["DEST_CHAT_ID"])
MC_THRESHOLD = float(os.environ.get("MC_THRESHOLD", "15000"))

# Matches things like "Cap: $8.4K", "Cap: $850", "MC: $1.2M"
CAP_PATTERN = re.compile(
    r"(?:Cap|MC|Market\s*Cap)\s*:\s*\$?([\d,.]+)\s*([KMB]?)",
    re.IGNORECASE,
)

MULTIPLIERS = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


def extract_marketcap(text: str) -> float | None:
    """Pulls the first Cap/MC value out of a signal message and returns it as a number."""
    if not text:
        return None
    match = CAP_PATTERN.search(text)
    if not match:
        return None
    number_str, suffix = match.groups()
    try:
        number = float(number_str.replace(",", ""))
    except ValueError:
        return None
    return number * MULTIPLIERS.get(suffix.upper(), 1)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or message.chat_id != SOURCE_CHAT_ID:
        return

    text = message.text or message.caption
    marketcap = extract_marketcap(text)

    if marketcap is None:
        logger.info("No marketcap found in message %s, skipping.", message.message_id)
        return

    logger.info("Message %s has marketcap %.2f", message.message_id, marketcap)

    if marketcap <= MC_THRESHOLD:
        await context.bot.forward_message(
            chat_id=DEST_CHAT_ID,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=message.message_id,
        )
        logger.info(
            "Forwarded message %s (MC=%.2f <= %.2f)",
            message.message_id,
            marketcap,
            MC_THRESHOLD,
        )


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    logger.info(
        "Bot starting. Watching chat %s for Cap <= %.0f, forwarding to %s",
        SOURCE_CHAT_ID,
        MC_THRESHOLD,
        DEST_CHAT_ID,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
