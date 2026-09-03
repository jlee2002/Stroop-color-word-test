# test1

A Python + Pygame experiment prototype with separate participant and observer windows.

The repository's original [experiment overview](docs/experiment-overview.md) describes the Snowball Lab study context.

## Trial rules

- **INK:** a color word is printed in a different color. Choose the ink color, ignoring the word.
- **WORD:** the word and ink color match. Choose the color named by the word.

The session lasts **two minutes**, starting when the observer presses Space or Start. Both windows show the same countdown from **02:00** to **00:00**. The clock continues during error pauses and between trials. At zero, the task ends automatically and no further answers are accepted.

The conditions are shuffled in batches of 40, with equal counts (one extra INK trial when a batch has an odd size). New batches are generated as needed until time expires; 40 is not a session limit. The number of completed trials and the condition counts depend on response speed and pauses. Consecutive trials may use the same condition. Colors are sampled independently; color frequencies are not counterbalanced. Each trial shows its instruction. This implements the two conditions described above, not a full factorial Stroop protocol.

Correct answers advance after a **250 ms blank stimulus interval**, with the countdown still visible. Participants no longer see a response-confirmation message. Wrong answers play a short beep and pause the task, but not the countdown. The observer sees the expected answer, selected answer, response time, and a suggested focus reminder. The observer presses **Space** (or clicks **Continue / Space**) to move to the next trial. Space works with either game window focused, so the participant can keep using the mouse. Space also starts a waiting session; it does nothing during an active trial or after completion. The failed trial is recorded once and is not retried.

### Optional answer time limit

Before starting, click the observer's **Answer limit (seconds)** field, type a positive number such as `3` or `2.5`, and click **Apply** or press **Enter**. Leave the field blank and apply it to disable the limit. The setting is fixed once the session starts.

The limit starts when each stimulus first appears. An unanswered trial that reaches the limit is marked incorrect, beeps, and pauses until the observer presses Space. A late answer cannot replace a timeout. The observer sees **Time limit exceeded**. The two-minute session countdown continues throughout; session completion takes precedence if both deadlines are reached together.

## Install and run

Install Python 3.10–3.12, then run from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe stroop.py
```

Both windows open on display 0 by default for setup on a single monitor. Move them apart using their title bars. Click **Test beep**, then press **Space** to start. The participant clicks a choice in the two-row answer grid or uses **1 = red, 2 = blue, 3 = green, 4 = yellow, 5 = orange, 6 = purple, 7 = pink, 8 = white**. All eight colors are available as words and ink colors. Keyboard answers require participant-window focus; clicking an answer also works. The observer can use the keyboard's Space key while the participant uses the mouse. Either game window must be focused; Space is not a system-wide shortcut. Keyboards attached to this computer share input, so Space is not restricted to a particular person or keyboard.

For two monitors, set Windows displays to **Extend**, then run:

```powershell
.\.venv\Scripts\python.exe stroop.py --participant-display 1 --observer-display 0 --fullscreen --trials 40
```

Display indices are zero-based. Swap 0 and 1 if necessary. Omit `--fullscreen` to use movable windows. Pygame runs each window in a separate process, with local queues connecting them. No server or network connection is required.

Use `--seed 123` to reproduce a trial order. The default duration is 120 seconds; `--duration 10` runs a short setup check. `--trials` controls the shuffled batch size, not the session length. Press **Esc** or close either window to stop early. After completion, close either window to exit. Sound uses the computer's default audio output, not a monitor-specific output. The observer displays an audio-unavailable notice if initialization fails; test the beep before a session.

## Results

Each run creates a timestamped CSV in `results/`, flushed after each response or timeout. Columns include trial number, condition, word, ink, expected/selected answer, correctness, response time in milliseconds, UTC response/timeout timestamp, random seed, `timed_out`, and `response_limit_seconds`. Timeouts have response `TIMEOUT`, correctness `False`, and `timed_out=True`. Their response time is the elapsed time when the program detects the timeout, normally within one frame of the limit. An unfinished trial at session end or manual exit is not recorded. Files remain local and are excluded from Git by `.gitignore`.

Timing starts immediately after Pygame flips the first stimulus frame. These are software response times, not calibrated display-onset measurements. This prototype does not measure blood pressure or establish that a session increases it. The intended experimental protocol and any BP measurement procedure are separate from the app.

## Development

```powershell
python -m unittest discover -s tests -v
```

Before collecting data, check both physical monitors, participant input focus, the audible beep, error pause/resume, and CSV output on the actual experiment computer.

## GitHub

Source and tests are maintained at [jlee2002/Stroop-color-word-test](https://github.com/jlee2002/Stroop-color-word-test). Keep participant results in the ignored `results/` directory.
