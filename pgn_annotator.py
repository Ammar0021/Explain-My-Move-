
# pgn_annotator.py  —  Explain My Move  v1.3
# Author: Ammar
# OCR A-Level Computer Science NEA — Component 03/04
#
# Contains:
#   PGNAnnotator  — Produces annotated PGN strings with embedded move comments.
#
# Purpose:
#   Extends the basic PGN export (OutputFormatter.generate_pgn_output) by
#   embedding a comment after every move in the PGN. Comments include:
#       • Classification label  (e.g., "??" for Blunder)
#       • Centipawn loss        (Intermediate mode only)
#       • Engine explanation    (from ExplanationEngine)
#       • Best move alternative (when the player's move was not best)
#
#   The output is a valid PGN string that loads correctly in:
#       Lichess Analysis Board, Chess.com Analysis, Arena, ChessBase.
#   (Satisfies the measurable success criterion "exported PGNs must load
#    correctly in standard tools" — NEA Analysis 3.1.4(b).)
#
# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────
#   PGNAnnotator is called from the GUI's "Export Annotated PGN" button,
#   which appears in the review mode menu (File → Export Annotated PGN).
#   It receives the _review_moves list directly from ExplainMyMoveApp.
#
# ─────────────────────────────────────────────────────────────────────────────
# PGN COMMENT FORMAT  (NEA design justification)
# ─────────────────────────────────────────────────────────────────────────────
#   The PGN standard (FIDE handbook) allows free-text comments inside { }.
#   We follow the NAG (Numeric Annotation Glyph) standard for classification:
#       $1  = Best move (!!)  /  Good move (!)
#       $2  = Mistake (?)
#       $4  = Blunder (??)
#       $6  = Inaccuracy (?!)
#   NAGs are machine-readable and displayed by GUI tools as familiar symbols.
#   A human-readable text comment is also appended in {} for plain-text viewers.
#
# ─────────────────────────────────────────────────────────────────────────────
# DESIGN JUSTIFICATION  (NEA Section 3.2.2(d))
# ─────────────────────────────────────────────────────────────────────────────
#   PGNAnnotator is a separate class from OutputFormatter rather than a method
#   on it because:
#     1. It depends on the full review_entries structure, not just ranked_moves.
#     2. It is only relevant in PGN review mode — adding it to OutputFormatter
#        would violate the Single Responsibility Principle.
#     3. A dedicated class can be independently tested without a live board.


import chess
import chess.pgn
import io
from dataclasses import dataclass



# NAG MAPPING
# (Numeric Annotation Glyphs — PGN standard §8.2.4)


_NAG_MAP: dict[str, int] = {
    "Brilliant":  1,    # ! (best move)
    "Best":       1,    # !
    "OK":         1,    # ! (no annotation in practice, but valid)
    "Good":       1,    # !
    "Inaccuracy": 6,    # ?!
    "Mistake":    2,    # ?
    "Blunder":    4,    # ??
}

# Human-readable symbols for the text comment (for plain-text PGN viewers)
_SYMBOL_MAP: dict[str, str] = {
    "Brilliant":  "!!",
    "Best":       "",
    "OK":         "",
    "Good":       "",
    "Inaccuracy": "?!",
    "Mistake":    "?",
    "Blunder":    "??",
}



# PGN ANNOTATOR CLASS


class PGNAnnotator:
    """
    Produces an annotated PGN string from a completed game review.

    Class attributes:
        mode  (str) — "Beginner" or "Intermediate"; controls comment verbosity

    Methods:
        annotate(review_entries, game_metadata) → str
            Main public method. Returns a valid annotated PGN string.

        build_comment(entry, mode)              → str   [classmethod]
            Builds the comment string for a single move entry.
            Exposed as classmethod for unit-testing without running a full game.

        _build_nag(classification)              → int
            Returns the NAG integer for a given classification string.

        _build_pgn_header(metadata)             → str
            Constructs the PGN header tag pairs from a metadata dict.

    Algorithm:
        1. Replay the game move-by-move using the review_entries list,
           which provides the board state before each move.
        2. For each move, construct a chess.pgn.GameNode and set its
           comment using build_comment().
        3. Set the NAG using GameNode.nags.add(nag_value).
        4. Export the completed chess.pgn.Game using StringExporter.
    """

    def __init__(self, mode: str = "Beginner"):
        self.mode = mode

    def set_mode(self, mode: str):
        """Hot-swap mode without recreating the annotator."""
        self.mode = mode

    # ── Public API ────────────────────────────────────────────────────────────

    def annotate(self, review_entries: list,
                 metadata: dict = None) -> str:
        """
        Main entry point. Builds an annotated PGN from a list of review entries.

        Parameters:
            review_entries  — list of ReviewEntry dicts from the PGN review
                              (must contain 'board_before', 'move', 'move_san',
                              'classification', 'cp_loss', 'reasons',
                              'best_move_san', 'explanation_best', 'explanation_user')
            metadata        — optional dict with PGN header fields:
                              {"Event": ..., "White": ..., "Black": ..., "Date": ...}
                              If None, sensible defaults are used.

        Returns:
            A valid PGN string. Returns empty string if review_entries is empty.

        Example output:
            [Event "Explain My Move Analysis"]
            [White "Player"]
            [Black "Player"]
            ...

            1. e4 { Best move. This move controls the centre of the board. } $1
               e5 { Best move. } $1
            2. Nf3 { Best move. This move develops a minor piece... } $1
               Nc6 ?? { Blunder! This move loses approximately 2.4 pawns compared
               to the best: d6. Try d6 instead. } $4
            ...
        """
        if not review_entries:
            return ""

        # ── Build PGN Game object ─────────────────────────────────────────────
        game = chess.pgn.Game()

        # Header
        meta = metadata or {}
        game.headers["Event"]  = meta.get("Event",  "Explain My Move Analysis")
        game.headers["Site"]   = meta.get("Site",   "Explain My Move v1.3")
        game.headers["Date"]   = meta.get("Date",   "????.??.??")
        game.headers["Round"]  = meta.get("Round",  "?")
        game.headers["White"]  = meta.get("White",  "Player")
        game.headers["Black"]  = meta.get("Black",  "Player")
        game.headers["Result"] = meta.get("Result", "*")
        game.headers["Annotator"] = "Explain My Move (OCR A-Level NEA)"

        # ── Replay moves and add comments ─────────────────────────────────────
        node = game
        for entry in review_entries:
            move = entry.get("move")
            if move is None:
                continue

            # Add the move as a child node
            node = node.add_variation(move)

            # Set NAG (Numeric Annotation Glyph)
            classification = entry.get("classification", "OK")
            nag = self._build_nag(classification)
            if nag != 1:     # Only annotate non-best moves with NAG
                node.nags.add(nag)

            # Set comment
            comment = self.build_comment(entry, self.mode)
            if comment:
                node.comment = comment

        # ── Export ────────────────────────────────────────────────────────────
        exporter = chess.pgn.StringExporter(
            headers   = True,
            variations= False,
            comments  = True
        )
        pgn_string = game.accept(exporter)
        return pgn_string

    @classmethod
    def build_comment(cls, entry: dict, mode: str = "Beginner") -> str:
        """
        Constructs a PGN comment string for a single review entry.

        The comment is tailored to mode:
            Beginner:     plain English, no centipawn values
            Intermediate: includes centipawn loss figure and classification label

        Parameters:
            entry  — a ReviewEntry dict from the review pipeline
            mode   — "Beginner" or "Intermediate"

        Returns:
            A comment string (without the surrounding { } — chess.pgn adds those).
        """
        classification = entry.get("classification", "OK")
        symbol         = _SYMBOL_MAP.get(classification, "")
        is_bad         = entry.get("is_bad", False)
        cp_loss        = entry.get("cp_loss", 0)
        best_move_san  = entry.get("best_move_san", "")
        move_san       = entry.get("move_san", "")
        reasons        = entry.get("reasons", [])
        expl_best      = entry.get("explanation_best", "")
        expl_user      = entry.get("explanation_user", "")

        parts = []

        if not is_bad:
            # Good move — short comment
            if mode == "Beginner":
                if expl_user:
                    parts.append(expl_user)
                else:
                    parts.append("Good move.")
            else:
                parts.append(f"Best move (0 cp loss). {expl_user}" if expl_user else "Best move.")
            return " ".join(parts)

        # Bad move — more detailed comment
        if symbol:
            parts.append(f"{symbol}")

        if mode == "Beginner":
            # Plain English — first reason only
            if reasons:
                parts.append(reasons[0])
            if best_move_san and best_move_san != move_san:
                parts.append(f"Consider {best_move_san} instead.")
        else:
            # Intermediate — include cp_loss and all reasons
            pawns = cp_loss / 100.0
            parts.append(f"[{classification} — {pawns:.1f} pawns lost]")
            for reason in reasons[:2]:           # at most 2 reasons in annotation
                parts.append(reason)
            if best_move_san and best_move_san != move_san:
                parts.append(f"Best was {best_move_san}.")
            if expl_best:
                parts.append(f"Engine idea: {expl_best}")

        comment = " ".join(parts)

        # Enforce a reasonable comment length for PGN viewers
        # (very long comments can break some GUI tools)
        if len(comment) > 300:
            comment = comment[:297] + "..."

        return comment

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_nag(classification: str) -> int:
        """
        Returns the NAG integer for a given classification string.
        Defaults to NAG 1 (good move) for unrecognised classifications.

        NAG reference:
            1  = Good move  (!)
            2  = Mistake    (?)
            4  = Blunder    (??)
            6  = Inaccuracy (?!)
        """
        return _NAG_MAP.get(classification, 1)

    @staticmethod
    def format_pgn_move_summary(review_entries: list) -> str:
        """
        Produces a plain-text tabular summary of move classifications.
        Useful as a printed appendix in the NEA document or for copy-paste
        evidence of game review functionality.

        Format:
            Move  SAN      White/Black  Class.        CP Loss
            ─────────────────────────────────────────────────
              1.  e4       White        Best              0 cp
              1.  e5       Black        Inaccuracy       42 cp
              2.  Nf3      White        Best              0 cp
              ...

        Parameters:
            review_entries  — list of ReviewEntry dicts

        Returns:
            Multi-line string table.
        """
        if not review_entries:
            return "(No review entries to display.)"

        lines = [
            f"  {'Move':>5}  {'SAN':<8}  {'Side':<6}  {'Classification':<14}  {'CP Loss':>8}",
            "  " + "─" * 58,
        ]
        for entry in review_entries:
            move_num = entry.get("move_num", 0)
            san      = entry.get("move_san", "?")
            colour   = entry.get("color", chess.WHITE)
            side     = "White" if colour == chess.WHITE else "Black"
            cls_lbl  = entry.get("classification", "OK")
            cp_loss  = entry.get("cp_loss", 0)

            icon = _SYMBOL_MAP.get(cls_lbl, "")
            lines.append(
                f"  {move_num:>5}.  {san:<8}  {side:<6}  "
                f"{cls_lbl + icon:<14}  {cp_loss:>6} cp"
            )

        lines.append("  " + "─" * 58)
        lines.append(f"  Total moves: {len(review_entries)}")
        return "\n".join(lines)
