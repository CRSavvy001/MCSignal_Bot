import os
import re
import logging
from html import unescape
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


LINK_PATTERN = re.compile(r'<a href="([^"]+)">(.*?)</a>', re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")


def linkify_plaintext(html_text: str) -> str:
    """Turns Telegram's HTML rendering of a line into plain text where every
    hidden hyperlink (e.g. 'Web' pointing to some URL) is rewritten as
    'Web (https://actual-url.com)' so the real link is visible and still clickable
    once sent as plain text (Telegram auto-links raw URLs)."""

    def repl(match: re.Match) -> str:
        url, anchor_text = match.group(1), match.group(2)
        return f"{anchor_text} ({url})"

    text = LINK_PATTERN.sub(repl, html_text)
    text = TAG_PATTERN.sub("", text)  # strip any remaining bold/italic/etc tags
    return unescape(text)


def strip_links_keep_text(html_text: str) -> str:
    """Removes hyperlinks but keeps their visible text, for lines we don't want
    exposing raw URLs for (wallet addresses, chart links, hashtag links, etc.)."""
    text = LINK_PATTERN.sub(lambda m: m.group(2), html_text)
    text = TAG_PATTERN.sub("", text)
    return unescape(text)


def build_outgoing_text(message) -> str:
    """Builds the text to send onward. Only the 'Socials:' line has its hidden
    links exposed as visible '(url)' text; every other link (wallet explorer
    addresses, chart links, hashtag links, etc.) is stripped down to plain text
    with no URL, since those aren't needed downstream."""
    html_source = message.text_html_urled or message.caption_html_urled
    if not html_source:
        return message.text or message.caption or ""

    out_lines = []
    for line in html_source.split("\n"):
        if "social" in line.lower():
            out_lines.append(linkify_plaintext(line))
        else:
            out_lines.append(strip_links_keep_text(line))
    return "\n".join(out_lines)


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
        outgoing_text = build_outgoing_text(message)

        if message.photo:
            await context.bot.send_photo(
                chat_id=DEST_CHAT_ID,
                photo=message.photo[-1].file_id,
                caption=outgoing_text[:1024] if outgoing_text else None,
            )
        else:
            await context.bot.send_message(
                chat_id=DEST_CHAT_ID,
                text=outgoing_text[:4096],
                disable_web_page_preview=True,
            )

        logger.info(
            "Sent message %s with links exposed (MC=%.2f <= %.2f)",
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
