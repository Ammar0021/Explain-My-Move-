
# engine_interface.py  —  Explain My Move  v1.2
# Author: Ammar
#
# Contains:
#   PIECE_VALUES           — centipawn constants for fallback heuristic
#   ChessEngineInterface   (Design Class 1)
#   MoveEvaluator          (Design Class 2)
#   BadMoveAnalyser        (v1.2 NEW — Design Class 7)
#   format_score()         — shared score formatting utility
#
# Changes from v1.0 → v1.2:
#   - BadMoveAnalyser class added (Design Class 7 / NEA feature F09).
#     Given a board position and a user-supplied move, it:
#       1. Evaluates the position before the move (best_score_before)
#       2. Evaluates the position after the user's move (score_after)
#       3. Computes the centipawn loss (cp_loss)
#       4. Classifies the move: OK / Inaccuracy / Mistake / Blunder
#       5. Returns a BadMoveResult dataclass with all diagnostic data
#          so the GUI can render a detailed "why was that bad?" panel.
#   - All version strings updated from "v1.0" to "v1.2".


import chess
import chess.engine
import time
from dataclasses import dataclass, field
from engine_config import ConfigManager



# PIECE VALUES  (used by fallback heuristic)


PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   0,
}



# BAD MOVE RESULT DATACLASS  (v1.2)


@dataclass
class BadMoveResult:
    """
    Carries the complete diagnostic result of a bad-move analysis.

    Attributes:
        user_move       (chess.Move) — the move the user entered
        user_move_san   (str)        — SAN notation of the user's move
        best_move       (chess.Move | None) — engine's recommended move
        best_move_san   (str)        — SAN of best move
        score_before    (int)        — centipawn evaluation before the move
        score_after     (int)        — centipawn evaluation after the user's move
        cp_loss         (int)        — how many centipawns the move cost
                                       (always non-negative; positive = worse)
        classification  (str)        — "OK" / "Inaccuracy" / "Mistake" / "Blunder"
        is_bad          (bool)       — True if classification != "OK"
        reasons         (list[str])  — list of human-readable reason strings
        better_lines    (list[str])  — SAN of 1–3 better alternatives
    """
    user_move:      object       = None
    user_move_san:  str          = ""
    best_move:      object       = None
    best_move_san:  str          = ""
    score_before:   int          = 0
    score_after:    int          = 0
    cp_loss:        int          = 0
    classification: str          = "OK"
    is_bad:         bool         = False
    reasons:        list         = field(default_factory=list)
    better_lines:   list         = field(default_factory=list)



# SCORE FORMATTING UTILITY


def format_score(centipawns: int, mode: str, is_mate: bool = False,
                 mate_in: int = None) -> str:
    """
    Converts a raw centipawn score into a human-readable display string.

    Intermediate mode: "+0.45", "Mate in 3"
    Beginner mode:     "Slight advantage for White", "Forced checkmate!"
    """
    if centipawns is None:
        return "—"

    if abs(centipawns) >= 9000:
        if mode == "Beginner":
            return "Forced checkmate!" if centipawns > 0 else "Opponent has forced checkmate"
        else:
            moves = (10000 - abs(centipawns) + 1) // 2
            if centipawns > 0:
                return f"Mate in {moves}"
            else:
                return f"Opponent mates in {moves}"

    if mode == "Intermediate":
        pawns = centipawns / 100.0
        return f"{pawns:+.2f}"
    else:
        if centipawns >= 300:
            return "Strong advantage for White"
        elif centipawns >= 100:
            return "Slight advantage for White"
        elif centipawns >= -100:
            return "Roughly equal"
        elif centipawns >= -300:
            return "Slight advantage for Black"
        else:
            return "Strong advantage for Black"



# CHESS ENGINE INTERFACE CLASS  (Design Class 1)


class ChessEngineInterface:
    """
    Handles all interaction with the external Stockfish engine.

    Methods:
        analyse_multipv(board, multipv) → list[(chess.Move, int)]
        analyse_single(board)           → (chess.Move | None, int)  [v1.2]
        update_from_config(config)      — syncs depth/timeout
        _fallback_score(board, n)       → list[(chess.Move, int)]
    """

    def __init__(self, config: ConfigManager):
        self.engine_path      = config.get_setting("engine_path")
        self.engine_depth     = config.get_setting("engine_depth")
        self.timeout          = config.get_setting("timeout")
        self.engine_instance  = None
        self.timeout_flag     = False
        self.analysis_time_ms = 0

    def update_from_config(self, config: ConfigManager):
        self.engine_path  = config.get_setting("engine_path")
        self.engine_depth = config.get_setting("engine_depth")
        self.timeout      = config.get_setting("timeout")

    def analyse_multipv(self, board: chess.Board, multipv: int) -> list:
        """
        Analyses the board and returns up to `multipv` ranked
        (chess.Move, centipawn_score) tuples, best first.
        """
        self.timeout_flag = False
        start             = time.time()
        legal_count       = sum(1 for _ in board.legal_moves)

        if legal_count == 0:
            self.analysis_time_ms = 0
            return []

        effective_multipv = min(multipv, legal_count)

        try:
            engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
            limit  = chess.engine.Limit(depth=self.engine_depth, time=self.timeout)
            results = engine.analyse(board, limit, multipv=effective_multipv)
            engine.quit()

            if isinstance(results, dict):
                results = [results]

            ranked = []
            for info in results:
                if "pv" not in info or not info["pv"]:
                    continue
                move  = info["pv"][0]
                score = info["score"].white().score(mate_score=10000)
                ranked.append((move, score))

            self.analysis_time_ms = int((time.time() - start) * 1000)
            return ranked

        except FileNotFoundError:
            self.timeout_flag     = True
            self.analysis_time_ms = int((time.time() - start) * 1000)
            return self._fallback_score(board, effective_multipv)

        except Exception:
            self.timeout_flag     = True
            self.analysis_time_ms = int((time.time() - start) * 1000)
            return self._fallback_score(board, effective_multipv)

    def analyse_single(self, board: chess.Board) -> tuple:
        """
        Analyses the board at depth/timeout and returns (best_move, score).
        Returns (None, 0) for terminal positions or on failure.
        Used by BadMoveAnalyser for single-position evaluation.  [v1.2]
        """
        results = self.analyse_multipv(board, 1)
        if results:
            return results[0]
        return (None, 0)

    def _fallback_score(self, board: chess.Board, num_moves: int) -> list:
        """
        Pure-Python material heuristic scorer used when Stockfish is
        unavailable or times out.
        """
        our_colour = board.turn
        scored     = []

        for move in board.legal_moves:
            test = board.copy()
            test.push(move)
            ours = opp = 0
            for sq in chess.SQUARES:
                p = test.piece_at(sq)
                if p is None or p.piece_type == chess.KING:
                    continue
                val = PIECE_VALUES[p.piece_type]
                if p.color == our_colour:
                    ours += val
                else:
                    opp += val
            scored.append((move, ours - opp))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:num_moves]



# MOVE EVALUATOR CLASS  (Design Class 2)


class MoveEvaluator:
    """
    Evaluates all legal moves from a board state and ranks them.
    """

    def __init__(self, board: chess.Board, engine: ChessEngineInterface,
                 config: ConfigManager):
        self.board            = board
        self._engine          = engine
        self._config          = config
        self.evaluated_moves  = []
        self.ranked_moves     = []
        self.timeout_flag     = False
        self.analysis_time_ms = 0

    def generate_legal_moves(self) -> list:
        return list(self.board.legal_moves)

    def evaluate_moves(self):
        multipv = self._config.get_setting("multipv_count")
        self.evaluated_moves  = self._engine.analyse_multipv(self.board, multipv)
        self.timeout_flag     = self._engine.timeout_flag
        self.analysis_time_ms = self._engine.analysis_time_ms

    def rank_moves(self):
        if not self.evaluated_moves:
            self.ranked_moves = []
            return
        reverse      = (self.board.turn == chess.WHITE)
        null_default = -99999 if reverse else 99999
        self.ranked_moves = sorted(
            self.evaluated_moves,
            key    = lambda x: x[1] if x[1] is not None else null_default,
            reverse = reverse,
        )

    def get_best_move(self):
        return self.ranked_moves[0][0] if self.ranked_moves else None

    def run_full_evaluation(self):
        self.evaluate_moves()
        self.rank_moves()



# BAD MOVE ANALYSER  (Design Class 7 — v1.2 NEW)


class BadMoveAnalyser:
    """
    Analyses a user-supplied move against the engine's best recommendation
    and explains WHY the move is bad — or confirms it is fine.

    Algorithm:
        1. Evaluate the position before the move → score_before (from White's POV)
        2. Push the user's move; evaluate the resulting position → score_after
        3. cp_loss = (score_before − score_after) from the SIDE TO MOVE's POV:
               White to move: cp_loss = score_before − score_after
                              (positive = White lost ground = bad for White)
               Black to move: cp_loss = score_after − score_before
                              (positive = Black's position worsened = bad for Black)
        4. Classify:
               cp_loss < threshold       → "OK"
               threshold ≤ cp_loss < 200 → "Inaccuracy"
               200 ≤ cp_loss < 400       → "Mistake"
               cp_loss ≥ 400             → "Blunder"
        5. Generate reason strings explaining what was missed / what went wrong.

    Design justification (NEA F09):
        Separating bad-move detection into its own class keeps MoveEvaluator
        focused on ranking legal moves, and keeps ExplanationEngine focused
        on positive move explanations. This satisfies Single Responsibility
        and allows BadMoveAnalyser to be unit-tested independently.

    Attributes:
        _engine   (ChessEngineInterface)
        _config   (ConfigManager)
        threshold (int) — centipawn loss to classify as "not OK"
    """

    # Human-readable classification labels
    _CLASSIFICATIONS = [
        (400, "Blunder"),
        (200, "Mistake"),
        (  0, "Inaccuracy"),
    ]

    def __init__(self, engine: ChessEngineInterface, config: ConfigManager):
        self._engine   = engine
        self._config   = config
        self.threshold = config.get_setting("bad_move_threshold")

    def _san(self, board: chess.Board, move: chess.Move) -> str:
        """Safe SAN conversion with UCI fallback."""
        try:
            return board.san(move)
        except Exception:
            return str(move)

    def _classify(self, cp_loss: int) -> str:
        """Returns classification string for a given centipawn loss."""
        if cp_loss < self.threshold:
            return "OK"
        for threshold, label in self._CLASSIFICATIONS:
            if cp_loss >= threshold:
                return label
        return "Inaccuracy"

    def _score_from_side(self, raw_white_score: int, is_white_to_move: bool) -> int:
        """
        Converts a White-normalised centipawn score to the moving side's
        perspective. Positive = good for the side to move.
        """
        if is_white_to_move:
            return raw_white_score
        else:
            return -raw_white_score

    def analyse(self, board: chess.Board, user_move: chess.Move,
                mode: str = "Beginner") -> BadMoveResult:
        """
        Core analysis method.

        Parameters:
            board      — position BEFORE the user's move is applied
            user_move  — the move the user wants to check
            mode       — "Beginner" or "Intermediate" (affects reason wording)

        Returns:
            BadMoveResult with all diagnostic data populated.
        """
        result = BadMoveResult()
        result.user_move    = user_move
        result.user_move_san = self._san(board, user_move)

        is_white = (board.turn == chess.WHITE)

        # ── Step 1: best move and score before user's move ────────────────────
        best_results = self._engine.analyse_multipv(board, 3)
        if not best_results:
            result.classification = "OK"
            return result

        best_move, raw_before = best_results[0]
        result.best_move    = best_move
        result.best_move_san = self._san(board, best_move)
        result.score_before = raw_before
        score_before_side   = self._score_from_side(raw_before, is_white)

        # ── Step 2: evaluate position after user's move ───────────────────────
        board_after = board.copy()
        board_after.push(user_move)
        _, raw_after = self._engine.analyse_single(board_after)

        # After pushing user's move it's the opponent's turn, so flip POV
        result.score_after = raw_after
        # score_after from USER's perspective (negated because it's opponent's turn now)
        score_after_side   = -self._score_from_side(raw_after, not is_white)

        # ── Step 3: centipawn loss ────────────────────────────────────────────
        cp_loss = score_before_side - score_after_side
        result.cp_loss = max(0, cp_loss)

        # ── Step 4: classify ──────────────────────────────────────────────────
        classification      = self._classify(result.cp_loss)
        result.classification = classification
        result.is_bad       = (classification != "OK")

        # ── Step 5: generate reasons ──────────────────────────────────────────
        result.reasons      = self._generate_reasons(
            board, user_move, best_move, result, mode
        )

        # ── Step 6: better alternatives ──────────────────────────────────────
        result.better_lines = [
            self._san(board, m)
            for m, _ in best_results[:3]
            if m != user_move
        ][:3]

        return result

    def _generate_reasons(self, board: chess.Board, user_move: chess.Move,
                          best_move: chess.Move, result: BadMoveResult,
                          mode: str) -> list:
        """
        Generates a list of human-readable reason strings explaining
        why the user's move is classified as it is.

        Checks (in order of importance):
            1. Hangs a piece (user's move leaves their own piece undefended)
            2. Misses a capture of a hanging piece
            3. Misses a fork
            4. Misses check / checkmate
            5. Misses pawn promotion
            6. Walks into check
            7. General score-based reason
        """
        reasons = []

        if not result.is_bad:
            if mode == "Beginner":
                reasons.append("This move is fine — no significant mistake detected.")
            else:
                reasons.append(
                    f"This move loses ≤{result.cp_loss} centipawns "
                    "and is within acceptable bounds."
                )
            return reasons

        # Import helpers used in explanation_engine — avoids circular import
        # by doing a local import here.
        try:
            from explanation_engine import (
                _is_hanging, _creates_fork, _post_move_check,
                _is_pawn_promotion, _threatens_checkmate
            )
        except ImportError:
            reasons.append(
                f"This move loses approximately "
                f"{result.cp_loss / 100:.1f} pawns compared to the best move."
            )
            return reasons

        # 1. Does the user's move leave one of their own pieces hanging?
        board_after = board.copy()
        board_after.push(user_move)
        for sq in chess.SQUARES:
            p = board_after.piece_at(sq)
            if p and p.color == board.turn:  # user's pieces
                # Check if opponent can take it undefended
                if _is_hanging(board_after, sq):
                    pname = chess.piece_name(p.piece_type).capitalize()
                    sq_name = chess.square_name(sq)
                    if mode == "Beginner":
                        reasons.append(
                            f"This move leaves your {pname} on {sq_name} undefended "
                            f"— it can be taken for free."
                        )
                    else:
                        reasons.append(
                            f"This move leaves the {pname} on {sq_name} hanging "
                            f"(undefended), gifting material to the opponent."
                        )

        # 2. Did the user miss taking a hanging piece?
        if best_move and board.is_capture(best_move):
            target_sq = best_move.to_square
            if _is_hanging(board, target_sq):
                target_piece = board.piece_at(target_sq)
                if target_piece:
                    pname = chess.piece_name(target_piece.piece_type).capitalize()
                    if mode == "Beginner":
                        reasons.append(
                            f"You missed capturing a free {pname} "
                            f"on {chess.square_name(target_sq)}."
                        )
                    else:
                        reasons.append(
                            f"The best move captures a hanging {pname} on "
                            f"{chess.square_name(target_sq)}, winning material."
                        )

        # 3. Does the best move create a fork the user missed?
        if best_move and _creates_fork(board, best_move):
            if not _creates_fork(board, user_move):
                if mode == "Beginner":
                    reasons.append(
                        "You missed a move that attacks two opponent pieces at once "
                        "(a fork)."
                    )
                else:
                    reasons.append(
                        f"{result.best_move_san} creates a fork attacking two opponent "
                        "pieces simultaneously — your move misses this tactic."
                    )

        # 4. Does the best move threaten checkmate / give check?
        if best_move and _threatens_checkmate(board, best_move):
            if not _threatens_checkmate(board, user_move):
                if mode == "Beginner":
                    reasons.append("You missed a move that threatens checkmate!")
                else:
                    reasons.append(
                        f"{result.best_move_san} delivers check with a near-forced "
                        "checkmate — your move misses this winning sequence."
                    )

        # 5. Does the user's move walk into check (illegal would be caught earlier,
        #    but we check if it forces a bad king position)?
        board_after2 = board.copy()
        board_after2.push(user_move)
        if board_after2.is_check():
            if mode == "Beginner":
                reasons.append(
                    "This move puts your king in check, forcing you to respond "
                    "immediately and losing tempo."
                )
            else:
                reasons.append(
                    "After this move your king is in check, consuming a tempo "
                    "and worsening your position."
                )

        # 6. Did the user miss a pawn promotion?
        if best_move and _is_pawn_promotion(board, best_move):
            if not _is_pawn_promotion(board, user_move):
                if mode == "Beginner":
                    reasons.append("You missed promoting your pawn to a new piece!")
                else:
                    reasons.append(
                        f"{result.best_move_san} promotes the pawn, gaining a major piece. "
                        "Your move misses this opportunity."
                    )

        # 7. Fallback general reason if none of the above triggered
        if not reasons:
            pawns = result.cp_loss / 100.0
            if mode == "Beginner":
                if result.classification == "Blunder":
                    reasons.append(
                        f"This is a serious mistake — it gives the opponent a big advantage. "
                        f"Try {result.best_move_san} instead."
                    )
                elif result.classification == "Mistake":
                    reasons.append(
                        f"This move weakens your position noticeably. "
                        f"{result.best_move_san} would be stronger."
                    )
                else:
                    reasons.append(
                        f"This move is slightly weaker than the best option "
                        f"({result.best_move_san})."
                    )
            else:
                reasons.append(
                    f"This move loses approximately {pawns:.1f} pawns "
                    f"({result.cp_loss} cp) compared to the engine's best: "
                    f"{result.best_move_san}."
                )

        return reasons
