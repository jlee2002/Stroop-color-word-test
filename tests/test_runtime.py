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
        if state["phase"] == "error":
            commands.put("resume")
        if state["phase"] == "done":
            commands.put("stop")
            return
        if state["phase"] == "closed":
            return


@unittest.skipUnless(importlib.util.find_spec("pygame"), "Pygame not installed")
class RuntimeTests(unittest.TestCase):
    def test_participant_process_link_and_csv(self):
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            import pygame as pg
            import test1
            finished = threading.Event()

            def answer():
                while not finished.wait(.1):
                    if pg.display.get_init():
                        try:
                            pg.event.post(pg.event.Event(pg.KEYDOWN, key=pg.K_8))
                        except pg.error:
                            pass

            worker = threading.Thread(target=answer, daemon=True)
            with tempfile.TemporaryDirectory() as folder:
                args = SimpleNamespace(participant_display=0, observer_display=0,
                                       fullscreen=False, trials=1, seed=123, output=folder)
                worker.start()
                try:
                    with patch.object(test1, "observer_window", scripted_observer):
                        test1.run(args)
                finally:
                    finished.set()
                    worker.join(timeout=2)
                files = list(Path(folder).glob("*.csv"))
                self.assertEqual(len(files), 1)
                with files[0].open(newline="", encoding="utf-8") as log:
                    rows = list(csv.DictReader(log))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["response"], "WHITE")
                self.assertGreaterEqual(float(rows[0]["response_ms"]), 0)

    def test_observer_render_and_close(self):
        from queue import Queue
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            import test1
            updates, commands = Queue(), Queue()
            updates.put({"phase": "error", "index": 1, "total": 40, "correct": 0,
                         "answered": 1, "last": {"correct": False, "response": "RED",
                         "expected": "BLUE", "condition": "INK", "response_ms": 123}})

            def close():
                time.sleep(.25)
                updates.put({"phase": "closed"})

            closer = threading.Thread(target=close)
            closer.start()
            test1.observer_window(updates, commands, 0)
            closer.join()
            self.assertEqual(commands.get_nowait(), "connected")
            self.assertEqual(commands.get_nowait(), "stop")
