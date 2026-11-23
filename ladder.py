"""Odds ladder: Claude Haiku 5.5 (White) vs Claude Opus 5.5 (Black), Opus starts with pieces removed.
Rules fixed before the first game (2026-11-24):
  - One game per rung, in order. Rung 0 no odds; 1 knight (b8); 2 rook (a8); 3 queen (d8);
    4 queen + rook (d8, a8); 5 queen + both rooks (d8, a8, h8); 6 queen + both rooks + both bishops.
  - The ladder stops at the first rung Haiku wins. A draw is not a win; the ladder goes on.
  - Haiku is always White (moves first). Both sides are told the odds in the system prompt.
  - Each move is a fresh `claude -p` call with every tool disabled, no session, no settings or MCP.
    The prompt is the ep07/ep09 one: move list, FEN, text diagram. 3 illegal tries in a row = forfeit.
  - python-chess is the referee. Move 150 = draw.
Usage: python ladder.py <rung> <out dir>    log: <out>/r<rung>.jsonl, PGN r<rung>.pgn
"""
import json, re, subprocess, sys, time, pathlib, datetime
import chess, chess.pgn

RUNGS = {0: ("no odds", []), 1: ("a knight", ["b8"]), 2: ("a rook", ["a8"]), 3: ("the queen", ["d8"]),
         4: ("queen + rook", ["d8", "a8"]), 5: ("queen + both rooks", ["d8", "a8", "h8"]),
         6: ("queen, rooks + bishops", ["d8", "a8", "h8", "c8", "f8"])}
rung, out = int(sys.argv[1]), pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
label, gone = RUNGS[rung]
LOG = open(out / f"r{rung}.jsonl", "a")
MODEL = {"haiku": "claude-haiku-5-5", "opus": "claude-opus-5-5"}
NAME = {"haiku": "HAIKU 5.5", "opus": "OPUS 5.5"}
COL = {"opus": "\033[38;5;117m", "haiku": "\033[38;5;150m"}
B, R, D, X = "\033[1m", "\033[31m", "\033[2m", "\033[0m"

start = chess.Board()
for sq in gone:
    start.remove_piece_at(chess.parse_square(sq))
start.castling_rights = start.clean_castling_rights()
START = start.fen()
names = {chess.KNIGHT: "knight", chess.ROOK: "rook", chess.QUEEN: "queen", chess.BISHOP: "bishop"}
gone_txt = ", ".join(f"the {names[chess.Board().piece_at(chess.parse_square(s)).piece_type]} on {s}" for s in gone)


def system(side):
    odds = ""
    if gone and side == "Black":
        odds = f"This is an odds game: you started without {gone_txt}. "
    elif gone:
        odds = f"This is an odds game: your opponent started without {gone_txt}. "
    return (f"You are playing a game of chess as {side} against another AI. {odds}You have no tools and no code. "
            "Reply in exactly two lines: line 1, a short comment on your move under 12 words; line 2, only your move in SAN.")


def log(**kw):
    kw["t"] = datetime.datetime.now().isoformat(timespec="seconds"); LOG.write(json.dumps(kw) + "\n"); LOG.flush()


def movelist(board):
    b = chess.Board(START); parts = []
    for i, m in enumerate(board.move_stack):
        if i % 2 == 0: parts.append(f"{i // 2 + 1}.")
        parts.append(b.san(m)); b.push(m)
    return " ".join(parts) or "(none, game start)"


def ask(model, board, misses):
    side = "White" if board.turn == chess.WHITE else "Black"
    p = (f"Moves so far: {movelist(board)}\nPosition (FEN): {board.fen()}\n"
         f"Board (White at the bottom, uppercase = White):\n{board}\n")
    for m in misses:
        p += f"You tried {m}, which is not a legal move in this position.\n"
    p += f"You are {side}. Your move."
    t0 = time.time()
    r = subprocess.run(["claude", "-p", "--model", model, "--tools", "", "--no-session-persistence",
                        "--setting-sources", "", "--strict-mcp-config", "--output-format", "json",
                        "--system-prompt", system(side), p], capture_output=True, text=True, timeout=900)
    try:
        j = json.loads(r.stdout); text = j.get("result", ""); used = ",".join(j.get("modelUsage", {}).keys())
    except json.JSONDecodeError:
        text, used = r.stdout + r.stderr, "?"
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    comment = lines[0] if len(lines) > 1 else ""
    raw = lines[-1] if lines else ""
    san = re.sub(r"^\d+\.(\.\.)?\s*", "", raw).strip(" .*`")
    secs = round(time.time() - t0, 1)
    log(ply=board.ply(), side=side, model=model, prompt=p, system=system(side), reply=text, used=used, secs=secs)
    return comment, san, secs


def show(board):
    print()
    for i, row in enumerate(str(board.unicode(invert_color=True, empty_square="·")).splitlines()):
        print(f"   {D}{8 - i}{X}  " + " ".join(row.split()))
    print(f"      {D}a b c d e f g h{X}\n")


board = chess.Board(START); illegal = {"haiku": 0, "opus": 0}; forfeit = None
print(f"{B}RUNG {rung}: OPUS GIVES {label.upper()}{X}")
print(f"{B}{COL['haiku']}HAIKU 5.5{X}{B} (White) vs {COL['opus']}OPUS 5.5{X}{B} (Black){X}  {D}no tools, no code{X}")
log(rung=rung, label=label, gone=gone, start=START)
show(board)
while not board.is_game_over(claim_draw=True) and board.fullmove_number <= 150:
    who = "haiku" if board.turn == chess.WHITE else "opus"
    n = board.fullmove_number; dots = "." if board.turn == chess.WHITE else "..."
    misses = []
    while True:
        comment, san, secs = ask(MODEL[who], board, misses)
        try:
            mv = board.parse_san(san)
        except ValueError:
            mv = None
        if mv:
            break
        illegal[who] += 1; misses.append(san or "(no move)")
        print(f" {R}{B}ILLEGAL{X}  {COL[who]}{NAME[who]}{X} {n}{dots} {san}   {D}try {len(misses)}/3{X}")
        log(ply=board.ply(), side=who, illegal=san, tries=len(misses))
        if len(misses) == 3:
            forfeit = who; break
    if forfeit:
        print(f"\n {R}{B}THREE ILLEGAL TRIES. {NAME[forfeit]} FORFEITS.{X}"); break
    print(f" {COL[who]}{B}{NAME[who]}{X}  {n}{dots} {board.san(mv)}   {D}{secs}s{X}   \"{comment}\"")
    board.push(mv); log(ply=board.ply(), move=mv.uci(), fen=board.fen())
    if board.ply() % 2 == 0 or board.is_game_over(): show(board)
if forfeit:
    result = "0-1" if forfeit == "haiku" else "1-0"; why = f"FORFEIT ({NAME[forfeit]}, 3 illegal tries)"
elif board.is_game_over(claim_draw=True):
    result = board.result(claim_draw=True); why = board.outcome(claim_draw=True).termination.name
else:
    result, why = "1/2-1/2", "MOVE 150 CAP"
print(f"\n {B}RESULT {result}{X}  {why}   moves: {board.fullmove_number}   illegal: Haiku {illegal['haiku']}, Opus {illegal['opus']}")
log(result=result, why=why, illegal=illegal, moves=board.fullmove_number,  # moves = number AFTER the last move (one high when Black moved last)
    rung=rung, label=label, start=START)
pg = chess.pgn.Game.from_board(board)
pg.headers.update({"Event": f"Odds ladder rung {rung}: Opus gives {label}", "White": "Claude Haiku 5.5",
                   "Black": "Claude Opus 5.5", "Result": result})
(out / f"r{rung}.pgn").write_text(str(pg) + "\n")
