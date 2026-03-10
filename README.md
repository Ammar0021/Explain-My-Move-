# ♟️ Explain My Move

> A chess analysis tool that explains every move in plain English — powered by Stockfish 16, built with Python and Tkinter.

**OCR A-Level Computer Science NEA · Component 03/04 · Author: Ammar · v1.3.1**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Stockfish](https://img.shields.io/badge/Engine-Stockfish%2016-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=flat-square)
![License](https://img.shields.io/badge/License-NEA%20Project-orange?style=flat-square)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Quick Start](#-quick-start)
- [Building the .exe](#%EF%B8%8F-building-the-exe)
- [Using the Application](#-using-the-application)
  - [Analyse a Position (FEN mode)](#analyse-a-position-fen-mode)
  - [PGN Game Review](#pgn-game-review)
- [Move Classifications](#-move-classifications)
- [Explanation Rules](#-explanation-rules)
- [Modes & Settings](#%EF%B8%8F-modes--settings)
- [Exporting](#-exporting)
- [File Structure](#-file-structure)
- [Running Tests](#-running-tests)
- [Troubleshooting](#-troubleshooting)

---

## 🔍 Overview

**Explain My Move** is a desktop chess analysis application that combines Stockfish 16 with a custom 18-rule natural language engine to explain *why* a move is good or bad — in plain English, pitched at the player's level.

Instead of showing raw centipawn numbers, it translates engine output into human-readable concepts:

> *"This move creates a fork, attacking the queen and rook simultaneously."*
>
> *"This captures a completely undefended piece."*
>
> *"This move develops a minor piece towards the centre."*

### ✨ Features at a Glance

| | Feature | Description |
|---|---|---|
| ♟️ | **FEN Analysis** | Paste any FEN string to analyse a position — get the top 3 engine moves explained |
| 📋 | **PGN Game Review** | Review every move in a complete game, chess.com-style |
| 🧠 | **18 Explanation Rules** | Checks, forks, pins, skewers, discovered attacks, outposts, batteries, and more |
| 🏷️ | **Move Classifications** | Every move graded: Brilliant / Best / Good / Inaccuracy / Mistake / Blunder |
| 📤 | **Annotated PGN Export** | Export games with embedded comments and NAG symbols (`!!`, `?`, `??`) |
| 🎓 | **Two Skill Modes** | Beginner (plain English) vs. Intermediate (centipawn detail) |
| 🌙 | **Dark & Light Themes** | Full re-theme via View → Dark Mode (`Ctrl+D`) |
| 📊 | **JSON Output Panel** | Structured analysis data, collapsible and copyable |
| 📦 | **Portable .exe** | Single executable — Stockfish bundled, nothing to install on the target machine |

---

## ⚡ Quick Start

> **Already have `ExplainMyMove.exe`?** Just double-click it — Stockfish is bundled inside. Skip everything below.

To build the exe yourself, you need:

1. **Python 3.10+** from [python.org](https://www.python.org/downloads/) *(tick "Add to PATH" during install)*
2. **python-chess and PyInstaller:**
   ```bat
   pip install python-chess pyinstaller
   ```
3. **Stockfish** from [stockfishchess.org/download](https://stockfishchess.org/download/), placed at:
   ```
   stockfish\stockfish-windows-x86-64-avx2.exe
   ```
4. **Build, then run:**
   ```bat
   build_exe.bat
   dist\ExplainMyMove.exe
   ```

> ⚠️ **Do not run `explain_my_move.py` directly.** The application must be compiled first using `build_exe.bat` — Stockfish is resolved at runtime from inside the bundled executable. Always launch `dist\ExplainMyMove.exe`.

---

## 🛠️ Building the .exe

`build_exe.bat` uses PyInstaller to bundle Python, python-chess, and Stockfish into a single self-contained `ExplainMyMove.exe`.

### Prerequisites

```bat
pip install pyinstaller python-chess
```

Ensure all 7 source files are in the same folder as `build_exe.bat`, and that Stockfish is at `stockfish\stockfish-windows-x86-64-avx2.exe`.

### Run the Build

```bat
build_exe.bat
```

✅ Output: `dist\ExplainMyMove.exe`

Copy this single file to any Windows machine and run it. No Python, no Stockfish, no extra files required.

### What the script does

1. Verifies Python, PyInstaller, and python-chess are installed
2. Checks all 7 required `.py` source files are present
3. Runs PyInstaller with `--onefile --windowed`, bundling Stockfish via `--add-data`
4. Outputs `dist\ExplainMyMove.exe` — fully portable

> 📝 `test_suite.py` is intentionally **excluded** from the exe. Run it separately from your dev environment.

### System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 64-bit | Windows 11 |
| Python | 3.10 | 3.12 |
| RAM | 4 GB | 8 GB |
| CPU | AVX2 support | Any modern Intel/AMD (2013+) |

> ⚠️ **AVX2 note:** The bundled Stockfish binary requires AVX2 CPU support. If you get an "illegal instruction" crash, download the legacy Stockfish build from [stockfishchess.org](https://stockfishchess.org/download/) instead.

---

## 🖥️ Using the Application

### Interface Layout

The window is split into two columns:

- **Left — Chess Board:** Interactive 480×480 px board with rank/file labels and a live evaluation bar on the left edge
- **Right — Analysis Panel:** Format selector (FEN / PGN radio buttons), input box, the **▶ Analyse Position** button, ranked move buttons (Top 1/2/3), explanation card, and a collapsible JSON output panel

Below the board sit three persistent buttons: **Flip Board**, **Copy FEN**, and **Export PGN**. During an active game review, **← Prev** and **→ Next** navigation buttons also appear here (or use the left/right arrow keys).

### Menu Bar

| Menu | Item | Shortcut | Action |
|---|---|---|---|
| **File** | Copy FEN | — | Copy the current board position as a FEN string |
| **File** | Export PGN | — | Copy the annotated PGN to clipboard |
| **File** | Copy JSON | — | Copy the last analysis result as JSON |
| **File** | Exit | — | Close the application |
| **View** | Fullscreen | `F11` | Toggle fullscreen |
| **View** | Flip Board | `Ctrl+F` | Rotate the board 180° |
| **View** | Dark Mode | `Ctrl+D` | Switch between dark navy and light themes |
| **Help** | About | — | Show project info and version |

---

### Analyse a Position (FEN mode)

1. **Select FEN** using the radio buttons at the top of the input card *(FEN is selected by default)*

2. **Paste a FEN string** into the input box, or leave it blank to use the starting position:
   ```
   rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
   ```

3. **Click ▶ Analyse Position** (or press `Enter`) — Stockfish analyses the position and returns the top 3 candidate moves

4. **Click a ranked move button** (Top 1 / Top 2 / Top 3) to view its explanation. The board highlights the move: 🟡 yellow = source square, 🟢 green = destination

5. **Read the explanation card** — shows the move in algebraic notation, the evaluation score (e.g. `+0.45`), and a plain-English explanation. In Intermediate mode, the specific tactical rules that fired are also shown.

> 💡 The evaluation bar on the left edge of the board updates after each analysis. White advantage fills from the bottom; Black advantage fills from the top.

---

### PGN Game Review

1. **Select PGN** using the radio buttons at the top of the input card

2. **Paste a full PGN** into the input box. You can get PGNs from:
   - **Lichess:** Game page → Share & export → Download PGN
   - **Chess.com:** Analysis → Export PGN

3. **Click ▶ Analyse Position** — the engine analyses every move in a background thread. For a ~40-move game at depth 12, expect 20–60 seconds.

4. **Navigate with ← Prev / → Next** (or the left/right arrow keys) — step through every move. The board and explanation card update for each one.

5. **Read per-move detail** — each move shows:
   - Classification badge (e.g. `??` Blunder, `?!` Inaccuracy)
   - Centipawn loss *(Intermediate mode only)*
   - Plain-English explanation of the move played
   - For bad moves: what the engine recommends instead and why

6. **Export** via **File → Export PGN** to copy the annotated PGN to your clipboard — it loads correctly in Lichess, Chess.com, ChessBase, and Arena.

> 💡 Bad-move analysis is fully integrated into the game review. Every move that exceeds the centipawn threshold automatically receives an explanation of what went wrong — no separate step needed.

---

## 🏷️ Move Classifications

Every move is compared against Stockfish's best move. The centipawn loss determines the grade:

| Symbol | Grade | Centipawn Loss | Meaning |
|---|---|---|---|
| `!!` | **Brilliant** | 0 cp · sacrifice | A rare, exceptional move |
| `★` | **Best** | 0 – 10 cp | Engine's top choice |
| `✓` | **Good** | 10 – 25 cp | A solid, near-optimal move |
| `?!` | **Inaccuracy** | 25 – 100 cp | Slightly inferior |
| `?` | **Mistake** | 100 – 300 cp | A significant error |
| `??` | **Blunder** | > 300 cp | A severe, game-changing error |

> **cp = centipawns.** 100 cp ≈ 1 pawn of advantage. A blunder (> 300 cp) means the move played was roughly 3+ pawns worse than the best available.

---

## 🧠 Explanation Rules

The `ExplanationEngine` checks up to 18 rules in priority order to generate a plain-English reason for each move:

| # | Rule | What it detects |
|---|---|---|
| 1 | `check` | Move puts the opponent in check |
| 2 | `checkmate_threat` | Creates a forced mate threat |
| 3 | `hanging_capture` | Captures a completely undefended piece |
| 4 | `fork` | Piece simultaneously attacks two or more opponent pieces |
| 5 | `discovered_attack` | Moving a piece reveals a hidden attack by a friendly slider |
| 6 | `pin` | Attacks a piece that cannot safely move |
| 7 | `skewer` | Attacks a high-value piece with a lesser piece hiding behind it |
| 8 | `pawn_promotion` | Pawn advances to the 7th rank (one step from queening) |
| 9 | `captures_material` | Captures any opponent piece |
| 10 | `piece_development` | Develops a knight or bishop from its starting square |
| 11 | `centre_control` | Pawn or piece moves to or attacks a central square (d4/e4/d5/e5) |
| 12 | `king_safety` | Castles kingside or queenside |
| 13 | `open_file_rook` | Rook moves to a file with no pawns |
| 14 | `passed_pawn` | Creates or advances a passed pawn |
| 15 | `knight_outpost` | Knight reaches an advanced square unreachable by opponent pawns |
| 16 | `battery_formation` | Two heavy pieces align on the same file or rank |
| 17 | `trades_equal` | Makes an equal material exchange |
| 18 | `general_best` | Fallback: engine's top choice with no specific tactical reason found |

---

## ⚙️ Modes & Settings

### Skill Modes

Select your mode using the radio buttons in the right panel of the application:

| Mode | Explanation Style | Word Limit |
|---|---|---|
| 🟢 **Beginner** | Plain English, no centipawn values or jargon | 30 words |
| 🔵 **Intermediate** | Includes cp loss, classification label, and all matching rule names | 40 words |

### Engine Depth

A depth slider sits directly in the right panel beneath the mode selector — drag it to adjust Stockfish's search depth on the fly (range: 1–20, default: 12).

> 💡 **For quick examiner testing:** set the depth slider to **8** for fast results with no meaningful loss in explanation quality.

### Other Settings

These are configured in `engine_config.py` — there is no in-app settings window:

| Setting | Default | Range | Effect |
|---|---|---|---|
| Analysis Timeout | 10 s | 1 – 30 s | Max wait before fallback heuristic kicks in |
| Multi-PV Count | 3 | 1 – 5 | Number of ranked alternative moves shown |
| Bad Move Threshold | 100 cp | 50 – 500 cp | cp drop that triggers a bad-move explanation |

---

## 📤 Exporting

### Annotated PGN

After a PGN Game Review, use **File → Export PGN**. The PGN is copied to your clipboard and contains:

- Standard PGN headers (`Event`, `White`, `Black`, `Date`, `Annotator`)
- NAG symbols after each move: `$1` !, `$2` ?, `$4` ??, `$6` ?!
- Text comments in curly braces `{ … }` with plain-English explanations
- Centipawn loss figures *(Intermediate mode only)*

NAG symbols follow [PGN standard §8.2.4](https://www.chessclub.com/help/PGN-spec) and are recognised by Lichess, Chess.com, ChessBase, and Arena.

### Copy FEN

Click **Copy FEN** below the board (or **File → Copy FEN**) to copy the current board position as a FEN string — paste it into any other chess tool to continue analysis there.

### JSON Output

Click **▶ JSON OUTPUT** to expand the collapsible panel on the right. The full analysis result is displayed and can be copied via the **Copy** button or **File → Copy JSON**. Schema fields:

```
best_move_uci    best_move_san    score_centipawns    score_display
explanation      mode             depth_used          timeout_flag
analysis_time_ms ranked_moves     word_count          schema_valid
```

---

## 📁 File Structure

```
explain-my-move/
│
├── explain_my_move.py      # 🖥️  GUI layer — board rendering, input, event handling, review nav
├── engine_interface.py     # ⚙️  ChessEngineInterface, MoveEvaluator, BadMoveAnalyser
├── explanation_engine.py   # 🧠  Rule + ExplanationEngine — 18 natural language rules (v1.4)
├── engine_config.py        # 🔧  ConfigManager, get_stockfish_path()
├── output_formatter.py     # 📝  OutputFormatter — text, JSON, and PGN formatting
├── game_statistics.py      # 📊  StatisticsCalculator — accuracy, blunder/mistake rates
├── pgn_annotator.py        # 📋  PGNAnnotator — annotated PGN with NAG symbols
│
├── test_suite.py           # 🧪  Formal test runner T01–T42 (dev only — not in .exe)
├── build_exe.bat           # 📦  PyInstaller build script → dist\ExplainMyMove.exe
├── total_lines.py          # 🔢  Dev utility: counts lines of code (requires rich)
│
└── stockfish\
    └── stockfish-windows-x86-64-avx2.exe   # ⚠️  Not in repo — download separately
```

---

## 🧪 Running Tests

> `test_suite.py` is a **development-only** tool — it is not included in the compiled `.exe`. Tests T40–T42 require Stockfish to be configured in `engine_config.py`.

```bash
python test_suite.py
```

### Test Categories

| Range | Category | What is tested |
|---|---|---|
| T01 – T08 | `ConfigManager` | Defaults, validation, boundary conditions, atomic updates |
| T09 – T16 | `ExplanationEngine` | All 18 rules, word limits, mode switching, priority order |
| T17 – T22 | `OutputFormatter` (text) | Score formatting, SAN notation, beginner/intermediate output |
| T23 – T25 | `OutputFormatter` (JSON) | Schema validity, required fields, type checking |
| T26 – T32 | `MoveEvaluator` | Move ranking, multi-PV, timeout fallback, FEN parsing |
| T33 – T39 | `BadMoveAnalyser` | Threshold detection, explanation generation, best-move suggestion |
| T40 – T42 | Integration | End-to-end: FEN → engine → explanation → JSON |

Expected output: `42 / 42 passed`

---

## 🔧 Troubleshooting

| ❌ Problem | ✅ Fix |
|---|---|
| `Python not found on PATH` | Reinstall Python and tick "Add to PATH", or add manually via System Environment Variables |
| `PyInstaller not installed` | `pip install pyinstaller` |
| `python-chess not installed` | `pip install python-chess` |
| Stockfish not found at build time | Ensure `stockfish\stockfish-windows-x86-64-avx2.exe` exists before running `build_exe.bat` |
| `Illegal instruction` crash on launch | Your CPU may not support AVX2 — download the legacy Stockfish build from stockfishchess.org |
| Antivirus blocking the build | Temporarily disable real-time protection; add the project folder to AV exclusions |
| Exe crashes with no error message | Remove `--windowed` from `build_exe.bat` temporarily to reveal the error in the console |
| Engine timing out on every move | Lower the depth slider inside the app, or reduce the timeout in `engine_config.py` |

---

*♟️ Explain My Move v1.3.1 · OCR A-Level Computer Science NEA · Author: Ammar*
