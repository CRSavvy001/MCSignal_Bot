# MC Signal Bot

Watches a Telegram group/channel for signal messages, extracts the `Cap:` (marketcap) and coin-age values, and forwards any message where marketcap ≤ threshold (default **$10,000**) **and** the coin was created ≤ threshold minutes ago (default **10 minutes**) to another chat you own.

## How it works

- `main.py` runs a long-polling Telegram bot.
- Every incoming message in `SOURCE_CHAT_ID` is checked with a regex that looks for `Cap:`, `MC:`, or `Market Cap:` followed by a dollar amount (handles K/M/B suffixes, e.g. `$8.4K` → `8400`).
- The same message is also checked for the age token that follows the `ATH:` value (e.g. `ATH: $217.1K · 18m ·`, `ATH: $9.7K · 18s ·`). This handles seconds, minutes, hours, days, and weeks (`s`, `m`, `h`, `d`, `w` and their long forms), so coins launched moments ago (`18s`) are correctly treated as newer than ones launched `18m` ago.
- A message is only forwarded if **both** conditions hold:
  - `marketcap <= MC_THRESHOLD`
  - `age_in_minutes <= AGE_THRESHOLD_MINUTES`
- If either the marketcap or the age token can't be found/parsed, the message is skipped (and logged) rather than forwarded — better to miss one than forward something we couldn't actually verify.
- If it passes, the bot rebuilds the message as plain text:
  - The `Socials:` line is rewritten with each link on its own line, with a blank line between entries, e.g.:
    ```
    Socials:

    Web (https://example.com)

    X (https://x.com/example)

    TG (https://t.me/example)
    ```
    This works whether the link is a hidden label (like "Web" secretly pointing somewhere) or a link whose visible text is already the raw URL.
  - Every other hyperlink in the message (wallet/holder explorer links, chart links like DexScreener/GMGN, hashtag links, etc.) is stripped down to its plain visible text with the underlying URL dropped — those aren't needed downstream and would otherwise clutter the message.
- This is a re-sent message, not a native Telegram "Forwarded from" message, since Telegram doesn't allow editing a message's content while forwarding it.

## 1. Create your bot

- Message [@BotFather](https://t.me/BotFather) on Telegram.
- `/newbot` → follow the prompts → copy the token it gives you.
- `/setprivacy` → select your bot → **Disable**. (Required so the bot can read every message in the group, not just commands.)

## 2. Add the bot to both chats

- **Source chat** (the signal group): add the bot as a member. If it's a channel rather than a group, add it as **admin** so it can read posts.
- **Destination chat** (where filtered signals go): add the bot as **admin** with "Post Messages" permission.

## 3. Get the chat IDs

Forward any message from each chat to [@userinfobot](https://t.me/userinfobot) or [@RawDataBot](https://t.me/RawDataBot) — it'll reply with the chat ID (looks like `-1001234567890`).

## 4. Configure environment variables

Copy `.env.example` to `.env` for local testing, or set these directly as environment variables in Railway:

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Token from BotFather |
| `SOURCE_CHAT_ID` | Chat ID of the group to watch |
| `DEST_CHAT_ID` | Chat ID to forward matching signals to |
| `MC_THRESHOLD` | Optional. Max marketcap to forward. Default `10000` |
| `AGE_THRESHOLD_MINUTES` | Optional. Max coin age (in minutes) to forward. Default `10` |

## 5. Run locally (optional, to test first)

```bash
pip install -r requirements.txt
export BOT_TOKEN=...
export SOURCE_CHAT_ID=...
export DEST_CHAT_ID=...
python main.py
```

## 6. Deploy on Railway

- Push this folder to a GitHub repo.
- On railway.com, **New Project** → **Deploy from GitHub repo**, select the repo.
- Railway will detect `requirements.txt` and the `Procfile` automatically and run it as a worker process (no public URL needed — this bot uses polling, not webhooks).
- In the Railway project, go to **Variables** and add `BOT_TOKEN`, `SOURCE_CHAT_ID`, `DEST_CHAT_ID`, and optionally `MC_THRESHOLD` and `AGE_THRESHOLD_MINUTES`.
- Deploy. Check the **Logs** tab — you should see `Bot starting. Watching chat ... for Cap <= 10000 and age <= 10m, forwarding to ...`.

## Notes / things to double check

- If the source is a channel and the bot doesn't see any messages, it almost certainly needs to be added as admin there, not just a member — channels don't broadcast to regular bot members even with privacy mode disabled.
- If message formats vary (e.g. some say `MC:` instead of `Cap:`), the regex in `main.py` already tries both — extend `CAP_PATTERN` if you spot a new format that's being missed. Check the Railway logs for `"No marketcap found"` entries to catch these.
- Similarly, if a message's age token uses a format not yet covered, extend `AGE_PATTERN`/`AGE_UNIT_MINUTES` — check the logs for `"No coin age found"` entries.
- This bot doesn't validate or vet the signals themselves — it's purely a filter on the stated marketcap and age numbers. Sub-$10K marketcap, sub-10-minute-old tokens carry real, well-known risks (rugs, thin liquidity); this tool just gets the raw signal to you faster.
