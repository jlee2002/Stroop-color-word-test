# test1

A Python + Pygame experiment prototype with separate participant and observer windows.

The repository's original [experiment overview](docs/experiment-overview.md) describes the Snowball Lab study context.

## Trial rules

- **INK:** a color word is printed in a different color. Choose the ink color, ignoring the word.
- **WORD:** the word and ink color match. Choose the color named by the word.

The conditions are shuffled together, with equal counts (one extra INK trial when the total is odd). Consecutive trials may use the same condition. Colors are sampled independently; color frequencies are not counterbalanced. Each trial shows its instruction. This implements the two conditions described above, not a full factorial Stroop protocol.

Correct answers advance after 650 ms. Wrong answers play a short beep and pause the task. The observer sees the expected answer, selected answer, response time, and a suggested focus reminder. The observer clicks **Continue after error** to move to the next trial. The failed trial is recorded once and is not retried. There is no response deadline.

## Install and run

Install Python 3.10–3.12, then run from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe test1.py
```

Both windows open on display 0 by default for setup on a single monitor. Move them apart using their title bars. Click **Test beep**, then **Start session** in the observer window. The participant clicks a choice in the two-row answer grid or uses **1 = red, 2 = blue, 3 = green, 4 = yellow, 5 = orange, 6 = purple, 7 = pink, 8 = white**. All eight colors are available as words and ink colors. Keyboard answers require participant-window focus; clicking an answer also works. Observer controls use the same computer's mouse; a second keyboard is not independently assigned to the observer.

For two monitors, set Windows displays to **Extend**, then run:

```powershell
.\.venv\Scripts\python.exe test1.py --participant-display 1 --observer-display 0 --fullscreen --trials 40
```

Display indices are zero-based. Swap 0 and 1 if necessary. Omit `--fullscreen` to use movable windows. Pygame runs each window in a separate process, with local queues connecting them. No server or network connection is required.

Use `--seed 123` to reproduce a trial order. Press **Esc** or close either window to stop. After completion, close either window to exit. Sound uses the computer's default audio output, not a monitor-specific output. The observer displays an audio-unavailable notice if initialization fails; test the beep before a session.

## Results

Each run creates a timestamped CSV in `results/`, flushed after each response. Columns include trial number, condition, word, ink, expected/selected answer, correctness, response time in milliseconds, UTC response timestamp, and random seed. Unanswered trials are not recorded. Files remain local and are excluded from Git by `.gitignore`.

Timing starts immediately after Pygame flips the first stimulus frame. These are software response times, not calibrated display-onset measurements. This prototype does not measure blood pressure or establish that a session increases it. The intended experimental protocol and any BP measurement procedure are separate from the app.

## Development

```powershell
python -m unittest discover -s tests -v
```

Before collecting data, check both physical monitors, participant input focus, the audible beep, error pause/resume, and CSV output on the actual experiment computer.

## GitHub

Source and tests are maintained at [jlee2002/Stroop-color-word-test](https://github.com/jlee2002/Stroop-color-word-test). Keep participant results in the ignored `results/` directory.
