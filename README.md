# SharkBonus

A private-chat educational Telegram bot with exactly three main menu features:

- **Daily Quiz:** five general knowledge questions per UTC day, with explanations.
- **Quick Challenge:** short maths questions with immediate feedback.
- **My Progress:** saved quiz and challenge scores.

All content runs inside Telegram. Scores have no monetary value. There are no purchases, prizes, external redirects, broadcasts, or alternate review modes.

## Run

Requires Python 3.11 or newer. Uses only the Python standard library; no package installation is needed.

1. Create your bot in BotFather and set a suitable original profile image there.
2. Set `BOT_TOKEN` in your hosting provider's secret environment settings. Never commit it.
3. Run `python bot.py` as a continuously running background worker.
4. Use a persistent disk and set `DATABASE_PATH` to its database location (for example `/var/data/sharkbonus.db`). Without persistent storage, progress may be lost during redeployment.
5. Run only one worker instance for each token. This bot uses long polling, not a web server; it needs no incoming port.

On every startup, the code registers the SharkBonus name, About (`setMyShortDescription`), Description (`setMyDescription`), and command menu. A valid token and successful API calls are required for these settings to appear on Telegram. A profile photo must be added separately in BotFather.

Commands: `/start`, `/help`, `/cancel`, `/privacy`, `/delete_data`.

The SQLite database stores user IDs, learning scores, quiz date, current activity, and polling offset. `/delete_data` erases a user's learning records. A subsequent interaction starts a new record. No names, usernames, or chat history are stored.

## Verify

Run `python -m unittest -v`.

Before promoting, verify the deployed bot's profile image, name, About, Description, all three buttons, callback answers, and persistence on both mobile and desktop. Use an English ad and matching targeting. Telegram determines approval and timing; code alone cannot guarantee either.

Suggested ad text:

Practise general knowledge with SharkBonus. Take a daily quiz, solve quick maths challenges, and track your learning progress directly in Telegram.

Official requirements: https://ads.telegram.org/guidelines
