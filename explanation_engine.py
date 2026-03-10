
# explanation_engine.py  —  Explain My Move  v1.4
# Author: Ammar
# OCR A-Level Computer Science NEA — Component 03/04
#
# Contains:
#   Rule              (Design Class 4)
#   ExplanationEngine (Design Class 3)
#   Tactical helpers  (_is_hanging, _creates_fork, _creates_pin, …)
#
# Changes from v1.3 → v1.4:
#   Four new tactical detection helpers added (rules 15–18):
#
#   _is_discovered_attack (Rule 15 — priority 3.5, between fork and pin)
#       Detects when moving a piece reveals an attack by a friendly slider
#       (rook, bishop, or queen) on an opponent piece behind the moving piece.
#       This is one of the most powerful tactical motifs in chess.
#
#   _is_skewer (Rule 16 — priority 4.5, between pin and hanging_capture)
#       Detects when a sliding piece attacks a high-value opponent piece with a
#       lesser piece behind it. The more valuable piece must move, exposing the
#       lesser piece to capture. Inverse of a pin.
#
#   _is_knight_outpost (Rule 17 — priority 12.5, after open-file rook)
#       Detects when a knight lands on an advanced square that cannot be attacked
#       by any opponent pawn and is supported by a friendly pawn. Outpost knights
#       are a classic positional advantage concept.
#
#   _is_battery_formation (Rule 18 — priority 13.5, after passed pawn)
#       Detects when two friendly heavy pieces (rook+rook, queen+rook, or
#       queen+queen) align on the same file or rank with nothing between them,
#       forming a battery — doubling the firepower along that line.
#
#   Total rules: 14 (v1.3) → 18 (v1.4)
#
# All existing v1.3 behaviour is preserved unchanged.
# Rules are re-sorted on construction so new priorities slot in correctly.


import chess



# WORD LIMITS


WORD_LIMIT = {
    "Beginner":     30,
    "Intermediate": 40,
}



# PIECE VALUES (local — avoids circular import with engine_interface)

# Used only by _is_skewer for comparing relative piece values.
# Intentionally simplified to ordinal values (not full centipawn values)
# since the comparison is qualitative: "is piece A more valuable than B?"

_PIECE_VALUE_ORDINAL = {
    chess.PAWN:   1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK:   5,
    chess.QUEEN:  9,
    chess.KING:   99,   # king is infinitely valuable; won't appear as skewer target
}



# EXISTING TACTICAL DETECTION HELPERS (v1.3 — unchanged)


def _post_move_check(board: chess.Board, move: chess.Move) -> bool:
    """Returns True if pushing move results in the opponent being in check."""
    test = board.copy()
    test.push(move)
    return test.is_check()


def _is_hanging(board: chess.Board, square: int) -> bool:
    """
    Returns True if the piece on `square` is attacked by the side to move
    and completely undefended by its own side.

    Uses board.attackers() for both attack and defence counts.
    An undefended attacked piece is 'free to take'.
    """
    piece = board.piece_at(square)
    if piece is None:
        return False
    attackers = board.attackers(board.turn, square)
    defenders = board.attackers(not board.turn, square)
    return len(attackers) > 0 and len(defenders) == 0


def _creates_fork(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if, after the move, the moved piece simultaneously attacks
    two or more opponent pieces — the definition of a fork.

    Limitation: does not verify whether those pieces are adequately defended.
    """
    test_board = board.copy()
    test_board.push(move)
    opponent_colour  = test_board.turn
    attacked_squares = test_board.attacks(move.to_square)
    pieces_attacked  = sum(
        1 for sq in attacked_squares
        if (p := test_board.piece_at(sq)) is not None
        and p.color == opponent_colour
    )
    return pieces_attacked >= 2


def _creates_pin(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if a sliding piece (bishop / rook / queen) creates an
    absolute pin on an opponent piece after the move.

    Uses python-chess board.pin(colour, square) — if the ray is not
    chess.BB_ALL, the piece is absolutely pinned.

    Limitation: absolute pins only; relative pins not detected.
    """
    piece = board.piece_at(move.from_square)
    if piece is None:
        return False
    if piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
        return False

    test_board = board.copy()
    test_board.push(move)
    opponent = not board.turn

    if test_board.king(opponent) is None:
        return False

    for sq in chess.SQUARES:
        p = test_board.piece_at(sq)
        if p and p.color == opponent and p.piece_type != chess.KING:
            if test_board.pin(opponent, sq) != chess.BB_ALL:
                return True
    return False


def _threatens_checkmate(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if the move delivers checkmate, or if it puts the opponent
    in check with ≤2 legal replies (a near-forced mate heuristic).
    """
    test = board.copy()
    test.push(move)
    if test.is_checkmate():
        return True
    if test.is_check() and len(list(test.legal_moves)) <= 2:
        return True
    return False


def _is_open_file_rook(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if a rook moves to a file with zero pawns of either colour.
    An open file gives the rook maximum mobility along that column.
    """
    if board.piece_at(move.from_square) is None:
        return False
    if board.piece_at(move.from_square).piece_type != chess.ROOK:
        return False
    dest_file = chess.square_file(move.to_square)
    for rank in range(8):
        p = board.piece_at(chess.square(dest_file, rank))
        if p and p.piece_type == chess.PAWN:
            return False
    return True


def _is_semi_open_file_rook(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if a rook moves to a file with only opponent pawns (no
    friendly pawns). Pressuring an opponent's pawn directly is advantageous.
    """
    p = board.piece_at(move.from_square)
    if p is None or p.piece_type != chess.ROOK:
        return False
    our_colour   = board.turn
    dest_file    = chess.square_file(move.to_square)
    has_opp_pawn = False
    for rank in range(8):
        sq  = chess.square(dest_file, rank)
        pp  = board.piece_at(sq)
        if pp and pp.piece_type == chess.PAWN:
            if pp.color == our_colour:
                return False
            has_opp_pawn = True
    return has_opp_pawn


def _is_passed_pawn_advance(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if a pawn move results in a passed pawn — no opponent pawns
    on the same or adjacent files ahead of it — and the pawn has advanced past
    the 4th rank (early-game passed pawns are less educationally relevant).
    """
    p = board.piece_at(move.from_square)
    if p is None or p.piece_type != chess.PAWN:
        return False

    our_colour = board.turn
    dest_file  = chess.square_file(move.to_square)
    dest_rank  = chess.square_rank(move.to_square)
    opponent   = not our_colour

    if our_colour == chess.WHITE and dest_rank < 4:
        return False
    if our_colour == chess.BLACK and dest_rank > 3:
        return False

    ahead = range(dest_rank + 1, 8) if our_colour == chess.WHITE \
            else range(0, dest_rank)
    for f_off in (-1, 0, 1):
        cf = dest_file + f_off
        if not 0 <= cf <= 7:
            continue
        for rank in ahead:
            sq = chess.square(cf, rank)
            pp = board.piece_at(sq)
            if pp and pp.piece_type == chess.PAWN and pp.color == opponent:
                return False
    return True


def _is_back_rank_pressure(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if a rook or queen reaches the 7th rank (rank index 6 for
    White, 1 for Black), creating back-rank pressure on the opponent's king.
    """
    p = board.piece_at(move.from_square)
    if p is None or p.piece_type not in (chess.ROOK, chess.QUEEN):
        return False
    seventh = 6 if board.turn == chess.WHITE else 1
    return chess.square_rank(move.to_square) == seventh


def _is_castling(board: chess.Board, move: chess.Move) -> bool:
    """Returns True if the move is a castling move."""
    return board.is_castling(move)


def _is_pawn_promotion(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if the move promotes a pawn.
    Promotions are one of the most important tactical ideas in chess.
    """
    return move.promotion is not None



# NEW TACTICAL DETECTION HELPERS  (v1.4)


def _is_discovered_attack(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if moving a piece reveals a new attack by a friendly sliding
    piece (rook, bishop, or queen) on an opponent's piece or king.

    Algorithm:
        1. For every friendly sliding piece on the board (excluding the piece
           being moved), compare the squares it attacks BEFORE and AFTER the
           move is made.
        2. If any new square in the 'after' attack set contains an opponent
           piece, the move creates a discovered attack.

    This works because chess.Board.attacks(square) accounts for pieces blocking
    the ray: when the blocking piece moves, the ray extends further.

    Design note:
        We iterate only over friendly sliding pieces (not all pieces) to keep
        the function efficient — O(k) where k ≤ 9 (max sliders per side).

    Limitation:
        Does not check whether the discovered attack can be safely pursued (i.e.,
        whether the opponent can interpose or recapture). The educational purpose
        is pattern detection — the presence of the motif is sufficient for
        explanation generation. This limitation is documented for the NEA.
    """
    our_colour = board.turn
    from_sq    = move.from_square

    # Build the position after the move to compare attack sets
    test = board.copy()
    try:
        test.push(move)
    except Exception:
        return False

    for sq in chess.SQUARES:
        # We only care about our OWN sliding pieces (rook, bishop, queen)
        # that are NOT the piece being moved (it will be elsewhere after push)
        p = board.piece_at(sq)
        if p is None:
            continue
        if p.color != our_colour:
            continue
        if p.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue
        if sq == from_sq:
            continue     # Skip the piece we're moving; it no longer occupies sq

        # Compare attack sets before and after the move
        attacks_before = board.attacks(sq)
        attacks_after  = test.attacks(sq)

        # Newly reached squares (previously blocked by the moving piece)
        newly_attacked = attacks_after - attacks_before

        # Check if any newly attacked square contains an opponent piece
        for target_sq in newly_attacked:
            tp = test.piece_at(target_sq)
            if tp is not None and tp.color != our_colour:
                return True

    return False


def _is_skewer(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if a sliding piece move creates a skewer: the piece attacks
    a high-value opponent piece, behind which is a lesser piece that would
    be exposed once the front piece moves away.

    Definition:
        A skewer is the inverse of a pin. In a pin, the less-valuable piece
        is in front of the king. In a skewer, the MORE-valuable piece is in
        front of a less-valuable piece. The opponent must move the valuable
        piece (to avoid capture), exposing the piece behind it.

    Algorithm:
        1. Verify the moving piece is a slider (bishop, rook, or queen).
        2. After the move, cast rays from move.to_square in all directions
           applicable to the piece type.
        3. Along each ray, find the first and second opponent pieces.
        4. If the first piece is more valuable than the second, a skewer exists.

    Limitation:
        Does not verify that the first opponent piece is actually forced to move
        (the first piece might be adequately defended elsewhere). The pattern
        detection is sufficient for explanation purposes. Documented for NEA.
    """
    piece = board.piece_at(move.from_square)
    if piece is None:
        return False
    if piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
        return False

    test = board.copy()
    try:
        test.push(move)
    except Exception:
        return False

    opponent   = not board.turn
    to_file    = chess.square_file(move.to_square)
    to_rank    = chess.square_rank(move.to_square)

    # Directions applicable to the piece type
    if piece.piece_type == chess.ROOK:
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    elif piece.piece_type == chess.BISHOP:
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    else:                  # QUEEN — all eight directions
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0),
                      (1, 1), (1, -1), (-1, 1), (-1, -1)]

    for df, dr in directions:
        first_piece  = None
        second_piece = None
        cf, cr       = to_file + df, to_rank + dr

        while 0 <= cf <= 7 and 0 <= cr <= 7:
            sq = chess.square(cf, cr)
            p  = test.piece_at(sq)

            if p is not None:
                if p.color == opponent:
                    if first_piece is None:
                        first_piece = p
                    else:
                        second_piece = p
                        break           # Found both pieces — stop scanning ray
                else:
                    break               # Hit a friendly piece — ray blocked

            cf += df
            cr += dr

        # Skewer if first piece is more valuable than the second
        if first_piece is not None and second_piece is not None:
            first_val  = _PIECE_VALUE_ORDINAL.get(first_piece.piece_type, 0)
            second_val = _PIECE_VALUE_ORDINAL.get(second_piece.piece_type, 0)
            if first_val > second_val:
                return True

    return False


def _is_knight_outpost(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if a knight moves to an outpost square.

    An outpost is a square that satisfies ALL three conditions:
        1. The square is advanced (rank 4–7 for White, rank 1–4 for Black).
        2. No opponent pawn can ever attack the square (i.e., no opponent pawn
           on the same or adjacent file that could advance to attack the square).
        3. The square is currently supported by a friendly pawn (providing
           a 'guard' that prevents the opponent from easily dislodging the knight).

    Design justification:
        The outpost concept is a classic positional idea in chess strategy.
        A knight on an outpost square is exceptionally powerful because:
          (a) It cannot be chased away by opponent pawns.
          (b) It is protected, so the opponent cannot take it for free.
          (c) It controls key central and advanced squares.
        Teaching this concept addresses the intermediate player's positional
        understanding — a key educational goal of the system.

    Limitation:
        Condition 2 checks only for opponent pawns currently on the board,
        not pawn advances that might eventually attack the square. This is
        sufficient for real-time pattern detection but noted as a limitation.
    """
    piece = board.piece_at(move.from_square)
    if piece is None or piece.piece_type != chess.KNIGHT:
        return False

    our_colour = board.turn
    opponent   = not our_colour
    dest       = move.to_square
    dest_rank  = chess.square_rank(dest)
    dest_file  = chess.square_file(dest)

    # Condition 1: Advanced territory
    # White: ranks 4–7 (indices 3–6, 7 is promotion rank — unlikely for knight)
    # Black: ranks 1–4 (indices 0–3, 0 is promotion rank)
    if our_colour == chess.WHITE and dest_rank < 3:
        return False
    if our_colour == chess.BLACK and dest_rank > 4:
        return False

    # Condition 2: No opponent pawn can attack the destination square.
    # Opponent pawns attack diagonally: black pawns attack downward,
    # white pawns attack upward. Check adjacent files one rank "behind" the dest.
    if our_colour == chess.WHITE:
        pawn_attack_rank = dest_rank + 1   # Black pawn would be above dest
    else:
        pawn_attack_rank = dest_rank - 1   # White pawn would be below dest

    if 0 <= pawn_attack_rank <= 7:
        for file_off in (-1, 1):
            cf = dest_file + file_off
            if 0 <= cf <= 7:
                sq = chess.square(cf, pawn_attack_rank)
                p  = board.piece_at(sq)
                if p and p.piece_type == chess.PAWN and p.color == opponent:
                    return False   # Opponent pawn CAN attack — not an outpost

    # Condition 3: Supported by a friendly pawn (on an adjacent file, one rank back)
    if our_colour == chess.WHITE:
        support_rank = dest_rank - 1
    else:
        support_rank = dest_rank + 1

    if not 0 <= support_rank <= 7:
        return False   # Off the board — cannot be supported

    for file_off in (-1, 1):
        cf = dest_file + file_off
        if 0 <= cf <= 7:
            sq = chess.square(cf, support_rank)
            p  = board.piece_at(sq)
            if p and p.piece_type == chess.PAWN and p.color == our_colour:
                return True   # Supported by a friendly pawn ✓

    return False


def _is_battery_formation(board: chess.Board, move: chess.Move) -> bool:
    """
    Returns True if after the move, two friendly heavy pieces (rook+rook,
    queen+rook, or queen+queen) are aligned on the same file or rank with
    no pieces between them — forming a battery.

    Definition:
        A battery is a formation of two (or more) pieces of the same type or
        complementary types aligned along a file or rank (rooks/queens) or
        diagonal (bishops/queens). They amplify each other's firepower:
        after one piece fires (captures or advances), the other slides in.

    Algorithm:
        1. Confirm the moving piece is a rook or queen.
        2. After the move, scan the destination's file and rank for another
           friendly heavy piece (rook or queen).
        3. Check that no piece stands between them (the battery must be
           directly connected — an occupied square between them blocks the pair).

    Design justification:
        Doubled rooks and queen+rook batteries are fundamental heavy-piece
        coordination concepts. Detecting this pattern allows the system to
        explain a rook-doubling move in positional terms rather than just
        "this move puts the rook on an open file" (which the open_file rule
        covers). Both rules can fire simultaneously, and select_top_rules()
        will pick the two most relevant.

    Limitation:
        Only detects rank/file batteries (not diagonal queen+bishop batteries).
        Diagonal batteries require more complex ray scanning and are a known
        extension for future development (documented in 3.4.4).
    """
    piece = board.piece_at(move.from_square)
    if piece is None:
        return False
    if piece.piece_type not in (chess.ROOK, chess.QUEEN):
        return False

    our_colour = board.turn
    heavy_types = (chess.ROOK, chess.QUEEN)

    test = board.copy()
    try:
        test.push(move)
    except Exception:
        return False

    dest_file = chess.square_file(move.to_square)
    dest_rank = chess.square_rank(move.to_square)

    # ── Check same FILE ───────────────────────────────────────────────────────
    for rank in range(8):
        if rank == dest_rank:
            continue
        sq = chess.square(dest_file, rank)
        p  = test.piece_at(sq)
        if p is None or p.color != our_colour or p.piece_type not in heavy_types:
            continue
        # Found a second friendly heavy piece on the same file — check clear path
        min_r = min(rank, dest_rank)
        max_r = max(rank, dest_rank)
        if _file_clear(test, dest_file, min_r + 1, max_r - 1):
            return True

    # ── Check same RANK ───────────────────────────────────────────────────────
    for f in range(8):
        if f == dest_file:
            continue
        sq = chess.square(f, dest_rank)
        p  = test.piece_at(sq)
        if p is None or p.color != our_colour or p.piece_type not in heavy_types:
            continue
        # Found a second friendly heavy piece on the same rank — check clear path
        min_f = min(f, dest_file)
        max_f = max(f, dest_file)
        if _rank_clear(test, dest_rank, min_f + 1, max_f - 1):
            return True

    return False


def _file_clear(board: chess.Board, file_idx: int,
                rank_start: int, rank_end: int) -> bool:
    """Helper: returns True if all squares on `file_idx` between rank_start
    and rank_end (inclusive) are empty."""
    for r in range(rank_start, rank_end + 1):
        if board.piece_at(chess.square(file_idx, r)) is not None:
            return False
    return True


def _rank_clear(board: chess.Board, rank_idx: int,
                file_start: int, file_end: int) -> bool:
    """Helper: returns True if all squares on `rank_idx` between file_start
    and file_end (inclusive) are empty."""
    for f in range(file_start, file_end + 1):
        if board.piece_at(chess.square(f, rank_idx)) is not None:
            return False
    return True



# RULE CLASS  (Design Class 4 — unchanged from v1.3)


class Rule:
    """
    Represents a single explanation rule as an object.

    Attributes:
        rule_id               (str)      — unique identifier for logging/tests
        priority              (int/float)— lower = higher priority
        condition             (callable) — function(board, move) → bool
        beginner_template     (str)      — plain language, ≤10 words, no jargon
        intermediate_template (str)      — chess terminology allowed, up to 20 words

    Methods:
        is_triggered(board, move) → bool
        generate_text(mode)       → str

    Design justification:
        Encapsulating rules as objects means new rules can be appended to
        ExplanationEngine._build_rule_set() without touching any other code.
        This satisfies the Open/Closed Principle and supports extensibility
        (NEA design section 3.2.2(d)).
    """

    def __init__(self, rule_id: str, priority,
                 condition,
                 beginner_template: str,
                 intermediate_template: str):
        self.rule_id               = rule_id
        self.priority              = priority
        self.condition             = condition
        self.beginner_template     = beginner_template
        self.intermediate_template = intermediate_template

    def is_triggered(self, board: chess.Board, move: chess.Move) -> bool:
        """
        Evaluates the condition. Returns False on exception so a buggy rule
        never crashes the engine — supporting the no-crash guarantee (U23).
        """
        try:
            return bool(self.condition(board, move))
        except Exception:
            return False

    def generate_text(self, mode: str) -> str:
        """Returns the template string for the given mode."""
        return self.beginner_template if mode == "Beginner" \
               else self.intermediate_template



# EXPLANATION ENGINE  (Design Class 3)


class ExplanationEngine:
    """
    Generates human-readable explanations based on board analysis.

    Attributes:
        rules     (list[Rule]) — complete ordered rule set (18 rules in v1.4)
        mode      (str)        — "Beginner" or "Intermediate"
        max_words (int)        — word limit for current mode

    Methods:
        apply_rules(board, move)          → list[Rule]
        select_top_rules(triggered)       → list[Rule]
        format_explanation(rules, move)   → str
        generate_explanation(board, move) → str

    Design justification:
        ExplanationEngine is fully independent of the engine interface.
        It can be unit-tested on any chess.Board without needing Stockfish,
        supporting isolated module testing (tests T09–T21 in the test suite).
    """

    def __init__(self, mode: str = "Beginner"):
        self.mode      = mode
        self.max_words = WORD_LIMIT.get(mode, 20)
        self.rules     = self._build_rule_set()

    def set_mode(self, mode: str):
        """Hot-swap mode without recreating the engine."""
        self.mode      = mode
        self.max_words = WORD_LIMIT.get(mode, 20)

    # ── Rule set ──────────────────────────────────────────────────────────────

    def _build_rule_set(self) -> list:
        """
        Constructs all 18 rules. Each rule can be independently triggered
        and tested. Rules are sorted by priority at construction time so
        apply_rules() preserves that order naturally.

        Priority assignments (lower = higher importance):
            1   Pawn promotion  — most concrete, unambiguous, game-changing
            2   Checkmate threat — wins the game or forces the opponent to respond
            3   Fork            — attacks two opponent pieces simultaneously
            3.5 Discovered attack — reveals hidden attack (new v1.4)
            4   Pin             — restricts opponent piece movement
            4.5 Skewer          — forces opponent to expose a lesser piece (new v1.4)
            5   Hanging capture — free material gain
            6   Check          — forces opponent to respond immediately
            7   Capture (generic fallback if hanging not triggered)
            8   Castling       — king safety
            9   Central control — occupies a central square
            10  Development    — brings a piece into active play
            11  Open file rook — rook maximises mobility
            12  Semi-open file rook — rook pressures opponent pawns
            12.5 Knight outpost — powerful advanced knight position (new v1.4)
            13  Passed pawn    — pawn with no opposing blockers
            13.5 Battery formation — aligned heavy pieces (new v1.4)
            14  Back-rank pressure — rook/queen invades 7th rank
        """
        rules = [

            # Priority 1 — Pawn promotion
            Rule(
                rule_id               = "promotion",
                priority              = 1,
                condition             = _is_pawn_promotion,
                beginner_template     = "This pawn promotes — it becomes a new piece!",
                intermediate_template = "This move promotes the pawn, gaining a major piece.",
            ),

            # Priority 2 — Checkmate threat
            Rule(
                rule_id               = "mate_threat",
                priority              = 2,
                condition             = _threatens_checkmate,
                beginner_template     = "This move threatens checkmate!",
                intermediate_template = "This move delivers check with a near-forced checkmate.",
            ),

            # Priority 3 — Fork
            Rule(
                rule_id               = "fork",
                priority              = 3,
                condition             = _creates_fork,
                beginner_template     = "This move attacks two pieces at once — a fork!",
                intermediate_template = "This move creates a fork, attacking two opponent pieces simultaneously.",
            ),

            # Priority 3.5 — Discovered attack  (NEW v1.4)
            Rule(
                rule_id               = "discovered_attack",
                priority              = 3.5,
                condition             = _is_discovered_attack,
                beginner_template     = "Moving this piece reveals a hidden attack from another piece.",
                intermediate_template = "This move creates a discovered attack — a friendly slider now targets an opponent piece that was previously blocked.",
            ),

            # Priority 4 — Pin
            Rule(
                rule_id               = "pin",
                priority              = 4,
                condition             = _creates_pin,
                beginner_template     = "This move traps an opponent piece in place.",
                intermediate_template = "This move creates a pin — an opponent piece is fixed to protect its king.",
            ),

            # Priority 4.5 — Skewer  (NEW v1.4)
            Rule(
                rule_id               = "skewer",
                priority              = 4.5,
                condition             = _is_skewer,
                beginner_template     = "This move attacks a valuable piece and threatens to win the piece behind it!",
                intermediate_template = "This move creates a skewer — the opponent's valuable piece must move, exposing the lesser piece behind it to capture.",
            ),

            # Priority 5 — Hanging piece capture
            Rule(
                rule_id               = "hanging_capture",
                priority              = 5,
                condition             = lambda b, m: b.is_capture(m) and _is_hanging(b, m.to_square),
                beginner_template     = "This move takes a free piece!",
                intermediate_template = "This move captures a hanging piece — it was undefended and free to take.",
            ),

            # Priority 6 — Check
            Rule(
                rule_id               = "check",
                priority              = 6,
                condition             = _post_move_check,
                beginner_template     = "This move puts the opponent's king in check.",
                intermediate_template = "This move delivers check, forcing the opponent to respond immediately.",
            ),

            # Priority 7 — Basic capture (fallback)
            Rule(
                rule_id               = "capture",
                priority              = 7,
                condition             = lambda b, m: b.is_capture(m),
                beginner_template     = "This move takes one of the opponent's pieces.",
                intermediate_template = "This move captures opponent material, improving the material balance.",
            ),

            # Priority 8 — Castling
            Rule(
                rule_id               = "castling",
                priority              = 8,
                condition             = _is_castling,
                beginner_template     = "This move keeps the king safe by castling.",
                intermediate_template = "This move castles, sheltering the king and connecting the rooks.",
            ),

            # Priority 9 — Central control
            Rule(
                rule_id               = "central_control",
                priority              = 9,
                condition             = lambda b, m: m.to_square in (
                    chess.D4, chess.E4, chess.D5, chess.E5),
                beginner_template     = "This move controls the centre of the board.",
                intermediate_template = "This move occupies a central square (d4/e4/d5/e5), increasing positional control.",
            ),

            # Priority 10 — Minor piece development
            Rule(
                rule_id               = "development",
                priority              = 10,
                condition             = lambda b, m: (
                    (p := b.piece_at(m.from_square)) is not None
                    and p.piece_type in (chess.KNIGHT, chess.BISHOP)
                    and chess.square_rank(m.from_square) in (0, 7)
                ),
                beginner_template     = "This move brings a piece out to join the game.",
                intermediate_template = "This move develops a minor piece off the back rank, improving piece activity.",
            ),

            # Priority 11 — Open file rook
            Rule(
                rule_id               = "open_file",
                priority              = 11,
                condition             = _is_open_file_rook,
                beginner_template     = "This move puts the rook on a clear, open column.",
                intermediate_template = "This move places the rook on an open file, maximising its long-range activity.",
            ),

            # Priority 12 — Semi-open file rook
            Rule(
                rule_id               = "semi_open_file",
                priority              = 12,
                condition             = _is_semi_open_file_rook,
                beginner_template     = "This move puts the rook on a useful column.",
                intermediate_template = "This move places the rook on a semi-open file, pressuring the opponent's pawn.",
            ),

            # Priority 12.5 — Knight outpost  (NEW v1.4)
            Rule(
                rule_id               = "knight_outpost",
                priority              = 12.5,
                condition             = _is_knight_outpost,
                beginner_template     = "This knight is now on a powerful advanced square that can't be pushed away!",
                intermediate_template = "This move places the knight on an outpost — an advanced square unsupported by opponent pawns and guarded by a friendly pawn.",
            ),

            # Priority 13 — Passed pawn
            Rule(
                rule_id               = "passed_pawn",
                priority              = 13,
                condition             = _is_passed_pawn_advance,
                beginner_template     = "This pawn is now unstoppable — nothing can block it!",
                intermediate_template = "This advances a passed pawn with no opposing pawns able to stop its promotion.",
            ),

            # Priority 13.5 — Battery formation  (NEW v1.4)
            Rule(
                rule_id               = "battery",
                priority              = 13.5,
                condition             = _is_battery_formation,
                beginner_template     = "This move lines up two powerful pieces on the same row — double the firepower!",
                intermediate_template = "This move creates a battery — two heavy pieces aligned on the same file or rank, doubling their attacking potential.",
            ),

            # Priority 14 — Back-rank pressure
            Rule(
                rule_id               = "back_rank",
                priority              = 14,
                condition             = _is_back_rank_pressure,
                beginner_template     = "This move attacks the opponent's back row.",
                intermediate_template = "This move invades the 7th rank, creating back-rank pressure on the opponent's king.",
            ),
        ]

        rules.sort(key=lambda r: r.priority)
        return rules

    # ── Core pipeline ─────────────────────────────────────────────────────────

    def apply_rules(self, board: chess.Board, move: chess.Move) -> list:
        """
        Tests every rule. Returns all triggered rules in priority order.
        Uses a fresh board copy for each rule so rules that push/pop
        internally do not interfere with each other.
        """
        triggered = []
        for rule in self.rules:
            board_copy = board.copy()
            if rule.is_triggered(board_copy, move):
                triggered.append(rule)
        return triggered

    def select_top_rules(self, triggered: list) -> list:
        """
        Returns at most 2 triggered rules.

        Deduplication: if both 'capture' and 'hanging_capture' fire,
        drop the generic 'capture' — the more specific rule supersedes it.
        Prevents the explanation from redundantly mentioning a capture twice.
        """
        ids = {r.rule_id for r in triggered}
        if "hanging_capture" in ids and "capture" in ids:
            triggered = [r for r in triggered if r.rule_id != "capture"]
        return triggered[:2]

    def format_explanation(self, selected: list, move: chess.Move) -> str:
        """
        Joins the text of selected rules. Applies word-count enforcement.
        Falls back to a generic message if no rules fired (covers ≥90% of
        positions — success criterion F04).
        """
        if not selected:
            return (
                "This is the best available move."
                if self.mode == "Beginner"
                else "This move offers the best positional improvement available."
            )

        combined = " ".join(r.generate_text(self.mode) for r in selected)
        return self._enforce_word_limit(combined)

    def _enforce_word_limit(self, text: str) -> str:
        """Truncates to max_words. Appends ellipsis if truncated."""
        words = text.split()
        if len(words) <= self.max_words:
            return text
        return " ".join(words[:self.max_words]) + "…"

    def generate_explanation(self, board: chess.Board, move: chess.Move) -> str:
        """
        Public entry point.
        Runs the full pipeline: apply → select top 2 → format.
        """
        triggered = self.apply_rules(board, move)
        selected  = self.select_top_rules(triggered)
        return self.format_explanation(selected, move)
