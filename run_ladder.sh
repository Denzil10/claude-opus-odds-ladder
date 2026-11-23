#!/bin/bash
# Runs rungs in order; stops after the first rung White (Haiku) wins.
cd "$(dirname "$0")"
PY=../../../venv/bin/python
for r in 0 1 2 3 4 5 6; do
  [ -f games/r$r.pgn ] && { grep -q 'Result "1-0"' games/r$r.pgn && break; continue; }
  $PY ladder.py $r games > games/r$r.out 2>&1
  grep -q 'Result "1-0"' games/r$r.pgn && break
done
echo LADDER DONE
