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
MC_THRESHOLD = float(os.environ.get("MC_THRESHOLD", "10000"))
AGE_THRESHOLD_MINUTES = float(os.environ.get("AGE_THRESHOLD_MINUTES", "10"))

# Matches things like "Cap: $8.4K", "Cap: $850", "MC: $1.2M"
CAP_PATTERN = re.compile(
    r"(?:Cap|MC|Market\s*Cap)\s*:\s*\$?([\d,.]+)\s*([KMB]?)",
    re.IGNORECASE,
)

MULTIPLIERS = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

# Matches the age token that follows the ATH value, e.g.
# "ATH: $217.1K · 18m ·", "ATH: $9.7K · 18s ·", "ATH: $1.2M · 2h ·", "ATH: $500 · 3d ·"
AGE_PATTERN = re.compile(
    r"ATH\s*:\s*\$?[\d,.]+\s*[KMB]?\s*[·\-|]\s*([\d.]+)\s*(s|sec|secs|second|seconds|"
    r"m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|week|weeks)\b",
    re.IGNORECASE,
)

# Age unit -> minutes multiplier
AGE_UNIT_MINUTES = {
    "s": 1 / 60, "sec": 1 / 60, "secs": 1 / 60, "second": 1 / 60, "seconds": 1 / 60,
    "m": 1, "min": 1, "mins": 1, "minute": 1, "minutes": 1,
    "h": 60, "hr": 60, "hrs": 60, "hour": 60, "hours": 60,
    "d": 1440, "day": 1440, "days": 1440,
    "w": 10080, "week": 10080, "weeks": 10080,
}


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


def extract_age_minutes(text: str) -> float | None:
    """Pulls the coin-age token that follows 'ATH: $X ·' (e.g. '18m', '18s', '2h')
    and returns the age in minutes. Handles sub-minute ages ('18s' -> 0.3 minutes)
    as well as larger units."""
    if not text:
        return None
    match = AGE_PATTERN.search(text)
    if not match:
        return None
    number_str, unit = match.groups()
    try:
        number = float(number_str)
    except ValueError:
        return None
    multiplier = AGE_UNIT_MINUTES.get(unit.lower())
    if multiplier is None:
        return None
    return number * multiplier


LINK_PATTERN = re.compile(r'<a href="([^"]+)">(.*?)</a>', re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")


SOCIAL_ENTRY_PATTERN = re.compile(
    r'(?:([A-Za-z]+)\s*\()?<a href="([^"]+)">(.*?)</a>', re.DOTALL
)


def strip_links_keep_text(html_text: str) -> str:
    """Removes hyperlinks but keeps their visible text, for lines we don't want
    exposing raw URLs for (wallet addresses, chart links, hashtag links, etc.)."""
    text = LINK_PATTERN.sub(lambda m: m.group(2), html_text)
    text = TAG_PATTERN.sub("", text)
    return unescape(text)


def format_socials_line(html_line: str) -> str:
    """Rebuilds the 'Socials:' line as 'Socials:' followed by each link on its
    own line, with a blank line between entries, e.g.:

        Socials:

        Web (https://example.com)

        X (https://x.com/example)

        TG (https://t.me/example)

    Handles both hidden-label links (anchor text is 'Web'/'X'/'TG') and links
    where the visible anchor text is already the raw URL (avoids the URL being
    duplicated as 'url (url)' in that case).
    """
    entries = []
    for label_word, url, anchor_text in SOCIAL_ENTRY_PATTERN.findall(html_line):
        anchor_text = unescape(TAG_PATTERN.sub("", anchor_text)).strip()
        if label_word:
            label = label_word.strip()
        elif anchor_text and anchor_text != url:
            label = anchor_text
        else:
            label = None
        entries.append(f"{label} ({url})" if label else url)

    if not entries:
        return strip_links_keep_text(html_line)
    return "Socials:\n\n" + "\n\n".join(entries)


def build_outgoing_text(message) -> str:
    """Builds the text to send onward. Only the 'Socials:' line has its hidden
    links exposed as visible, spaced-out '(url)' entries; every other link
    (wallet explorer addresses, chart links, hashtag links, etc.) is stripped
    down to plain text with no URL, since those aren't needed downstream."""
    html_source = message.text_html_urled or message.caption_html_urled
    if not html_source:
        return message.text or message.caption or ""

    out_lines = []
    for line in html_source.split("\n"):
        if "social" in line.lower():
            out_lines.append(format_socials_line(line))
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

    age_minutes = extract_age_minutes(text)

    if age_minutes is None:
        logger.info("No coin age found in message %s, skipping.", message.message_id)
        return

    logger.info(
        "Message %s has marketcap %.2f and age %.2f minutes",
        message.message_id,
        marketcap,
        age_minutes,
    )

    if marketcap <= MC_THRESHOLD and age_minutes <= AGE_THRESHOLD_MINUTES:
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
            "Sent message %s with links exposed (MC=%.2f <= %.2f, age=%.2fm <= %.2fm)",
            message.message_id,
            marketcap,
            MC_THRESHOLD,
            age_minutes,
            AGE_THRESHOLD_MINUTES,
        )


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    logger.info(
        "Bot starting. Watching chat %s for Cap <= %.0f and age <= %.0fm, forwarding to %s",
        SOURCE_CHAT_ID,
        MC_THRESHOLD,
        AGE_THRESHOLD_MINUTES,
        DEST_CHAT_ID,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
