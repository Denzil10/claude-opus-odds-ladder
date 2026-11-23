"""Replay a finished ladder.py game on the referee screen, from its log, faster than it was played.
  python replay.py <rN.jsonl> [seconds per ply, default 0.35] [first ply to show, default 0] [last ply, default all]
Same lines ladder.py printed live (move, real think time, the side's comment, illegal tries), plus a banner
saying it is a sped-up replay. Plies before <first ply> are applied silently. Recorded with vhs.
"""
import json, sys, textwrap, time
import chess

B, R, D, X = "\033[1m", "\033[31m", "\033[2m", "\033[0m"
NAME = {"Black": "OPUS 5.5", "White": "HAIKU 5.5"}
COL = {"Black": "\033[38;5;117m", "White": "\033[38;5;150m"}
rows = [json.loads(l) for l in open(sys.argv[1])]
step = float(sys.argv[2]) if len(sys.argv) > 2 else 0.35
first = int(sys.argv[3]) if len(sys.argv) > 3 else 0
last_ply = int(sys.argv[4]) if len(sys.argv) > 4 else 10**6
head = rows[0]


def show(board):
    print()
    for i, row in enumerate(str(board.unicode(invert_color=True, empty_square="·")).splitlines()):
        print(f"   {D}{8 - i}{X}  " + " ".join(row.split()))
    print(f"      {D}a b c d e f g h{X}\n")


def out(*a):
    if board.ply() >= first:
        print(*a)


print(f"{B}RUNG {head['rung']}: OPUS GIVES {head['label'].upper()}{X}")
print(f"{B}{COL['White']}HAIKU 5.5{X}{B} (White) vs {COL['Black']}OPUS 5.5{X}{B} (Black){X}")
print(f"{D}no tools, no code · replay of the real game log, sped up{X}")
board = chess.Board(head["start"])
if first == 0:
    show(board); time.sleep(1.0)
last = None
for r in rows[1:]:
    if board.ply() >= last_ply:
        break  # stop with the quote of ply <last ply> as the last line on screen (for a still)
    if "result" in r:
        ill = r["illegal"]
        print(f"\n {B}RESULT {r['result']}{X}  {r['why']}  · moves: {r['moves']}")
        print(f" {D}illegal tries: Haiku {ill['haiku']}, Opus {ill['opus']}{X}")
    elif "reply" in r:
        last = r
    elif "illegal" in r:
        side = "White" if board.turn else "Black"; n = board.fullmove_number; dots = "." if board.turn else "..."
        out(f" {R}{B}ILLEGAL{X}  {COL[side]}{NAME[side]}{X} {n}{dots} {r['illegal'] or '(no move)'}  {D}try {r['tries']}/3{X}")
        if board.ply() >= first: time.sleep(step * 2)
    elif "move" in r:
        side = "White" if board.turn else "Black"
        lines = [l.strip() for l in last["reply"].strip().splitlines() if l.strip()]
        comment = lines[0] if len(lines) > 1 else ""
        mv = chess.Move.from_uci(r["move"]); n = board.fullmove_number; dots = "." if board.turn else "..."
        out(f" {COL[side]}{B}{NAME[side]}{X} {n}{dots} {board.san(mv)}  {D}{last['secs']}s{X}")
        if comment:
            for ln in textwrap.wrap(f'"{comment}"', 46):  # word wrap: the 1080px vhs terminal at FontSize 30 fits ~52 columns
                out(f"   {D}{ln}{X}")
        board.push(mv)
        if board.ply() >= last_ply:
            break
        if board.ply() > first and (board.ply() % 2 == 0 or board.is_game_over()):
            show(board)
        if board.ply() > first: time.sleep(step)
sys.stdout.flush(); time.sleep(4)
