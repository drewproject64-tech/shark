"""SharkBonus: three educational features, using the official Telegram Bot API."""
import datetime as dt
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import secrets
import sqlite3
import time
import urllib.error
import urllib.request

NAME = 'SharkBonus'
ABOUT = 'Daily quizzes, quick maths challenges, and personal learning progress.'
DESCRIPTION = ('SharkBonus helps you practise general knowledge and maths inside Telegram. '
               'Choose Daily Quiz, Quick Challenge, or My Progress. Scores track learning only; '
               'there are no prizes, payments, or cash rewards.')
MENU = {'keyboard': [['Daily Quiz'], ['Quick Challenge'], ['My Progress']], 'resize_keyboard': True, 'is_persistent': True}
QUESTIONS = [
 ('Which planet is known as the Red Planet?', ['Mars', 'Venus', 'Saturn'], 0, 'Iron oxide gives Mars its reddish appearance.'),
 ('How many sides does a hexagon have?', ['Five', 'Six', 'Eight'], 1, 'A hexagon has six sides.'),
 ('Which ocean is the largest?', ['Atlantic', 'Indian', 'Pacific'], 2, 'The Pacific is the largest ocean.'),
 ('What do plants absorb during photosynthesis?', ['Carbon dioxide', 'Helium', 'Hydrogen'], 0, 'Plants use carbon dioxide, water, and sunlight to make sugars.'),
 ('What is the chemical formula for water?', ['CO2', 'H2O', 'O2'], 1, 'Water contains two hydrogen atoms and one oxygen atom.'),
 ('Which instrument measures temperature?', ['Compass', 'Thermometer', 'Barometer'], 1, 'A thermometer measures temperature.'),
 ('How many minutes are in two hours?', ['90', '100', '120'], 2, 'Each hour has 60 minutes, so two hours contain 120.'),
 ('Which is a mammal?', ['Dolphin', 'Shark', 'Trout'], 0, 'Dolphins breathe air and nurse their young.'),
 ('Which number is prime?', ['9', '11', '15'], 1, '11 has exactly two positive divisors: 1 and 11.'),
 ('What is the capital of Japan?', ['Kyoto', 'Osaka', 'Tokyo'], 2, 'Tokyo is the capital of Japan.'),
 ('Which organ pumps blood?', ['Heart', 'Liver', 'Lung'], 0, 'The heart pumps blood through the circulatory system.'),
 ('How many degrees are in a right angle?', ['45', '90', '180'], 1, 'A right angle measures 90 degrees.'),
 ('Which language is mainly spoken in Brazil?', ['Spanish', 'Portuguese', 'French'], 1, 'Portuguese is the official language of Brazil.'),
 ('Which is the smallest of these units?', ['Metre', 'Kilometre', 'Millimetre'], 2, 'One millimetre is one thousandth of a metre.'),
 ('What is 25 percent of 80?', ['20', '25', '40'], 0, 'One quarter of 80 is 20.'),
]

class APIError(Exception):
    def __init__(self, code, retry=3):
        self.code, self.retry = code, retry
        super().__init__(f'Telegram API error {code}')

class Telegram:
    def __init__(self, token):
        self.base = 'https://api.telegram.org/bot' + token + '/'
    def call(self, method, **data):
        request = urllib.request.Request(self.base + method, json.dumps(data).encode(), {'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            raise APIError(exc.code) from None
        except (urllib.error.URLError, TimeoutError):
            raise APIError(0) from None
        if not result.get('ok'):
            raise APIError(result.get('error_code', 0), result.get('parameters', {}).get('retry_after', 3))
        return result['result']

class Bot:
    def __init__(self, api, path):
        self.api = api
        self.db = sqlite3.connect(path)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS progress(uid INTEGER PRIMARY KEY, quizzes INTEGER DEFAULT 0, correct INTEGER DEFAULT 0, challenges INTEGER DEFAULT 0, challenge_correct INTEGER DEFAULT 0, day TEXT);
        CREATE TABLE IF NOT EXISTS sessions(uid INTEGER PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value INTEGER);
        ''')
    def send(self, uid, text, markup=MENU):
        return self.api.call('sendMessage', chat_id=uid, text=text, reply_markup=markup)
    def save(self, uid, session):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO sessions VALUES (?,?)', (uid, json.dumps(session)))
    def session(self, uid):
        row = self.db.execute('SELECT data FROM sessions WHERE uid=?', (uid,)).fetchone()
        return json.loads(row[0]) if row else None
    def prompt(self, uid, s):
        if s['kind'] == 'quiz':
            question, options, _, _ = QUESTIONS[s['ids'][s['index']]]
            text = f"Daily Quiz {s['index'] + 1}/5\n{question}"
        else:
            question, options = s['question'], s['options']
            text = 'Quick Challenge\n' + question
        markup = {'inline_keyboard': [[{'text': option, 'callback_data': f"a:{s['nonce']}:{i}"}] for i, option in enumerate(options)]}
        self.send(uid, text, markup)
    def handle(self, update):
        if 'callback_query' in update:
            return self.answer(update['callback_query'])
        msg = update.get('message', {})
        if msg.get('chat', {}).get('type') != 'private':
            return
        uid = msg['from']['id']
        text = msg.get('text', '')
        command = text.split()[0].split('@')[0] if text else ''
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO progress(uid) VALUES (?)', (uid,))
        if command in ('/start', '/help', '/menu'):
            return self.send(uid, 'Welcome to SharkBonus! Practise general knowledge and maths.\n\nDaily Quiz: five questions each day.\nQuick Challenge: a short maths question.\nMy Progress: your saved learning scores.\n\nChoose a button below. Use /cancel to leave a question, /privacy for data details, or /delete_data to erase your progress.')
        if command == '/privacy':
            return self.send(uid, 'We store your Telegram user ID, learning scores, daily quiz date, and current question in a local database. We do not store your name, username, or message history. Use /delete_data to erase your records. No marketing messages are sent.')
        if command in ('/cancel', '/delete_data'):
            with self.db:
                self.db.execute('DELETE FROM sessions WHERE uid=?', (uid,))
                if command == '/delete_data':
                    self.db.execute('DELETE FROM progress WHERE uid=?', (uid,))
            return self.send(uid, 'Your saved data has been deleted.' if command == '/delete_data' else 'Question closed. Choose a feature below.')
        if text == 'My Progress':
            p = self.db.execute('SELECT quizzes,correct,challenges,challenge_correct FROM progress WHERE uid=?', (uid,)).fetchone()
            return self.send(uid, f'Daily quizzes completed: {p[0]}\nQuiz answers correct: {p[1]}/{p[0]*5}\nChallenges completed: {p[2]}\nChallenge answers correct: {p[3]}/{p[2]}\n\nScores are for personal learning only.')
        if text in ('Daily Quiz', 'Quick Challenge'):
            s = self.session(uid)
            if s:
                self.send(uid, 'Continue your current activity below, or use /cancel to start another.')
                return self.prompt(uid, s)
            if text == 'Daily Quiz':
                today = dt.datetime.now(dt.timezone.utc).date().isoformat()
                if self.db.execute('SELECT day FROM progress WHERE uid=?', (uid,)).fetchone()[0] == today:
                    return self.send(uid, 'You completed today’s quiz. The next quiz opens at 00:00 UTC. Try Quick Challenge meanwhile.')
                seed = int.from_bytes(hashlib.sha256(today.encode()).digest(), 'big')
                s = {'kind': 'quiz', 'ids': random.Random(seed).sample(range(len(QUESTIONS)), 5), 'index': 0, 'score': 0, 'day': today}
            else:
                a, b = secrets.randbelow(20)+1, secrets.randbelow(20)+1
                choices = [a+b, a+b+1, a+b-1]
                random.SystemRandom().shuffle(choices)
                s = {'kind': 'challenge', 'question': f'What is {a} + {b}?', 'options': list(map(str, choices)), 'correct': choices.index(a+b)}
            s['nonce'] = secrets.token_hex(6)
            self.save(uid, s)
            return self.prompt(uid, s)
        self.send(uid, 'Choose Daily Quiz, Quick Challenge, or My Progress below. Use /help for instructions.')
    def answer(self, query):
        uid = query['from']['id']
        s = self.session(uid)
        parts = query.get('data', '').split(':')
        if not s or len(parts) != 3 or parts[0] != 'a' or parts[1] != s['nonce'] or parts[2] not in ('0', '1', '2'):
            return self.api.call('answerCallbackQuery', callback_query_id=query['id'], text='This question is closed. Choose a feature from the menu.')
        index = int(parts[2])
        if s['kind'] == 'quiz':
            _, options, correct, explanation = QUESTIONS[s['ids'][s['index']]]
        else:
            options, correct = s['options'], s['correct']
            explanation = 'Add the two numbers to find the total.'
        success = index == correct
        feedback = ('Correct! ' if success else f'Answer: {options[correct]}. ') + explanation
        with self.db:
            if s['kind'] == 'quiz':
                s['score'] += int(success)
                s['index'] += 1
                if s['index'] == 5:
                    self.db.execute('UPDATE progress SET quizzes=quizzes+1,correct=correct+?,day=? WHERE uid=?', (s['score'], s['day'], uid))
                    self.db.execute('DELETE FROM sessions WHERE uid=?', (uid,))
                    feedback += f"\nQuiz complete: {s['score']}/5."
                    s = None
                else:
                    s['nonce'] = secrets.token_hex(6)
                    self.save(uid, s)
            else:
                self.db.execute('UPDATE progress SET challenges=challenges+1,challenge_correct=challenge_correct+? WHERE uid=?', (int(success), uid))
                self.db.execute('DELETE FROM sessions WHERE uid=?', (uid,))
                s = None
        self.api.call('answerCallbackQuery', callback_query_id=query['id'], text='Answer saved.')
        self.send(uid, feedback)
        if s:
            self.prompt(uid, s)

def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    token = os.environ.get('BOT_TOKEN', '').strip()
    if not token:
        raise SystemExit('Set BOT_TOKEN to your BotFather token before starting.')
    path = os.environ.get('DATABASE_PATH', 'data/sharkbonus.db')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    api = Telegram(token)
    bot = Bot(api, path)
    api.call('deleteWebhook', drop_pending_updates=False)
    api.call('setMyName', name=NAME)
    api.call('setMyShortDescription', short_description=ABOUT)
    api.call('setMyDescription', description=DESCRIPTION)
    api.call('setMyCommands', commands=[{'command': c, 'description': d} for c,d in [('start','Open the three-feature menu'),('help','How to use SharkBonus'),('cancel','Close the current activity'),('privacy','View stored data details'),('delete_data','Delete your learning data')]])
    logging.info('SharkBonus polling started; run only one instance per token.')
    while True:
        row = bot.db.execute("SELECT value FROM meta WHERE key='offset'").fetchone()
        offset = row[0] if row else 0
        try:
            updates = api.call('getUpdates', offset=offset, timeout=30, allowed_updates=['message','callback_query'])
            for update in updates:
                try:
                    bot.handle(update)
                except APIError as exc:
                    if exc.code not in (400, 403):
                        raise
                    logging.warning('Update could not be delivered (code %s)', exc.code)
                with bot.db:
                    bot.db.execute("INSERT OR REPLACE INTO meta VALUES ('offset',?)", (update['update_id']+1,))
        except APIError as exc:
            if exc.code in (401,409):
                raise SystemExit('Invalid token or another polling instance is running.') from None
            logging.warning('Telegram temporarily unavailable (code %s); retrying', exc.code)
            time.sleep(max(1, min(exc.retry, 60)))
        except KeyboardInterrupt:
            break

if __name__ == '__main__':
    main()
