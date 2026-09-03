import unittest

from test1 import COLORS, Session, make_trials


class SessionTests(unittest.TestCase):
    def test_conditions_and_reproducible_order(self):
        trials = make_trials(40, 17)
        self.assertEqual(trials, make_trials(40, 17))
        self.assertEqual(sum(t.condition == "INK" for t in trials), 20)
        for trial in trials:
            self.assertEqual(trial.word == trial.ink, trial.condition == "WORD")
            self.assertEqual(trial.answer, trial.ink)

    def test_error_requires_resume_and_cannot_accept_duplicate(self):
        session = Session(make_trials(2, 1))
        session.advance()
        self.assertIsNone(session.respond("RED", 100))
        session.onset = 100
        wrong = next(c for c in COLORS if c != session.trial.answer)
        row = session.respond(wrong, 100.125)
        self.assertFalse(row["correct"])
        self.assertEqual(row["response_ms"], 125)
        self.assertEqual(session.phase, "error")
        self.assertIsNone(session.respond(session.trial.answer, 101))
        self.assertEqual(len(session.rows), 1)
        session.advance()
        self.assertEqual(session.index, 1)
        self.assertIsNone(session.onset)

    def test_completion_and_correct_totals(self):
        session = Session(make_trials(1, 2))
        session.advance()
        session.onset = 10
        session.respond(session.trial.answer, 11)
        self.assertEqual(session.phase, "correct")
        session.advance()
        self.assertEqual(session.phase, "done")
        self.assertEqual(session.snapshot()["correct"], 1)
        self.assertIsNone(session.trial)
        self.assertIsNone(session.respond("RED", 12))


if __name__ == "__main__":
    unittest.main()
