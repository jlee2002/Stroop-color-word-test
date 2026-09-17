"""Headless smoke checks; physical monitors and audible output need a manual check."""
import csv
import importlib.util
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


def scripted_observer(updates, commands, display, fullscreen=False):
    commands.put("connected")
    commands.put("resume")
    while True:
        state = updates.get(timeout=10)
        if state["phase"] == "ready":
            commands.put("resume")
        if state["phase"] == "done":
            commands.put("stop")
            return
        if state["phase"] == "closed":
            return


def practice_observer(updates, commands, display, fullscreen=False):
    commands.put("connected")
    commands.put("resume")
    for _ in range(4):
        state = updates.get(timeout=10)
        assert state["phase"] == "practice"
        assert state["deadline"] is None
        assert state["answered"] == 0
    commands.put("stop")


def timeout_observer(updates, commands, display, fullscreen=False):
    commands.put("connected")
    commands.put({"response_limit_seconds": .03})
    commands.put("resume")
    while True:
        state = updates.get(timeout=10)
        if state["phase"] in ("ready", "error"):
            commands.put("resume")
        elif state["phase"] in ("done", "closed"):
            commands.put("stop")
            return


def grading_observer(updates, commands, display, fullscreen=False):
    commands.put("connected")
    commands.put("resume")
    restarted = False
    awaiting_ready = False
    while True:
        state = updates.get(timeout=10)
        if state["phase"] == "active":
            commands.put({"grade": restarted, "trial": state["index"]})
        elif state["phase"] == "error":
            commands.put("resume")
        elif state["phase"] == "done":
            if awaiting_ready:
                continue
            if restarted:
                commands.put("stop")
                return
            restarted = True
            awaiting_ready = True
            commands.put("restart")
        elif state["phase"] == "ready":
            awaiting_ready = False
            commands.put("resume")
        elif state["phase"] == "closed":
            return


@unittest.skipUnless(importlib.util.find_spec("pygame"), "Pygame not installed")
class RuntimeTests(unittest.TestCase):
    def test_practice_previous_revisits_introductions_and_examples(self):
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            import pygame as pg
            import stroop
            next_click = pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(600, 595))
            previous = pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(350, 595))
            pages = [[], [next_click], [next_click], [previous], [previous],
                     [next_click], [next_click], [next_click], [next_click],
                     [next_click], [previous], [next_click], [next_click], [next_click], [next_click]]
            events = iter(pages)
            with tempfile.TemporaryDirectory() as folder:
                args = SimpleNamespace(participant_display=0, observer_display=0,
                                       fullscreen=False, trials=1, seed=123, output=folder, duration=.05)
                with patch.object(stroop, "observer_window", scripted_observer), \
                     patch.object(pg.event, "get", side_effect=lambda: next(events, [])), \
                     patch.object(stroop, "draw_practice", wraps=stroop.draw_practice) as draw:
                    stroop.run(args)
                self.assertEqual([call.args[2] for call in draw.call_args_list],
                                 [0, 1, 2, 1, 0, 1, 2, 3, 4, 5, 4, 5, 6, 7])

    def test_instructions_block_start_and_leave_timer_stopped(self):
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            import pygame as pg
            import stroop
            with tempfile.TemporaryDirectory() as folder:
                args = SimpleNamespace(participant_display=0, observer_display=0,
                                       fullscreen=False, trials=40, seed=123, output=folder, duration=.01)
                with patch.object(stroop, "observer_window", practice_observer), patch.object(pg.event, "get", return_value=[]):
                    stroop.run(args)
                with next(Path(folder).glob("*.csv")).open(newline="", encoding="utf-8") as log:
                    self.assertEqual(list(csv.DictReader(log)), [])

    def setUp(self):
        import pygame as pg
        # Participant clicks each guided page; observer runs in its own process.
        click = pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(600, 595))
        patcher = patch.object(pg.event, "get", return_value=[click])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_no_answer_timeout_is_written_to_csv(self):
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            import stroop
            with tempfile.TemporaryDirectory() as folder:
                args = SimpleNamespace(participant_display=0, observer_display=0,
                                       fullscreen=False, trials=1, seed=123, output=folder, duration=None)
                with patch.object(stroop, "observer_window", timeout_observer):
                    stroop.run(args)
                with next(Path(folder).glob("*.csv")).open(newline="", encoding="utf-8") as log:
                    rows = list(csv.DictReader(log))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["response"], "TIMEOUT")
                self.assertEqual(rows[0]["correct"], "False")
                self.assertEqual(rows[0]["timed_out"], "True")
                self.assertEqual(float(rows[0]["response_limit_seconds"]), .03)

    def test_observer_can_enter_answer_limit(self):
        from queue import Queue
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            import pygame as pg
            import stroop
            updates, commands = Queue(), Queue()
            updates.put(stroop.Session(stroop.make_trials(2)).snapshot())
            events = [pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(260, 425)),
                      pg.event.Event(pg.KEYDOWN, key=pg.K_3, unicode="3"),
                      pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN), pg.event.Event(pg.QUIT)]
            with patch.object(pg.event, "get", return_value=events):
                stroop.observer_window(updates, commands, 0)
            self.assertEqual(commands.get_nowait(), "connected")
            self.assertEqual(commands.get_nowait(), {"response_limit_seconds": 3.0})
            self.assertEqual(commands.get_nowait(), "stop")

    def test_timer_finishes_without_any_response(self):
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            import stroop
            with tempfile.TemporaryDirectory() as folder:
                args = SimpleNamespace(participant_display=0, observer_display=0,
                                       fullscreen=False, trials=40, seed=123, output=folder, duration=.2)
                with patch.object(stroop, "observer_window", scripted_observer):
                    stroop.run(args)
                with next(Path(folder).glob("*.csv")).open(newline="", encoding="utf-8") as log:
                    self.assertEqual(list(csv.DictReader(log)), [])

    def test_observer_grades_and_restarts_with_shuffle(self):
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            import stroop
            with tempfile.TemporaryDirectory() as folder:
                args = SimpleNamespace(participant_display=0, observer_display=0,
                                       fullscreen=False, trials=1, seed=123, output=folder, duration=None)
                with patch.object(stroop, "observer_window", grading_observer):
                    stroop.run(args)
                with next(Path(folder).glob("*.csv")).open(newline="", encoding="utf-8") as log:
                    rows = list(csv.DictReader(log))
                self.assertEqual(len(rows), 2)
                self.assertEqual([r["session"] for r in rows], ["1", "2"])
                self.assertEqual([r["correct"] for r in rows], ["False", "True"])
                self.assertNotEqual(rows[0]["seed"], rows[1]["seed"])

    def test_observer_render_and_close(self):
        from queue import Queue
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            import stroop
            updates, commands = Queue(), Queue()
            updates.put({"phase": "error", "index": 1, "total": 40, "correct": 0,
                         "answered": 1, "last": {"correct": False, "response": "RED",
                         "expected": "BLUE", "condition": "INK", "response_ms": 123}})

            def close():
                time.sleep(.25)
                updates.put({"phase": "closed"})

            closer = threading.Thread(target=close)
            closer.start()
            stroop.observer_window(updates, commands, 0)
            closer.join()
            self.assertEqual(commands.get_nowait(), "connected")
            self.assertEqual(commands.get_nowait(), "stop")
