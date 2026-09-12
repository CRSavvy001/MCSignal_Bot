# MC Signal Bot

Watches a Telegram group/channel for signal messages, extracts the `Cap:` (marketcap)
value, and forwards any message where marketcap ≤ threshold (default $15,000) to
another chat you own.

## How it works

- `main.py` runs a long-polling Telegram bot.
- Every incoming message in `SOURCE_CHAT_ID` is checked with a regex that looks for
  `Cap:`, `MC:`, or `Market Cap:` followed by a dollar amount (handles `K`/`M`/`B`
  suffixes, e.g. `$8.4K` → `8400`).
- If the marketcap is at or below `MC_THRESHOLD`, the bot rebuilds the message as
  plain text:
  - On the **`Socials:`** line only, hidden hyperlinks (e.g. the words "Web", "X",
    "TG" secretly linking somewhere) are rewritten as `Web (https://actual-url.com)`
    so the real destination is visible and still clickable.
  - Every other hyperlink in the message (wallet/holder explorer links, chart
    links like DexScreener/GMGN, hashtag links, etc.) is stripped down to its
    plain visible text with the underlying URL dropped — those aren't needed
    downstream and would otherwise clutter the message.

  This is a re-sent message, not a native Telegram "Forwarded from" message, since
  Telegram doesn't allow editing a message's content while forwarding it.

## 1. Create your bot

1. Message **@BotFather** on Telegram.
2. `/newbot` → follow the prompts → copy the token it gives you.
3. `/setprivacy` → select your bot → **Disable**. (Required so the bot can read
   every message in the group, not just commands.)

## 2. Add the bot to both chats

- **Source chat** (the signal group): add the bot as a member. If it's a **channel**
  rather than a group, add it as **admin** so it can read posts.
- **Destination chat** (where filtered signals go): add the bot as **admin** with
  "Post Messages" permission.

## 3. Get the chat IDs

Forward any message from each chat to **@userinfobot** or **@RawDataBot** — it'll
reply with the chat ID (looks like `-1001234567890`).

## 4. Configure environment variables

Copy `.env.example` to `.env` for local testing, or set these directly as
environment variables in Railway:

| Variable         | Description                                      |
|------------------|---------------------------------------------------|
| `BOT_TOKEN`      | Token from BotFather                              |
| `SOURCE_CHAT_ID` | Chat ID of the group to watch                     |
| `DEST_CHAT_ID`   | Chat ID to forward matching signals to            |
| `MC_THRESHOLD`   | Optional. Max marketcap to forward. Default 15000 |

## 5. Run locally (optional, to test first)

```bash
pip install -r requirements.txt
export BOT_TOKEN=...
export SOURCE_CHAT_ID=...
export DEST_CHAT_ID=...
python main.py
```

## 6. Deploy on Railway

1. Push this folder to a GitHub repo.
2. On [railway.com](https://railway.com), **New Project → Deploy from GitHub repo**,
   select the repo.
3. Railway will detect `requirements.txt` and the `Procfile` automatically and run
   it as a `worker` process (no public URL needed — this bot uses polling, not
   webhooks).
4. In the Railway project, go to **Variables** and add `BOT_TOKEN`, `SOURCE_CHAT_ID`,
   `DEST_CHAT_ID`, and optionally `MC_THRESHOLD`.
5. Deploy. Check the **Logs** tab — you should see
   `Bot starting. Watching chat ... for Cap <= 15000, forwarding to ...`.

## Notes / things to double check

- If the source is a **channel** and the bot doesn't see any messages, it almost
  certainly needs to be added as **admin** there, not just a member — channels
  don't broadcast to regular bot members even with privacy mode disabled.
- If message formats vary (e.g. some say `MC:` instead of `Cap:`), the regex in
  `main.py` already tries both — extend `CAP_PATTERN` if you spot a new format
  that's being missed. Check the Railway logs for "No marketcap found" entries to
  catch these.
- This bot doesn't validate or vet the signals themselves — it's purely a filter
  on the stated marketcap number. Sub-$15K marketcap tokens carry real, well-known
  risks (rugs, thin liquidity); this tool just gets the raw signal to you faster.
