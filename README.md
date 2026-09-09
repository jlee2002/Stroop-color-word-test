# test1

A Python + Pygame experiment prototype with separate participant and observer windows.

The repository's original [experiment overview](docs/experiment-overview.md) describes the Snowball Lab study context.

## Trial rules

- **INK:** a color word is printed in a different color. Choose the ink color, ignoring the word.
- **WORD:** the word and ink color match. Choose the color named by the word.

The session lasts **two minutes**, starting when the observer presses Space or Start. Both windows show the same countdown from **02:00** to **00:00**. The clock continues during error pauses and between trials. At zero, the task ends automatically and no further answers are accepted.

The conditions are shuffled in batches of 40, with equal counts (one extra INK trial when a batch has an odd size). New batches are generated as needed until time expires; 40 is not a session limit. The number of completed trials and the condition counts depend on response speed and pauses. Consecutive trials may use the same condition. Colors are sampled independently; color frequencies are not counterbalanced. Each trial shows its instruction. This implements the two conditions described above, not a full factorial Stroop protocol.

Participants respond **aloud**; their screen has no answer buttons or scoring shortcuts. The observer sees the current expected answer and clicks **Correct** or **Incorrect**, or presses **Right arrow = Correct** / **Left arrow = Incorrect** with the observer window focused. Correct answers show green **Correct** feedback for 600 ms before advancing. Incorrect answers and timeouts show **Incorrect**, beep, and pause trial progression until the observer presses **Space** with the observer window focused. The failed trial is recorded once; Space moves to the next trial. The overall session countdown continues during pauses.

After completion, the observer can click **Restart with shuffle**. This resets scores and the timer, generates a fresh shuffled batch, and returns to the ready screen. The previous answer limit is retained and can be edited before pressing Start or Space again.

### Optional answer time limit

Before starting, click the observer's **Answer limit (seconds)** field, type a positive number such as `2` or `2.5`, and click **Apply** or press **Enter**. Leave the field blank and apply it to disable the limit. Pressing Space or clicking Start while editing also applies the value before starting. The setting is fixed once the session starts.

The limit starts when each stimulus first appears. Entering `2` means exactly **two seconds**, not milliseconds. The observer must score the spoken answer before that deadline; the app does not detect speech. An unanswered trial that reaches the limit is marked incorrect, beeps, and pauses until the observer presses Space. A late answer cannot replace a timeout. The observer sees **Time limit exceeded**. The two-minute session countdown continues throughout; session completion takes precedence if both deadlines are reached together.

## Install and run

Install Python 3.10–3.12, then run from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe stroop.py
```

Both windows open on display 0 by default for setup on a single monitor. Move them apart using their title bars. Click **Test beep**, then press **Space** to start. The participant says their answer aloud. The observer listens, compares it with the displayed expected answer, and clicks Correct or Incorrect. Only the observer window accepts Space for starting or resuming. Space is not a system-wide shortcut; keep the observer window focused while scoring.

For two monitors, set Windows displays to **Extend**, then run:

```powershell
.\.venv\Scripts\python.exe stroop.py --participant-display 1 --observer-display 0 --fullscreen --trials 40
```

Display indices are zero-based. Swap 0 and 1 if necessary. `--fullscreen` opens both participant and observer windows fullscreen on their assigned displays. Omit it to start with movable windows. Click the title-bar **maximize** button in either window to fill the screen, and use **Restore Down** to return to its previous size. Both windows also support resizing. **F11** remains available for fullscreen without the title bar. Use separate monitors to see both fullscreen windows at once. Pygame runs each window in a separate process, with local queues connecting them. No server or network connection is required.

Use `--seed 123` to reproduce a trial order. The default duration is 120 seconds; `--duration 10` runs a short setup check. `--trials` controls the shuffled batch size, not the session length. Press **Esc** or close either window to stop early. After completion, click Restart with shuffle to prepare another session, or close either window to exit. Sound uses the computer's default audio output, not a monitor-specific output. The observer displays an audio-unavailable notice if initialization fails; test the beep before a session.

## Results

Each run creates a timestamped CSV in `results/`, flushed after each response or timeout. Columns include trial number, condition, word, ink, expected answer and observer judgment, correctness, response time in milliseconds, UTC response/timeout timestamp, random seed, session number, `timed_out`, and `response_limit_seconds`. Restarts append to the same CSV with an incremented `session` number and a fresh seed; previous results are preserved. Observer judgments use response `OBSERVER_CORRECT` or `OBSERVER_INCORRECT`; the actual spoken word is not transcribed. Timeouts have response `TIMEOUT`, correctness `False`, and `timed_out=True`. Their response time is the elapsed time when the program detects the timeout, normally within one frame of the limit. An unfinished trial at session end or manual exit is not recorded. Files remain local and are excluded from Git by `.gitignore`.

Timing starts immediately after Pygame flips the first stimulus frame. Response time measures the observer scoring click, including observer reaction time. These are software response times, not calibrated display-onset measurements. This prototype does not measure blood pressure or establish that a session increases it. The intended experimental protocol and any BP measurement procedure are separate from the app.

## Development

```powershell
python -m unittest discover -s tests -v
```

Before collecting data, check both physical monitors, observer input focus, the audible beep, error pause/resume, and CSV output on the actual experiment computer.

## GitHub

Source and tests are maintained at [jlee2002/Stroop-color-word-test](https://github.com/jlee2002/Stroop-color-word-test). Keep participant results in the ignored `results/` directory.
