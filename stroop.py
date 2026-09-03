"""Two-window test1 task. Run with python stroop.py --help."""

import argparse
from array import array
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
import multiprocessing as mp
from pathlib import Path
from queue import Empty
import random
import time


COLORS = {"RED": (245, 75, 88), "BLUE": (85, 150, 255),
          "GREEN": (60, 210, 140), "YELLOW": (250, 211, 70),
          "ORANGE": (255, 145, 40), "PURPLE": (175, 105, 240),
          "PINK": (255, 155, 200), "WHITE": (245, 245, 245)}
BG = (16, 22, 34)
PANEL = (29, 39, 56)
TEXT = (235, 241, 250)
MUTED = (157, 175, 199)


@dataclass(frozen=True)
class Trial:
    condition: str
    word: str
    ink: str

    @property
    def answer(self):
        return self.ink if self.condition == "INK" else self.word


def make_trials(count, seed=None):
    """Equal conditions (one extra INK for odd counts), shuffled together."""
    rng = random.Random(seed)
    trials = []
    names = list(COLORS)
    for i in range(count):
        condition = "INK" if i % 2 == 0 else "WORD"
        word = rng.choice(names)
        ink = rng.choice([c for c in names if c != word]) if condition == "INK" else word
        trials.append(Trial(condition, word, ink))
    rng.shuffle(trials)
    return trials


class Session:
    """State machine independent of graphics; observer resumes every error."""
    def __init__(self, trials, duration_seconds=None, seed=None):
        self.trials = trials
        self.index = 0
        self.phase = "ready"
        self.onset = None
        self.last = None
        self.rows = []
        self.duration_seconds = duration_seconds
        self.deadline = None
        self.batch_size = len(trials)
        self.refill_rng = random.Random(seed)
        self.response_limit_seconds = None

    def set_response_limit(self, value):
        if self.phase != "ready":
            return False
        self.response_limit_seconds = parse_response_limit(value)
        return True

    def remaining(self, now=None):
        if self.deadline is None:
            return self.duration_seconds or 0
        now = time.perf_counter() if now is None else now
        return max(0, self.deadline - now)

    def expire(self, now=None):
        if self.deadline is not None and self.remaining(now) <= 0 and self.phase != "done":
            self.phase = "done"
            self.onset = None
            return True
        return False

    @property
    def trial(self):
        return self.trials[self.index] if self.index < len(self.trials) else None

    def advance(self, now=None):
        if self.expire(now):
            return
        if self.phase not in ("ready", "correct", "error"):
            return
        if self.phase == "ready" and self.duration_seconds is not None:
            now = time.perf_counter() if now is None else now
            self.deadline = now + self.duration_seconds
        if self.phase != "ready":
            self.index += 1
        if self.index == len(self.trials) and self.duration_seconds is not None:
            self.trials.extend(make_trials(self.batch_size, self.refill_rng.getrandbits(32)))
        self.phase = "done" if self.index == len(self.trials) else "active"
        self.onset = None

    def respond(self, color, now):
        timeout = self.check_timeout(now)
        if timeout:
            return timeout
        if self.phase != "active" or self.onset is None or color not in COLORS:
            return None
        return self._record(color, now)

    def check_timeout(self, now):
        self.expire(now)
        if (self.phase == "active" and self.onset is not None
                and self.response_limit_seconds is not None
                and now - self.onset >= self.response_limit_seconds):
            return self._record("TIMEOUT", now, timed_out=True)
        return None

    def _record(self, color, now, timed_out=False):
        trial = self.trial
        correct = not timed_out and color == trial.answer
        self.last = {"trial": self.index + 1, **asdict(trial),
                     "expected": trial.answer, "response": color,
                     "correct": correct, "response_ms": round((now - self.onset) * 1000, 2),
                     "timed_out": timed_out, "response_limit_seconds": self.response_limit_seconds,
                     "answered_utc": datetime.now(timezone.utc).isoformat()}
        self.rows.append(self.last)
        self.phase = "correct" if correct else "error"
        return self.last

    def snapshot(self):
        return {"phase": self.phase, "index": min(self.index + 1, len(self.trials)),
                "total": len(self.trials), "answered": len(self.rows),
                "correct": sum(r["correct"] for r in self.rows),
                "deadline": self.deadline, "duration_seconds": self.duration_seconds,
                "response_limit_seconds": self.response_limit_seconds,
                "last": self.last}


def parse_response_limit(value):
    if value is None or str(value).strip() == "":
        return None
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Enter a number greater than zero, or leave blank.")
    return seconds


def timer_text(deadline, duration_seconds=120, now=None):
    now = time.perf_counter() if now is None else now
    seconds = math.ceil(max(0, deadline - now) if deadline is not None else (duration_seconds or 0))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def draw_text(pg, screen, text, y, size=28, color=TEXT, center=True, x=36):
    font = pg.font.SysFont("Segoe UI", size)
    surface = font.render(text, True, color)
    rect = surface.get_rect(center=(screen.get_width() // 2, y)) if center else surface.get_rect(topleft=(x, y))
    screen.blit(surface, rect)


def button(pg, screen, rect, label, color=TEXT):
    pg.draw.rect(screen, PANEL, rect, border_radius=12)
    pg.draw.rect(screen, color, rect, width=2, border_radius=12)
    font = pg.font.SysFont("Segoe UI", 24)
    surface = font.render(label, True, color)
    screen.blit(surface, surface.get_rect(center=rect.center))


def open_window(pg, title, display, fullscreen=False):
    pg.display.init()
    pg.font.init()
    desktops = pg.display.get_desktop_sizes()
    if not 0 <= display < len(desktops):
        raise ValueError(f"Display {display} does not exist; available: 0..{len(desktops)-1}")
    size = desktops[display] if fullscreen else (min(960, desktops[display][0] - 60), min(680, desktops[display][1] - 80))
    pg.display.set_caption(title)
    return pg.display.set_mode(size, pg.FULLSCREEN if fullscreen else 0, display=display)


def make_beep(pg):
    try:
        pg.mixer.init(frequency=44100, size=-16, channels=1)
        rate, _, channels = pg.mixer.get_init()
        samples = array("h")
        length = int(rate * 0.22)
        for i in range(length):
            envelope = min(1, i / (rate * .01), (length - i) / (rate * .02))
            value = int(5500 * envelope * math.sin(2 * math.pi * 660 * i / rate))
            samples.extend([value] * channels)
        return pg.mixer.Sound(buffer=samples)
    except pg.error:
        return None


def observer_window(updates, commands, display):
    import pygame as pg
    try:
        screen = open_window(pg, "test1 | Observer", display)
        clock = pg.time.Clock()
        state = {"phase": "connecting"}
        limit_input = ""
        editing_limit = False
        limit_message = "Blank = no limit. Set before starting."
        def apply_limit():
            nonlocal editing_limit, limit_message
            try:
                value = parse_response_limit(limit_input)
            except ValueError:
                limit_message = "Enter positive seconds, e.g. 3 or 2.5."
                return
            commands.put({"response_limit_seconds": value})
            editing_limit = False
            limit_message = "No answer limit." if value is None else f"Answer limit: {value:g} seconds."
        running = True
        commands.put("connected")
        while running:
            try:
                while True:
                    state = updates.get_nowait()
            except Empty:
                pass
            if state["phase"] == "closed":
                break
            w, h = screen.get_size()
            resume = pg.Rect(36, h - 154, w - 72, 54)
            sound = pg.Rect(36, h - 84, (w - 88) // 2, 48)
            stop = pg.Rect(w // 2 + 8, h - 84, (w - 88) // 2, 48)
            limit_rect = pg.Rect(250, h - 265, 140, 44)
            apply_rect = pg.Rect(406, h - 265, 120, 44)
            can_edit = state["phase"] == "ready"
            if not can_edit:
                editing_limit = False
            for event in pg.event.get():
                if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                    running = False
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    if can_edit and limit_rect.collidepoint(event.pos):
                        editing_limit = True
                    elif can_edit and apply_rect.collidepoint(event.pos):
                        apply_limit()
                    elif resume.collidepoint(event.pos):
                        if editing_limit:
                            apply_limit()
                            if editing_limit:
                                continue
                        commands.put("resume")
                    elif sound.collidepoint(event.pos):
                        commands.put("beep")
                    elif stop.collidepoint(event.pos):
                        running = False
                elif event.type == pg.KEYDOWN and editing_limit:
                    if event.key in (pg.K_RETURN, pg.K_KP_ENTER):
                        apply_limit()
                    elif event.key == pg.K_BACKSPACE:
                        limit_input = limit_input[:-1]
                    elif getattr(event, "unicode", "") in "0123456789." and len(limit_input) < 12:
                        limit_input += getattr(event, "unicode", "")
                elif event.type == pg.KEYDOWN and event.key == pg.K_SPACE and not getattr(event, "repeat", False):
                    commands.put("resume")
            screen.fill(BG)
            draw_text(pg, screen, "OBSERVER CONSOLE", 40, 20, MUTED)
            draw_text(pg, screen, timer_text(state.get("deadline"), state.get("duration_seconds", 120)),
                      22, 28, TEXT, center=False, x=w - 120)
            phase = state["phase"]
            titles = {"connecting": "Connecting...", "ready": "Ready to begin",
                      "active": "Participant responding", "correct": "Correct",
                      "error": "Incorrect - task paused", "done": "Session complete"}
            accent = COLORS["RED"] if phase == "error" else COLORS["GREEN"] if phase in ("correct", "done") else TEXT
            draw_text(pg, screen, titles.get(phase, phase), 100, 34, accent)
            if "total" in state:
                draw_text(pg, screen, f"Trial {state['index']}     |     Correct {state['correct']} / {state['answered']}", 160, 24)
                last = state.get("last")
                if last:
                    draw_text(pg, screen, f"Last response: {'CORRECT' if last['correct'] else 'INCORRECT'}", 222, 27,
                              COLORS["GREEN"] if last["correct"] else COLORS["RED"])
                    detail = f"Time limit exceeded   /   Expected {last['expected']}" if last.get("timed_out") else f"Selected {last['response']}   /   Expected {last['expected']}"
                    draw_text(pg, screen, detail, 265, 24)
                    draw_text(pg, screen, f"{last['condition']} condition   |   {last['response_ms']:.0f} ms", 305, 23, MUTED)
                if phase == "error":
                    draw_text(pg, screen, 'Prompt: "Please focus on the instruction."', 356, 24)
                draw_text(pg, screen, state.get("audio", ""), h - 182, 18, MUTED)
            draw_text(pg, screen, "Answer limit (seconds)", h - 255, 20, MUTED, center=False)
            if can_edit:
                button(pg, screen, limit_rect, limit_input + ("|" if editing_limit else ""), COLORS["BLUE"] if editing_limit else TEXT)
                button(pg, screen, apply_rect, "Apply")
                draw_text(pg, screen, "Enter to apply. " + limit_message, h - 208, 18, MUTED)
            else:
                value = state.get("response_limit_seconds")
                draw_text(pg, screen, "Off" if value is None else f"{value:g} s", h - 255, 24, TEXT, center=False, x=270)
                draw_text(pg, screen, "Answer limit is fixed once the session starts.", h - 208, 18, MUTED)
            button(pg, screen, resume, "Start session / Space" if phase == "ready" else "Continue / Space" if phase == "error" else "Waiting" if phase != "done" else "Complete", accent)
            button(pg, screen, sound, "Test beep")
            button(pg, screen, stop, "End session / Esc")
            pg.display.flip()
            clock.tick(30)
    finally:
        commands.put("stop")
        pg.quit()


def run(args):
    import pygame as pg
    key_map = {getattr(pg, f"K_{i}"): color for i, color in enumerate(COLORS, 1)}
    screen = open_window(pg, "test1 | Participant", args.participant_display, args.fullscreen)
    beep = make_beep(pg)
    audio = "Audio ready - test beep before starting" if beep else "AUDIO UNAVAILABLE - visual alerts only"
    session = Session(make_trials(args.trials, args.seed), duration_seconds=args.duration, seed=args.seed)
    ctx = mp.get_context("spawn")
    updates, commands = ctx.Queue(), ctx.Queue()
    observer = ctx.Process(target=observer_window, args=(updates, commands, args.observer_display))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    filename = output / (datetime.now(timezone.utc).strftime("session_%Y%m%dT%H%M%S_%fZ") + ".csv")
    fields = ["trial", "condition", "word", "ink", "expected", "response", "correct", "response_ms", "answered_utc", "seed", "timed_out", "response_limit_seconds"]
    clock = pg.time.Clock()
    correct_until = 0
    connected = False
    running = True
    last_update = 0
    def publish():
        updates.put({**session.snapshot(), "audio": audio})
    observer.start()
    try:
        with filename.open("x", newline="", encoding="utf-8") as log:
            writer = csv.DictWriter(log, fieldnames=fields)
            writer.writeheader()
            log.flush()
            def save_response(row):
                nonlocal correct_until
                if row is None:
                    return
                writer.writerow({**row, "seed": args.seed})
                log.flush()
                if row["correct"]:
                    correct_until = time.perf_counter() + .25
                elif beep:
                    beep.play()
                publish()
            publish()
            while running:
                if not observer.is_alive():
                    break
                if session.expire():
                    publish()
                save_response(session.check_timeout(time.perf_counter()))
                try:
                    while True:
                        command = commands.get_nowait()
                        if isinstance(command, dict) and "response_limit_seconds" in command:
                            session.set_response_limit(command["response_limit_seconds"])
                            publish()
                        elif command == "connected":
                            connected = True
                        elif command == "stop":
                            running = False
                        elif command == "beep" and beep:
                            beep.play()
                        elif command == "resume" and connected and session.phase in ("ready", "error"):
                            session.advance()
                            publish()
                except Empty:
                    pass
                if not running:
                    break
                w, h = screen.get_size()
                columns = 4
                rows = math.ceil(len(COLORS) / columns)
                cell_width = (w - 60) // columns
                buttons = [pg.Rect(30 + (i % columns) * cell_width,
                                   h - 70 - rows * 76 + (i // columns) * 76,
                                   cell_width - 12, 64) for i in range(len(COLORS))]
                for event in pg.event.get():
                    response = None
                    if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                        running = False
                        break
                    if event.type == pg.KEYDOWN and not getattr(event, "repeat", False):
                        if event.key == pg.K_SPACE and connected and session.phase in ("ready", "error"):
                            session.advance()
                            publish()
                        else:
                            response = key_map.get(event.key)
                    elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                        response = next((c for c, rect in zip(COLORS, buttons) if rect.collidepoint(event.pos)), None)
                    if response:
                        row = session.respond(response, time.perf_counter())
                        save_response(row)
                if session.phase == "correct" and time.perf_counter() >= correct_until:
                    session.advance()
                    publish()
                session.expire()
                if time.perf_counter() - last_update >= .1:
                    publish()
                    last_update = time.perf_counter()
                screen.fill(BG)
                draw_text(pg, screen, "test1", 45, 22, MUTED)
                draw_text(pg, screen, timer_text(session.deadline, session.duration_seconds),
                          22, 28, TEXT, center=False, x=w - 120)
                if session.phase == "active":
                    trial = session.trial
                    draw_text(pg, screen, "Choose the INK COLOR" if trial.condition == "INK" else "Choose the color NAMED BY THE WORD", 122, 30)
                    draw_text(pg, screen, "Ignore what the word says." if trial.condition == "INK" else "The word and ink color match.", 167, 23, MUTED)
                    draw_text(pg, screen, trial.word, h // 2 - 25, 90, COLORS[trial.ink])
                    for i, (color, rect) in enumerate(zip(COLORS, buttons), 1):
                        button(pg, screen, rect, f"{i}  {color}")
                elif session.phase != "correct":
                    messages = {"ready": "Wait for the observer to start.",
                                "error": "Paused - wait for the observer.", "done": "Session complete. Thank you."}
                    draw_text(pg, screen, messages[session.phase], h // 2, 32)
                draw_text(pg, screen, f"Click an answer or press 1-{len(COLORS)}   |   Esc to end", h - 35, 19, MUTED)
                pg.display.flip()
                if session.phase == "active" and session.onset is None:
                    # Begin timing only after the first frame containing the stimulus.
                    session.onset = time.perf_counter()
                clock.tick(60)
    finally:
        updates.put({"phase": "closed"})
        observer.join(timeout=3)
        if observer.is_alive():
            observer.terminate()
            observer.join(timeout=2)
        pg.quit()
        print(f"Responses saved to: {filename.resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=40, help="Trials per shuffled batch; batches refill until time expires")
    parser.add_argument("--duration", type=float, default=120, help="Session duration in seconds (default: 120)")
    parser.add_argument("--seed", type=int, help="Seed for repeatable trial order")
    parser.add_argument("--participant-display", type=int, default=0)
    parser.add_argument("--observer-display", type=int, default=0)
    parser.add_argument("--fullscreen", action="store_true", help="Participant fullscreen (use separate displays)")
    parser.add_argument("--output", default="results", help="Local CSV directory")
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials must be positive")
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("--duration must be a positive finite number")
    if args.fullscreen and args.participant_display == args.observer_display:
        parser.error("Fullscreen requires different participant and observer displays")
    if args.seed is None:
        args.seed = random.SystemRandom().randrange(2**32)
    run(args)


if __name__ == "__main__":
    mp.freeze_support()
    main()
