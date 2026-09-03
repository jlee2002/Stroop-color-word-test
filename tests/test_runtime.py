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


def scripted_observer(updates, commands, display):
    commands.put("connected")
    commands.put("resume")
    while True:
        state = updates.get(timeout=10)
        if state["phase"] == "done":
            commands.put("stop")
            return
        if state["phase"] == "closed":
            return


def timeout_observer(updates, commands, display):
    commands.put("connected")
    commands.put({"response_limit_seconds": .03})
    commands.put("resume")
    while True:
        state = updates.get(timeout=10)
        if state["phase"] == "error":
            commands.put("resume")
        elif state["phase"] in ("done", "closed"):
            commands.put("stop")
            return


@unittest.skipUnless(importlib.util.find_spec("pygame"), "Pygame not installed")
class RuntimeTests(unittest.TestCase):
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

    def test_space_resumes_error_from_participant_window_and_saves_csv(self):
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            import pygame as pg
            import stroop
            finished = threading.Event()

            def answer():
                press_space = False
                while not finished.wait(.1):
                    if pg.display.get_init():
                        try:
                            pg.event.post(pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE if press_space else pg.K_8))
                            press_space = not press_space
                        except pg.error:
                            pass

            worker = threading.Thread(target=answer, daemon=True)
            with tempfile.TemporaryDirectory() as folder:
                args = SimpleNamespace(participant_display=0, observer_display=0,
                                       fullscreen=False, trials=1, seed=123, output=folder, duration=None)
                worker.start()
                try:
                    with patch.object(stroop, "observer_window", scripted_observer):
                        stroop.run(args)
                finally:
                    finished.set()
                    worker.join(timeout=2)
                files = list(Path(folder).glob("*.csv"))
                self.assertEqual(len(files), 1)
                with files[0].open(newline="", encoding="utf-8") as log:
                    rows = list(csv.DictReader(log))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["response"], "WHITE")
                self.assertEqual(rows[0]["correct"], "False")
                self.assertGreaterEqual(float(rows[0]["response_ms"]), 0)

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
