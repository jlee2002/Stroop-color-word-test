import unittest

from stroop import COLORS, Session, make_trials, timer_text


class SessionTests(unittest.TestCase):
    def test_timer_starts_on_start_and_expires_during_error_pause(self):
        session = Session(make_trials(2, 1), duration_seconds=120)
        self.assertEqual(session.remaining(500), 120)
        session.advance(now=500)
        session.onset = 500
        wrong = next(c for c in COLORS if c != session.trial.answer)
        session.respond(wrong, 501)
        self.assertEqual(session.remaining(560), 60)
        self.assertTrue(session.expire(620))
        self.assertEqual(session.phase, "done")
        session.advance(now=621)
        self.assertEqual(session.phase, "done")
        self.assertEqual(timer_text(session.deadline, now=621), "00:00")

    def test_timed_session_refills_and_rejects_answers_at_deadline(self):
        session = Session(make_trials(1, 1), duration_seconds=120, seed=1)
        session.advance(now=0)
        session.onset = 0
        session.respond(session.trial.answer, 1)
        session.advance(now=2)
        self.assertEqual(session.phase, "active")
        self.assertEqual(session.index, 1)
        session.onset = 2
        self.assertIsNone(session.respond(session.trial.answer, 120))
        self.assertEqual(len(session.rows), 1)
        self.assertEqual(session.phase, "done")
        self.assertEqual(timer_text(None), "02:00")
        self.assertEqual(timer_text(120, now=60), "01:00")

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
