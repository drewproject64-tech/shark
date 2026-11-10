import tempfile
import unittest
from bot import Bot, QUESTIONS, ABOUT, DESCRIPTION

class FakeAPI:
    def __init__(self): self.calls = []
    def call(self, method, **data): self.calls.append((method, data)); return True

class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.api = FakeAPI()
        self.bot = Bot(self.api, self.tmp.name + '/test.db')
    def tearDown(self):
        self.bot.db.close()
        self.tmp.cleanup()
    def message(self, text):
        self.bot.handle({'message': {'chat': {'type': 'private'}, 'from': {'id': 1}, 'text': text}})
    def answer(self, s, choice):
        query = {'id':'q', 'from':{'id':1}, 'data':f"a:{s['nonce']}:{choice}"}
        self.bot.handle({'callback_query':query})
        return query
    def test_quiz_completion_duplicate_and_daily_limit(self):
        self.message('/start')
        self.message('Daily Quiz')
        for _ in range(5):
            s = self.bot.session(1)
            q = self.answer(s, QUESTIONS[s['ids'][s['index']]][2])
            self.bot.handle({'callback_query':q})
        self.assertIsNone(self.bot.session(1))
        self.assertEqual(self.bot.db.execute('SELECT quizzes,correct FROM progress').fetchone(), (1,5))
        self.message('Daily Quiz')
        self.assertIsNone(self.bot.session(1))
    def test_challenge_resume_and_delete(self):
        self.message('Quick Challenge')
        s = self.bot.session(1)
        self.message('Daily Quiz')
        self.assertEqual(s, self.bot.session(1))
        self.answer(s, s['correct'])
        self.assertEqual(self.bot.db.execute('SELECT challenges,challenge_correct FROM progress').fetchone(), (1,1))
        self.message('/delete_data')
        self.assertEqual(self.bot.db.execute('SELECT count(*) FROM progress').fetchone()[0], 0)
        self.message('My Progress')
        self.assertIn('Daily quizzes completed: 0', self.api.calls[-1][1]['text'])
    def test_cancel_invalid_and_metadata(self):
        self.message('Daily Quiz')
        s = self.bot.session(1)
        self.message('/cancel')
        self.answer(s, 0)
        self.assertIsNone(self.bot.session(1))
        self.assertLessEqual(len(ABOUT),120)
        self.assertLessEqual(len(DESCRIPTION),512)
    def test_progress_survives_restart(self):
        self.message('Quick Challenge')
        s = self.bot.session(1)
        self.bot.db.close()
        self.bot = Bot(self.api, self.tmp.name+'/test.db')
        self.assertEqual(s, self.bot.session(1))
        self.answer(s, s['correct'])
        self.message('My Progress')
        self.assertIn('Challenge answers correct: 1/1', self.api.calls[-1][1]['text'])

if __name__ == '__main__': unittest.main()
