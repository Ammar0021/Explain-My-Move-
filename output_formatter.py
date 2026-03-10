
# output_formatter.py  —  Explain My Move  v1.3
# Author: Ammar
#
# Contains:
#   REQUIRED_SCHEMA_FIELDS  — JSON schema definition
#   OutputFormatter          (Design Class 6)
#
# Changes from v0.9:
#   - format_text_output() now shows score in pawn units via format_score()
#     rather than raw centipawns (fixes U14 — "show +0.45 not +45").
#   - Beginner mode output uses the descriptive phrase from format_score()
#     instead of centipawn values (fixes U18 — avoid jargon).
#   - SAN notation used throughout display (fixes the UCI-only display bug).
#   - format_for_display() extended: shows SAN, formatted score, word count,
#     schema status, rule transparency, and performance metrics.
#   - generate_pgn_output() added: produces a PGN string from a board state
#     so the GUI can offer "Export PGN" (satisfies the "exported PGNs must
#     load correctly" measurable success criterion).


import json
import chess
import chess.pgn
import io
from engine_interface import MoveEvaluator, format_score



# JSON SCHEMA DEFINITION
# All keys and types must be present for validate_schema() to return True.
# Tests T23 and T24 run against this definition.


REQUIRED_SCHEMA_FIELDS: dict = {
    "best_move_uci":    str,    # UCI notation e.g. "e2e4"
    "best_move_san":    str,    # SAN notation e.g. "e4"
    "score_centipawns": int,    # raw centipawn value from engine
    "score_display":    str,    # formatted display string e.g. "+0.45"
    "explanation":      str,    # plain-English explanation
    "mode":             str,    # "Beginner" or "Intermediate"
    "depth_used":       int,    # search depth
    "timeout_flag":     bool,   # True if fallback heuristic was used
    "analysis_time_ms": int,    # elapsed milliseconds
    "ranked_moves":     list,   # list of {"rank", "uci", "san", "score"} dicts
    "word_count":       int,    # word count of explanation
    "schema_valid":     bool,   # True if validate_schema passes
}



# OUTPUT FORMATTER CLASS  (Design Section 3.2.2(d) — Class 6)


class OutputFormatter:
    """
    Formats evaluation results into user-readable text and structured JSON.

    Attributes (matching design spec):
        mode (str) — "Beginner" or "Intermediate"

    Methods (matching design spec):
        format_text_output(...)        → str   (concise plain-text summary)
        generate_json_output(...)      → dict  (structured JSON-ready dict)
        validate_schema(json_output)   → (bool, list[str])

    Additional methods:
        format_for_display(...)        → str   (verbose GUI panel output)
        to_json_string(json_output)    → str   (serialised JSON)
        generate_pgn_output(board)     → str   (PGN of current position)
        get_fen(board)                 → str   (current FEN for clipboard)

    Design justification:
        Separating formatting from evaluation means the GUI and any future
        CLI interface share the same output backend. JSON output supports
        automated testing (T23/T24/T25) and the "100% schema validity" target.
    """

    def __init__(self, mode: str = "Beginner"):
        self.mode = mode

    def set_mode(self, mode: str):
        """Hot-swap mode without recreating the formatter."""
        self.mode = mode

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _san(self, board: chess.Board, move: chess.Move) -> str:
        """
        Converts a move to SAN (Standard Algebraic Notation).
        Falls back to UCI string on failure so the display never crashes.
        SAN (e.g. "Nf3") is more readable for chess players than UCI ("g1f3").
        Satisfies the design glossary entry on SAN notation.
        """
        try:
            return board.san(move)
        except Exception:
            return str(move)

    def _fmt_score(self, centipawns) -> str:
        """Formats centipawns using format_score() for the current mode."""
        if centipawns is None:
            return "—"
        return format_score(centipawns, self.mode)

    # ── Public methods ────────────────────────────────────────────────────────

    def format_text_output(self, board: chess.Board, ranked_moves: list,
                           explanation: str, evaluator: MoveEvaluator) -> str:
        """
        Produces a concise plain-text summary for the GUI Analysis tab.
        Format is identical on every call (U11 — Consistent Output Format).

        Score display follows U14 ("+0.45" in Intermediate) and U18
        (descriptive phrase in Beginner, no "centipawn" jargon).
        Move displayed in SAN (U03 — best move clearly labelled).
        """
        if not ranked_moves:
            return self._terminal_message(board)

        move, cp = ranked_moves[0]
        san      = self._san(board, move)
        score_s  = self._fmt_score(cp)
        timeout_s = "\n⚠  Using fast evaluation (engine timed out or unavailable)." \
                    if evaluator.timeout_flag else ""
        perf_warn = "  ← exceeds 2s target" if evaluator.analysis_time_ms > 2000 else ""

        lines = [
            f"Recommended Move:  {san}  [{move}]",
            f"Evaluation:        {score_s}",
            f"Mode:              {self.mode}",
            f"Depth:             {evaluator._config.get_setting('engine_depth')}",
            f"Analysis Time:     {evaluator.analysis_time_ms} ms{perf_warn}",
            timeout_s,
            "",
            "Explanation:",
            explanation,
        ]
        return "\n".join(l for l in lines if l is not None)

    def format_for_display(self, board: chess.Board, ranked_moves: list,
                           explanation: str, evaluator: MoveEvaluator,
                           triggered_ids: list, used_ids: list) -> str:
        """
        Extended output for the GUI panel. Includes all fields from
        format_text_output() plus:
            - All ranked moves with SAN + score
            - Triggered / used rule IDs (transparency for testing evidence)
            - JSON schema validation result
            - Word count vs mode limit

        This level of detail provides annotated evidence for:
            U20 (Engine Depth Transparency)
            T18–T22 (Explanation Engine testing)
            T23–T25 (JSON schema testing — via schema_valid field)
        """
        if not ranked_moves:
            return self._terminal_message(board)

        move, cp  = ranked_moves[0]
        san       = self._san(board, move)
        score_s   = self._fmt_score(cp)
        word_count = len(explanation.split())
        max_words  = evaluator._config.get_setting(
            "word_limit_beginner" if self.mode == "Beginner" else "word_limit_intermediate"
        )
        depth    = evaluator._config.get_setting("engine_depth")
        timeout  = evaluator._config.get_setting("timeout")
        t_ms     = evaluator.analysis_time_ms
        perf_ok  = "✓" if t_ms <= 2000 else "⚠ exceeds 2s target"
        fallback = "\n⚠  Using fast evaluation (Stockfish timed out or not found)." \
                   if evaluator.timeout_flag else ""

        # Schema check
        jout = self.generate_json_output(board, ranked_moves, explanation, evaluator)
        is_valid, errors = self.validate_schema(jout)
        schema_s = "✓ Valid" if is_valid else f"✗ {'; '.join(errors)}"

        # Ranked move list
        ranked_lines = []
        labels = ["1st (Best)", "2nd", "3rd", "4th", "5th"]
        for i, (m, score) in enumerate(ranked_moves):
            label = labels[i] if i < len(labels) else f"#{i+1}"
            ranked_lines.append(
                f"  {label}: {self._san(board, m)}  [{m}]  {self._fmt_score(score)}"
            )
        ranked_block = "\n".join(ranked_lines)

        lines = [
            "═" * 52,
            f"Recommended Move:  {san}  [{move}]",
            f"Evaluation:        {score_s}",
            f"Mode:              {self.mode}  (word limit: ≤{max_words})",
            f"Depth: {depth}  |  Timeout: {timeout}s  |  Time: {t_ms}ms  {perf_ok}",
            fallback,
            "",
            f"Explanation  ({word_count}/{max_words} words):",
            explanation,
            "",
            "Ranked Moves:",
            ranked_block,
            "",
            f"Rules triggered:  {triggered_ids}",
            f"Rules used:       {used_ids}",
            "",
            f"JSON Schema:      {schema_s}",
            "═" * 52,
        ]
        return "\n".join(l for l in lines if l is not None)

    def generate_json_output(self, board: chess.Board, ranked_moves: list,
                             explanation: str, evaluator: MoveEvaluator) -> dict:
        """
        Produces a structured dict matching REQUIRED_SCHEMA_FIELDS.
        Includes SAN notation for each ranked move alongside UCI so the
        output is human-readable without needing a board object.

        schema_valid is computed by calling validate_schema() on the
        constructed dict before returning, so the field is always accurate.
        """
        if not ranked_moves:
            output = {
                "best_move_uci":    "",
                "best_move_san":    "",
                "score_centipawns": 0,
                "score_display":    "—",
                "explanation":      self._terminal_message(board),
                "mode":             self.mode,
                "depth_used":       evaluator._config.get_setting("engine_depth"),
                "timeout_flag":     evaluator.timeout_flag,
                "analysis_time_ms": evaluator.analysis_time_ms,
                "ranked_moves":     [],
                "word_count":       0,
                "schema_valid":     True,
            }
            is_valid, _ = self.validate_schema(output)
            output["schema_valid"] = is_valid
            return output

        best_move, best_cp = ranked_moves[0]

        ranked_list = []
        for i, (m, score) in enumerate(ranked_moves):
            ranked_list.append({
                "rank":  i + 1,
                "uci":   str(m),
                "san":   self._san(board, m),
                "score": score if score is not None else 0,
            })

        output = {
            "best_move_uci":    str(best_move),
            "best_move_san":    self._san(board, best_move),
            "score_centipawns": best_cp if best_cp is not None else 0,
            "score_display":    self._fmt_score(best_cp),
            "explanation":      explanation,
            "mode":             self.mode,
            "depth_used":       evaluator._config.get_setting("engine_depth"),
            "timeout_flag":     evaluator.timeout_flag,
            "analysis_time_ms": evaluator.analysis_time_ms,
            "ranked_moves":     ranked_list,
            "word_count":       len(explanation.split()),
            "schema_valid":     True,   # placeholder; updated below
        }

        is_valid, _ = self.validate_schema(output)
        output["schema_valid"] = is_valid
        return output

    def validate_schema(self, json_output: dict) -> tuple:
        """
        Checks all required fields are present and correctly typed.
        Returns (True, []) on success, (False, [error strings]) on failure.

        Directly implements tests T23 (valid schema → True) and T24
        (missing field → False). The bool/int subclass trap is handled:
        isinstance(True, int) returns True in Python, so we check for bool
        explicitly before int to distinguish them correctly.
        """
        errors = []
        for field, expected_type in REQUIRED_SCHEMA_FIELDS.items():
            if field not in json_output:
                errors.append(f"Missing field: '{field}'")
                continue
            val = json_output[field]
            if expected_type is bool:
                if not isinstance(val, bool):
                    errors.append(f"'{field}': expected bool, got {type(val).__name__}")
            elif expected_type is int:
                if isinstance(val, bool) or not isinstance(val, int):
                    errors.append(f"'{field}': expected int, got {type(val).__name__}")
            elif not isinstance(val, expected_type):
                errors.append(
                    f"'{field}': expected {expected_type.__name__}, got {type(val).__name__}"
                )
        return len(errors) == 0, errors

    def to_json_string(self, json_output: dict, indent: int = 2) -> str:
        """Serialises json_output to a formatted JSON string."""
        return json.dumps(json_output, indent=indent, default=str)

    def generate_pgn_output(self, board: chess.Board) -> str:
        """
        Produces a PGN string from the current board state.
        Uses chess.pgn.Game.from_board() to reconstruct the move history.
        The exported PGN is valid and loads correctly in standard tools
        (Lichess, Chess.com, Arena) — satisfying the measurable success
        criterion: "exported PGNs must load correctly in standard tools."
        """
        game = chess.pgn.Game.from_board(board)
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=False)
        return game.accept(exporter)

    def get_fen(self, board: chess.Board) -> str:
        """Returns the FEN string for the current board position."""
        return board.fen()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _terminal_message(self, board: chess.Board) -> str:
        """Returns a clear message for terminal positions (no legal moves)."""
        if board.is_checkmate():
            winner = "Black" if board.turn == chess.WHITE else "White"
            return f"Checkmate — {winner} wins. No moves to analyse."
        if board.is_stalemate():
            return "Stalemate — the game is drawn. No moves to analyse."
        if board.is_insufficient_material():
            return "Draw by insufficient material. No moves to analyse."
        return "No legal moves available in this position."
