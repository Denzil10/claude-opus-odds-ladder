# Claude Opus gives odds to Claude Haiku (chess, no tools)

Seven games, 2026-11-24. Opus 5.5 (Black) starts without more pieces each game Haiku 5.5 (White) fails to win; the ladder stops at the first Haiku win (step 6: Opus has only knights and pawns, Haiku mates on move 74). Each move is a fresh `claude -p --tools ""` call.

- `index.html`: every move and comment, Stockfish loss per move (live at https://denzil10.github.io/claude-opus-odds-ladder/)
- `ladder.py`: referee (python-chess), rules in its docstring; `run_ladder.sh`: runs the steps in order; `analyze.py`: Stockfish review; `replay.py`: the sped-up referee screen used in the video
- `games/`: full logs (every prompt and reply), PGNs, reviews
