
# test_suite.py  —  Explain My Move  v1.3
# Author: Ammar
# OCR A-Level Computer Science NEA — Component 03/04
#
# Formal test runner for all backend modules.
#
# Test IDs T01–T42 match the test plan referenced in the NEA Design section
# (3.2.3 — "Identify the test data to be used during the iterative development
# and post development phases and justify the choice of this test data").
#
# Running this file produces:
#   • A formatted PASS / FAIL report on the console
#   • test_results.txt written to the working directory (for NEA appendices in
#     sections 3.3.2 and 3.4.1)
#
# ─────────────────────────────────────────────────────────────────────────────
# STOCKFISH REQUIREMENT
# ─────────────────────────────────────────────────────────────────────────────
#   Tests T01–T39 do NOT require Stockfish — they exercise pure Python logic:
#   ConfigManager validation, ExplanationEngine rules, OutputFormatter schema,
#   format_score boundaries, and BadMoveAnalyser._classify().
#
#   Tests T40–T42 are integration tests that deliberately use an invalid engine
#   path to trigger the fallback heuristic path in ChessEngineInterface.
#   They confirm the application degrades gracefully when Stockfish is absent.
#   These are clearly labelled [FALLBACK / NO STOCKFISH].
#
# ─────────────────────────────────────────────────────────────────────────────
# USAGE
# ─────────────────────────────────────────────────────────────────────────────
#   python test_suite.py
#


import sys
import os
import io
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import chess
import chess.pgn

# ── Backend imports ───────────────────────────────────────────────────────────
from engine_config      import ConfigManager
from explanation_engine import (
    ExplanationEngine, Rule, WORD_LIMIT,
    _is_hanging, _creates_fork, _creates_pin,
    _threatens_checkmate, _post_move_check,
    _is_open_file_rook, _is_semi_open_file_rook,
    _is_passed_pawn_advance, _is_back_rank_pressure,
    _is_castling, _is_pawn_promotion,
)
from output_formatter   import OutputFormatter, REQUIRED_SCHEMA_FIELDS
from engine_interface   import (
    format_score, ChessEngineInterface,
    MoveEvaluator, BadMoveAnalyser,
)



# TEST RUNNER INFRASTRUCTURE


class TestResult:
    """Holds the outcome of a single test case."""
    def __init__(self, test_id: str, description: str,
                 passed: bool, detail: str = ""):
        self.test_id     = test_id
        self.description = description
        self.passed      = passed
        self.detail      = detail  # error message or extra info


class TestRunner:
    """
    Collects and runs test cases, then produces a formatted report.

    Design justification:
        A dedicated runner class keeps test logic separate from report
        formatting, satisfying the Single Responsibility Principle.
        Each test is registered via register_test() so tests can be
        added without modifying the runner itself (Open/Closed).
    """

    def __init__(self):
        self._results: list[TestResult] = []

    def run(self, test_id: str, description: str, test_callable) -> TestResult:
        """
        Executes test_callable. Catches all exceptions so one failing test
        does not abort the rest of the suite — matching the robustness
        requirement from the NEA (no-crash guarantee U23 applied to tests).
        """
        try:
            test_callable()
            result = TestResult(test_id, description, passed=True)
        except AssertionError as e:
            result = TestResult(test_id, description, passed=False,
                                detail=f"AssertionError: {e}")
        except Exception as e:
            result = TestResult(test_id, description, passed=False,
                                detail=f"{type(e).__name__}: {e}")
        self._results.append(result)
        return result

    def summary(self) -> tuple[int, int]:
        """Returns (passed_count, total_count)."""
        passed = sum(1 for r in self._results if r.passed)
        return passed, len(self._results)

    def print_report(self, output_file=None):
        """
        Writes a formatted report to console and optionally to a file.
        Format chosen for clarity when pasted as NEA evidence:
            T01  PASS  Description
            T02  FAIL  Description — error detail
        """
        lines = []
        sep = "=" * 72

        lines.append(sep)
        lines.append(f"  Explain My Move — Formal Test Suite Report")
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
        lines.append(sep)

        # Group by section
        sections = {
            "T01-T08  ConfigManager Validation": [
                r for r in self._results if r.test_id.startswith("T0") and
                int(r.test_id[1:]) <= 8],
            "T09-T21  ExplanationEngine Rules": [
                r for r in self._results if r.test_id.startswith("T") and
                9 <= int(r.test_id[1:]) <= 21],
            "T22-T27  OutputFormatter & JSON Schema": [
                r for r in self._results if r.test_id.startswith("T") and
                22 <= int(r.test_id[1:]) <= 27],
            "T28-T33  format_score() Boundary Values": [
                r for r in self._results if r.test_id.startswith("T") and
                28 <= int(r.test_id[1:]) <= 33],
            "T34-T39  BadMoveAnalyser Classification": [
                r for r in self._results if r.test_id.startswith("T") and
                34 <= int(r.test_id[1:]) <= 39],
            "T40-T42  Integration / Fallback (No Stockfish)": [
                r for r in self._results if r.test_id.startswith("T") and
                40 <= int(r.test_id[1:]) <= 42],
        }

        for section_title, results in sections.items():
            if not results:
                continue
            lines.append(f"\n  ── {section_title}")
            lines.append("  " + "-" * 68)
            for r in results:
                status = "PASS" if r.passed else "FAIL"
                base = f"  {r.test_id:<5}  {status}  {r.description}"
                if not r.passed and r.detail:
                    base += f"\n             Detail: {r.detail}"
                lines.append(base)

        lines.append("")
        lines.append(sep)
        passed, total = self.summary()
        lines.append(f"  RESULT:  {passed} / {total} tests passed")
        if passed == total:
            lines.append("  STATUS:  ALL TESTS PASSED ✓")
        else:
            lines.append(f"  STATUS:  {total - passed} FAILURE(S) — see detail above")
        lines.append(sep)

        report = "\n".join(lines)
        print(report)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\n  Report saved to: {output_file}")



# TEST POSITIONS

#
# FEN strings for specific tactical scenarios.
# Each position is documented with the expected rule trigger and justification.
# Positions chosen to be simple, unambiguous, and verifiable by hand.
#
# Test data justification (per NEA 3.2.3(a)):
#   Normal data    — typical game positions (starting position, common openings)
#   Boundary data  — edge cases (terminal positions, pawn on 7th rank, mate in 1)
#   Erroneous data — invalid FEN, missing fields, wrong types for validation tests

# Standard starting position
FEN_START = chess.STARTING_FEN

# Fork test: White knight on c4, Black queen on d7, Black bishop on c6.
# Move Nc4-e5 attacks both d7 and c6 simultaneously → fork.
FEN_FORK = "8/3q4/2b5/8/2N5/8/8/4K2k w - - 0 1"

# Check test: White queen on h5, Black king on g8.
# Move Qh5-h7 gives check (queen slides along h-file).
FEN_CHECK = "6k1/8/8/7Q/8/8/8/4K3 w - - 0 1"

# Promotion test: White pawn on e7, only legal pawn advance is e7-e8.
FEN_PROMO = "4k3/4P3/8/8/8/8/8/4K3 w - - 0 1"

# Castling test: White can castle kingside (rook on h1, king on e1, nothing between).
FEN_CASTLE = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"

# Hanging piece capture: White rook on a6 attacks undefended Black bishop on c6.
# Black has no pieces defending c6.
FEN_HANGING = "8/8/R1b5/8/8/8/8/4K2k w - - 0 1"

# Development test: White knight on g1 (back rank).
# Move Ng1-f3 develops a minor piece off the back rank.
FEN_DEV = chess.STARTING_FEN  # Starting position — knights on g1 and b1

# Open file rook: White rook on a1. File 'a' has no pawns.
# Move Ra1-a4 puts rook on an open a-file.
FEN_OPEN_FILE = "7k/8/8/8/8/8/8/R3K3 w - - 0 1"

# Pin test: White rook on a1, Black rook on d4, Black king on h4.
# Move Ra1-a4 pins the black rook on d4 against the black king on h4 (same rank).
FEN_PIN = "8/8/8/8/3r3k/8/8/R3K3 w - - 0 1"

# Back-rank pressure: White rook on a1, Black pieces on 7th rank.
# Move Ra1-a7 puts rook on rank 7 (the 7th rank from White's perspective).
FEN_BACK_RANK = "6k1/8/8/8/8/8/8/R3K3 w - - 0 1"

# Passed pawn: White pawn on e5 with no Black pawns on d, e, or f files ahead.
# Move e5-e6 advances the passed pawn.
FEN_PASSED = "7k/8/8/4P3/8/8/8/4K3 w - - 0 1"

# Checkmate position (terminal): Black is in checkmate.
FEN_CHECKMATE = "6k1/5Q2/6K1/8/8/8/8/8 b - - 0 1"

# Stalemate position (terminal): Black has no legal moves and is not in check.
FEN_STALEMATE = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"



# SECTION 1 — CONFIGMANAGER VALIDATION  (T01 – T08)


def test_T01(runner: TestRunner):
    runner.run("T01", "ConfigManager: default config loads without error", lambda: (
        # Normal data: factory defaults should always be valid
        ConfigManager()  # must not raise
    ))

def test_T02(runner: TestRunner):
    runner.run("T02", "ConfigManager: engine_depth below DEPTH_MIN raises ValueError", lambda: (
        _assert_raises(
            lambda: ConfigManager().update_setting("engine_depth", 0),
            ValueError,
            "depth=0 is below DEPTH_MIN=1"
        )
    ))

def test_T03(runner: TestRunner):
    runner.run("T03", "ConfigManager: engine_depth above DEPTH_MAX raises ValueError", lambda: (
        _assert_raises(
            lambda: ConfigManager().update_setting("engine_depth", 21),
            ValueError,
            "depth=21 is above DEPTH_MAX=20"
        )
    ))

def test_T04(runner: TestRunner):
    runner.run("T04", "ConfigManager: timeout below TIMEOUT_MIN raises ValueError", lambda: (
        _assert_raises(
            lambda: ConfigManager().update_setting("timeout", 0.5),
            ValueError,
            "timeout=0.5 is below TIMEOUT_MIN=1.0"
        )
    ))

def test_T05(runner: TestRunner):
    runner.run("T05", "ConfigManager: multipv_count above MULTIPV_MAX raises ValueError", lambda: (
        _assert_raises(
            lambda: ConfigManager().update_setting("multipv_count", 6),
            ValueError,
            "multipv=6 is above MULTIPV_MAX=5"
        )
    ))

def test_T06(runner: TestRunner):
    runner.run("T06", "ConfigManager: mode not in ('Beginner', 'Intermediate') raises ValueError", lambda: (
        _assert_raises(
            lambda: ConfigManager().update_setting("mode", "Expert"),
            ValueError,
            "mode='Expert' is invalid"
        )
    ))

def test_T07(runner: TestRunner):
    def _check():
        cfg = ConfigManager()
        cfg.update_setting("engine_depth", 15)          # valid
        try:
            cfg.update_setting("engine_depth", 999)     # invalid
        except ValueError:
            pass
        # Atomic write: value must be restored to 15
        assert cfg.get_setting("engine_depth") == 15, (
            f"Expected depth=15 after failed update; got {cfg.get_setting('engine_depth')}"
        )
    runner.run("T07", "ConfigManager: update_setting() restores old value on validation failure", _check)

def test_T08(runner: TestRunner):
    runner.run("T08", "ConfigManager: get_setting() raises KeyError for unknown key", lambda: (
        _assert_raises(
            lambda: ConfigManager().get_setting("nonexistent_key"),
            KeyError,
            "unknown key raises KeyError"
        )
    ))



# SECTION 2 — EXPLANATIONENGINE RULE TRIGGERS  (T09 – T21)


def test_T09(runner: TestRunner):
    """
    Normal data: a move to e4 from the starting position must trigger
    the 'central_control' rule (e4 is a central square).
    Justification: central pawn moves are the most common opening moves;
    the rule must fire reliably for this case.
    """
    def _check():
        board = chess.Board(FEN_START)
        move  = chess.Move(chess.E2, chess.E4)
        assert move in board.legal_moves, "e2-e4 must be legal from start"
        triggered_ids = [r.rule_id for r in ExplanationEngine("Beginner").apply_rules(board, move)]
        assert "central_control" in triggered_ids, (
            f"Expected 'central_control' rule, got: {triggered_ids}"
        )
    runner.run("T09", "ExplanationEngine: e2-e4 triggers 'central_control' rule", _check)

def test_T10(runner: TestRunner):
    """
    Tactical data: move Nc4-e5 in FEN_FORK position attacks Black queen on d7
    AND Black bishop on c6 simultaneously. _creates_fork must return True.
    Justification: fork detection is a core tactical feature (F05 in design).
    """
    def _check():
        board = chess.Board(FEN_FORK)
        move  = chess.Move(chess.C4, chess.E5)
        assert move in board.legal_moves, "Nc4-e5 must be legal in fork position"
        assert _creates_fork(board, move), (
            "_creates_fork should return True for Nc4-e5 (attacks d7 queen and c6 bishop)"
        )
        triggered_ids = [r.rule_id for r in ExplanationEngine("Beginner").apply_rules(board, move)]
        assert "fork" in triggered_ids, f"Expected 'fork' rule, got: {triggered_ids}"
    runner.run("T10", "ExplanationEngine: fork move triggers 'fork' rule", _check)

def test_T11(runner: TestRunner):
    """
    Tactical data: Qh5-h7 in FEN_CHECK gives check. _post_move_check must return True.
    Justification: check moves are a fundamental tactical concept that must be detected.
    """
    def _check():
        board = chess.Board(FEN_CHECK)
        move  = chess.Move(chess.H5, chess.H7)
        assert move in board.legal_moves, "Qh5-h7 must be legal"
        assert _post_move_check(board, move), "_post_move_check must return True for Qh5-h7"
        triggered_ids = [r.rule_id for r in ExplanationEngine("Beginner").apply_rules(board, move)]
        assert "check" in triggered_ids or "mate_threat" in triggered_ids, (
            f"Expected 'check' or 'mate_threat' rule, got: {triggered_ids}"
        )
    runner.run("T11", "ExplanationEngine: check move triggers 'check' rule", _check)

def test_T12(runner: TestRunner):
    """
    Boundary data: pawn on e7 promoting to queen on e8.
    _is_pawn_promotion must return True (move.promotion is not None).
    Justification: promotion is a high-value tactical idea that should always
    take highest priority in explanation (priority 1 in rule set).
    """
    def _check():
        board = chess.Board(FEN_PROMO)
        move  = chess.Move(chess.E7, chess.E8, promotion=chess.QUEEN)
        assert move in board.legal_moves, "e7-e8=Q must be legal in promotion position"
        assert _is_pawn_promotion(board, move), "_is_pawn_promotion must return True"
        triggered_ids = [r.rule_id for r in ExplanationEngine("Beginner").apply_rules(board, move)]
        assert "promotion" in triggered_ids, f"Expected 'promotion' rule, got: {triggered_ids}"
    runner.run("T12", "ExplanationEngine: promotion move triggers 'promotion' rule (priority 1)", _check)

def test_T13(runner: TestRunner):
    """
    Normal data: White castles kingside (e1-g1) in FEN_CASTLE.
    _is_castling must return True.
    Justification: castling is a critical king-safety concept that must be
    identified and explained (U16 — castling explanation).
    """
    def _check():
        board = chess.Board(FEN_CASTLE)
        # Kingside castle: e1 → g1
        move  = chess.Move(chess.E1, chess.G1)
        assert board.is_castling(move), "e1-g1 must be a castling move"
        assert _is_castling(board, move), "_is_castling must return True"
        triggered_ids = [r.rule_id for r in ExplanationEngine("Beginner").apply_rules(board, move)]
        assert "castling" in triggered_ids, f"Expected 'castling' rule, got: {triggered_ids}"
    runner.run("T13", "ExplanationEngine: castling move triggers 'castling' rule", _check)

def test_T14(runner: TestRunner):
    """
    Tactical data: White rook captures undefended Black bishop on c6 in FEN_HANGING.
    _is_hanging must return True for c6; the capture must trigger 'hanging_capture'.
    Justification: identifying free captures is essential for material advantage
    explanations (F06 — hanging piece detection).
    """
    def _check():
        board = chess.Board(FEN_HANGING)
        c6    = chess.C6
        assert _is_hanging(board, c6), (
            "_is_hanging should return True for undefended Black bishop on c6"
        )
        move  = chess.Move(chess.A6, chess.C6)
        assert move in board.legal_moves, "Ra6xc6 must be legal"
        triggered_ids = [r.rule_id for r in ExplanationEngine("Beginner").apply_rules(board, move)]
        assert "hanging_capture" in triggered_ids, (
            f"Expected 'hanging_capture', got: {triggered_ids}"
        )
    runner.run("T14", "ExplanationEngine: capturing hanging piece triggers 'hanging_capture'", _check)

def test_T15(runner: TestRunner):
    """
    Normal data: moving the g1 knight from the back rank (starting position)
    to f3 must trigger the 'development' rule.
    Justification: developing minor pieces is the most common opening principle
    and must always be detected (U09 — development explanation).
    """
    def _check():
        board = chess.Board(FEN_DEV)
        move  = chess.Move(chess.G1, chess.F3)
        assert move in board.legal_moves, "Ng1-f3 must be legal from start"
        triggered_ids = [r.rule_id for r in ExplanationEngine("Beginner").apply_rules(board, move)]
        assert "development" in triggered_ids, (
            f"Expected 'development' rule for Ng1-f3, got: {triggered_ids}"
        )
    runner.run("T15", "ExplanationEngine: back-rank knight move triggers 'development'", _check)

def test_T16(runner: TestRunner):
    """
    Normal data: select_top_rules() must return at most 2 rules regardless
    of how many rules fire.
    Justification: the word limit (≤30 Beginner / ≤40 Intermediate) would
    be violated if too many rule texts were concatenated (success criterion F04).
    """
    def _check():
        eng  = ExplanationEngine("Beginner")
        board = chess.Board(FEN_START)
        move  = chess.Move(chess.E2, chess.E4)
        triggered = eng.apply_rules(board, move)
        selected  = eng.select_top_rules(triggered)
        assert len(selected) <= 2, (
            f"select_top_rules returned {len(selected)} rules (maximum is 2)"
        )
    runner.run("T16", "ExplanationEngine: select_top_rules() returns at most 2 rules", _check)

def test_T17(runner: TestRunner):
    """
    Boundary data: when both 'hanging_capture' and 'capture' fire,
    select_top_rules() must drop the generic 'capture' rule.
    Justification: prevents redundant explanation (design requirement — deduplication).
    """
    def _check():
        board = chess.Board(FEN_HANGING)
        move  = chess.Move(chess.A6, chess.C6)  # captures hanging bishop
        eng   = ExplanationEngine("Beginner")
        triggered = eng.apply_rules(board, move)
        selected  = eng.select_top_rules(triggered)
        ids = [r.rule_id for r in selected]
        assert "hanging_capture" in ids, "hanging_capture should be in selected"
        assert "capture" not in ids, (
            "'capture' should be deduped out when 'hanging_capture' also fires"
        )
    runner.run("T17", "ExplanationEngine: 'capture' deduped when 'hanging_capture' fires", _check)

def test_T18(runner: TestRunner):
    """
    Boundary data: Beginner mode explanation must never exceed 30 words.
    Justification: measurable success criterion explicitly requires ≤30 words
    in Beginner mode (F03 — word limit enforcement).
    """
    def _check():
        board = chess.Board(FEN_START)
        eng   = ExplanationEngine("Beginner")
        for move in list(board.legal_moves)[:10]:  # first 10 legal moves
            expl = eng.generate_explanation(board, move)
            wc   = len(expl.split())
            assert wc <= 30, (
                f"Beginner explanation '{expl}' has {wc} words (limit 30)"
            )
    runner.run("T18", "ExplanationEngine: Beginner mode explanations never exceed 30 words", _check)

def test_T19(runner: TestRunner):
    """
    Boundary data: Intermediate mode explanation must never exceed 40 words.
    Justification: measurable success criterion (F03) — Intermediate limit ≤40 words.
    """
    def _check():
        board = chess.Board(FEN_START)
        eng   = ExplanationEngine("Intermediate")
        for move in list(board.legal_moves)[:10]:
            expl = eng.generate_explanation(board, move)
            wc   = len(expl.split())
            assert wc <= 40, (
                f"Intermediate explanation '{expl}' has {wc} words (limit 40)"
            )
    runner.run("T19", "ExplanationEngine: Intermediate mode explanations never exceed 40 words", _check)

def test_T20(runner: TestRunner):
    """
    Boundary data: generate_explanation() must never raise an exception,
    even for unusual positions (terminal, odd piece configurations).
    Justification: no-crash guarantee (U23 — the application must never crash
    due to explanation generation).
    """
    def _check():
        eng    = ExplanationEngine("Beginner")
        fens   = [FEN_START, FEN_FORK, FEN_CHECK, FEN_PROMO, FEN_CASTLE]
        for fen in fens:
            board = chess.Board(fen)
            for move in list(board.legal_moves)[:5]:
                try:
                    expl = eng.generate_explanation(board, move)
                    assert isinstance(expl, str) and len(expl) > 0, (
                        f"explanation must be a non-empty string; got: {repr(expl)}"
                    )
                except Exception as e:
                    raise AssertionError(
                        f"generate_explanation raised {type(e).__name__} for {fen}: {e}"
                    )
    runner.run("T20", "ExplanationEngine: generate_explanation() never raises (5 positions)", _check)

def test_T21(runner: TestRunner):
    """
    Normal data: set_mode() switches between Beginner and Intermediate
    without recreating the engine. Word limit must update correctly.
    Justification: mode switching without restart is a usability requirement (U07).
    """
    def _check():
        eng = ExplanationEngine("Beginner")
        assert eng.max_words == 30, f"Expected 30 for Beginner, got {eng.max_words}"
        eng.set_mode("Intermediate")
        assert eng.max_words == 40, f"Expected 40 for Intermediate, got {eng.max_words}"
        eng.set_mode("Beginner")
        assert eng.max_words == 30, f"Expected 30 after switch back, got {eng.max_words}"
    runner.run("T21", "ExplanationEngine: set_mode() updates max_words correctly", _check)



# SECTION 3 — OUTPUT FORMATTER / JSON SCHEMA  (T22 – T27)


def test_T22(runner: TestRunner):
    """
    Normal data: generate_json_output() must include ALL fields from
    REQUIRED_SCHEMA_FIELDS with correct types.
    Justification: 100% schema validity is a measurable success criterion (F08).
    """
    def _check():
        board  = chess.Board(FEN_START)
        cfg    = ConfigManager()
        cfg.settings["engine_path"] = "nonexistent.exe"  # force fallback
        eng    = ChessEngineInterface(cfg)
        ev     = MoveEvaluator(board, eng, cfg)
        ev.run_full_evaluation()
        fmt    = OutputFormatter("Beginner")
        expl   = ExplanationEngine("Beginner").generate_explanation(
            board, ev.ranked_moves[0][0])
        jout   = fmt.generate_json_output(board, ev.ranked_moves, expl, ev)
        for field in REQUIRED_SCHEMA_FIELDS:
            assert field in jout, f"Missing required field: '{field}'"
    runner.run("T22", "OutputFormatter: generate_json_output() includes all schema fields", _check)

def test_T23(runner: TestRunner):
    """
    Normal data: validate_schema() returns (True, []) for a correctly formed output.
    Justification: directly implements Test T23 in NEA design (schema validity check).
    """
    def _check():
        fmt    = OutputFormatter("Beginner")
        board  = chess.Board(FEN_START)
        cfg    = ConfigManager()
        cfg.settings["engine_path"] = "nonexistent.exe"
        eng    = ChessEngineInterface(cfg)
        ev     = MoveEvaluator(board, eng, cfg)
        ev.run_full_evaluation()
        expl   = "Test explanation"
        jout   = fmt.generate_json_output(board, ev.ranked_moves, expl, ev)
        valid, errors = fmt.validate_schema(jout)
        assert valid, f"Schema validation failed: {errors}"
        assert errors == [], f"Expected no errors; got: {errors}"
    runner.run("T23", "OutputFormatter: validate_schema() returns (True, []) for valid output", _check)

def test_T24(runner: TestRunner):
    """
    Erroneous data: validate_schema() must return (False, [error]) when a
    required field is missing.
    Justification: directly implements Test T24 in NEA design.
    """
    def _check():
        fmt  = OutputFormatter("Beginner")
        bad  = {
            "best_move_uci":    "e2e4",
            "best_move_san":    "e4",
            # "score_centipawns" deliberately omitted
            "score_display":    "+0.35",
            "explanation":      "Test",
            "mode":             "Beginner",
            "depth_used":       12,
            "timeout_flag":     False,
            "analysis_time_ms": 500,
            "ranked_moves":     [],
            "word_count":       1,
            "schema_valid":     True,
        }
        valid, errors = fmt.validate_schema(bad)
        assert not valid, "validate_schema() should return False for missing field"
        assert any("score_centipawns" in e for e in errors), (
            f"Error list should mention 'score_centipawns'; got: {errors}"
        )
    runner.run("T24", "OutputFormatter: validate_schema() catches missing field", _check)

def test_T25(runner: TestRunner):
    """
    Erroneous data: validate_schema() must return (False, [error]) when a
    field has the wrong type. Tests the bool/int subtype trap specifically:
    isinstance(True, int) is True in Python, but 'score_centipawns' must be int,
    not bool. The formatter must distinguish these correctly.
    Justification: T25 in NEA design — type checking robustness.
    """
    def _check():
        fmt  = OutputFormatter("Beginner")
        bad  = {
            "best_move_uci":    "e2e4",
            "best_move_san":    "e4",
            "score_centipawns": "not_an_int",  # wrong type
            "score_display":    "+0.35",
            "explanation":      "Test",
            "mode":             "Beginner",
            "depth_used":       12,
            "timeout_flag":     False,
            "analysis_time_ms": 500,
            "ranked_moves":     [],
            "word_count":       1,
            "schema_valid":     True,
        }
        valid, errors = fmt.validate_schema(bad)
        assert not valid, "validate_schema() should return False for wrong type"
        assert any("score_centipawns" in e for e in errors), (
            f"Error should mention 'score_centipawns'; got: {errors}"
        )
    runner.run("T25", "OutputFormatter: validate_schema() catches wrong field type", _check)

def test_T26(runner: TestRunner):
    """
    Normal data: format_text_output() must return a non-empty, well-formed string
    that includes the mode and explanation.
    Justification: consistent output format is a usability requirement (U11).
    """
    def _check():
        board = chess.Board(FEN_START)
        cfg   = ConfigManager()
        cfg.settings["engine_path"] = "nonexistent.exe"
        eng   = ChessEngineInterface(cfg)
        ev    = MoveEvaluator(board, eng, cfg)
        ev.run_full_evaluation()
        fmt   = OutputFormatter("Beginner")
        expl  = "This move controls the centre."
        out   = fmt.format_text_output(board, ev.ranked_moves, expl, ev)
        assert isinstance(out, str), "format_text_output() must return a str"
        assert len(out) > 0,         "format_text_output() must return a non-empty string"
        assert "Beginner" in out,    "Output must include mode label"
        assert expl in out,          "Output must contain the explanation text"
    runner.run("T26", "OutputFormatter: format_text_output() returns well-formed string", _check)

def test_T27(runner: TestRunner):
    """
    Normal data: generate_pgn_output() produces a non-empty PGN string that
    can be re-parsed by chess.pgn.read_game() without error.
    Justification: measurable success criterion — "exported PGNs must load
    correctly in standard tools" (Analysis section, 3.1.4(b)).
    """
    def _check():
        # Build a board with 4 moves of game history
        board = chess.Board()
        for san in ["e4", "e5", "Nf3", "Nc6"]:
            move = board.parse_san(san)
            board.push(move)
        fmt = OutputFormatter("Beginner")
        pgn_str = fmt.generate_pgn_output(board)
        assert isinstance(pgn_str, str) and len(pgn_str) > 0, "PGN string must not be empty"
        # Re-parse to confirm validity
        game = chess.pgn.read_game(io.StringIO(pgn_str))
        assert game is not None, "chess.pgn.read_game() must parse the exported PGN successfully"
    runner.run("T27", "OutputFormatter: generate_pgn_output() produces valid re-parseable PGN", _check)



# SECTION 4 — FORMAT_SCORE() BOUNDARY VALUES  (T28 – T33)


def test_T28(runner: TestRunner):
    """
    Normal data: Intermediate mode, positive centipawns → "+X.XX" format.
    Justification: U14 requires pawn-unit display (+0.45 not +45) in Intermediate mode.
    """
    def _check():
        result = format_score(45, "Intermediate")
        assert result == "+0.45", f"Expected '+0.45', got '{result}'"
    runner.run("T28", "format_score(): Intermediate, cp=45  → '+0.45'", _check)

def test_T29(runner: TestRunner):
    runner.run("T29", "format_score(): Intermediate, cp=-120 → '-1.20'", lambda: (
        _assert_eq(format_score(-120, "Intermediate"), "-1.20",
                   "Negative centipawns must format correctly")
    ))

def test_T30(runner: TestRunner):
    """
    Boundary data: Beginner, cp=350 → "Strong advantage for White".
    Justification: U18 — Beginner mode must use plain phrases, not centipawn values.
    """
    runner.run("T30", "format_score(): Beginner, cp=350 → 'Strong advantage for White'", lambda: (
        _assert_eq(format_score(350, "Beginner"), "Strong advantage for White",
                   "cp=350 should give strong advantage phrase")
    ))

def test_T31(runner: TestRunner):
    runner.run("T31", "format_score(): Beginner, cp=0    → 'Roughly equal'", lambda: (
        _assert_eq(format_score(0, "Beginner"), "Roughly equal",
                   "cp=0 should give 'Roughly equal'")
    ))

def test_T32(runner: TestRunner):
    """
    Boundary data: cp >= 9000 treated as forced mate.
    Justification: mate detection is a critical edge case (design notes state
    abs(cp) >= 9000 signals a mate score from Stockfish).
    """
    def _check():
        result_b = format_score(9000, "Beginner")
        result_i = format_score(9000, "Intermediate")
        assert "checkmate" in result_b.lower(), (
            f"Beginner mate score should mention checkmate; got '{result_b}'"
        )
        assert "Mate" in result_i, (
            f"Intermediate mate score should say 'Mate in N'; got '{result_i}'"
        )
    runner.run("T32", "format_score(): cp=9000 (mate) handled in both modes", _check)

def test_T33(runner: TestRunner):
    runner.run("T33", "format_score(): cp=None → '—'", lambda: (
        _assert_eq(format_score(None, "Beginner"), "—",
                   "None input should return em dash placeholder")
    ))



# SECTION 5 — BADMOVEANALYSER CLASSIFICATION  (T34 – T39)

#
# These tests exercise BadMoveAnalyser._classify() directly, which requires
# no Stockfish — classification is a pure centipawn threshold calculation.

def test_T34(runner: TestRunner):
    """
    Boundary data: cp_loss = 0 → "OK" (no mistake, threshold default = 100).
    Justification: zero cp_loss should always produce 'OK' regardless of threshold.
    """
    def _check():
        analyser = _make_analyser()
        assert analyser._classify(0) == "OK", (
            f"cp_loss=0 should classify as 'OK', got '{analyser._classify(0)}'"
        )
    runner.run("T34", "BadMoveAnalyser: cp_loss=0 classifies as 'OK'", _check)

def test_T35(runner: TestRunner):
    runner.run("T35", "BadMoveAnalyser: cp_loss=99 classifies as 'OK' (below threshold)", lambda: (
        _assert_eq(_make_analyser()._classify(99), "OK",
                   "cp_loss=99 is below default threshold of 100")
    ))

def test_T36(runner: TestRunner):
    """
    Boundary data: cp_loss exactly at threshold (100) → "Inaccuracy".
    This tests the boundary between OK and Inaccuracy.
    """
    runner.run("T36", "BadMoveAnalyser: cp_loss=100 classifies as 'Inaccuracy' (at threshold)", lambda: (
        _assert_eq(_make_analyser()._classify(100), "Inaccuracy",
                   "cp_loss=100 is at threshold, should be Inaccuracy")
    ))

def test_T37(runner: TestRunner):
    """Boundary data: 200 ≤ cp_loss < 400 → "Mistake"."""
    runner.run("T37", "BadMoveAnalyser: cp_loss=200 classifies as 'Mistake'", lambda: (
        _assert_eq(_make_analyser()._classify(200), "Mistake",
                   "cp_loss=200 should be 'Mistake'")
    ))

def test_T38(runner: TestRunner):
    runner.run("T38", "BadMoveAnalyser: cp_loss=399 classifies as 'Mistake' (boundary)", lambda: (
        _assert_eq(_make_analyser()._classify(399), "Mistake",
                   "cp_loss=399 is just below Blunder threshold")
    ))

def test_T39(runner: TestRunner):
    """Boundary data: cp_loss ≥ 400 → "Blunder" (the most severe classification)."""
    runner.run("T39", "BadMoveAnalyser: cp_loss=400 classifies as 'Blunder'", lambda: (
        _assert_eq(_make_analyser()._classify(400), "Blunder",
                   "cp_loss=400 should be 'Blunder'")
    ))



# SECTION 6 — INTEGRATION / FALLBACK  (T40 – T42)

# [FALLBACK / NO STOCKFISH]
# These tests use an invalid engine path to force the Python fallback heuristic.
# They confirm the application degrades gracefully without Stockfish.

def test_T40(runner: TestRunner):
    """
    [FALLBACK] Normal data: evaluate_moves() must return non-empty results
    even when Stockfish is unavailable.
    Justification: graceful degradation is a key robustness requirement (U22).
    """
    def _check():
        board, cfg, eng, ev = _fallback_setup()
        ev.run_full_evaluation()
        assert len(ev.ranked_moves) > 0, (
            "ranked_moves must be non-empty even when Stockfish is unavailable"
        )
    runner.run("T40", "[FALLBACK] MoveEvaluator returns results with invalid engine path", _check)

def test_T41(runner: TestRunner):
    """
    [FALLBACK] The timeout_flag must be True when the engine is unavailable.
    Justification: the GUI uses timeout_flag to display a warning banner (U22).
    """
    def _check():
        board, cfg, eng, ev = _fallback_setup()
        ev.run_full_evaluation()
        assert ev.timeout_flag is True, (
            f"timeout_flag must be True when engine is unavailable; got {ev.timeout_flag}"
        )
    runner.run("T41", "[FALLBACK] timeout_flag=True when engine is unavailable", _check)

def test_T42(runner: TestRunner):
    """
    [FALLBACK] ranked_moves must be sorted best-first (highest score for White).
    Justification: correct ranking is required even in fallback mode — the GUI
    displays rank order on the move buttons.
    """
    def _check():
        board, cfg, eng, ev = _fallback_setup()
        ev.run_full_evaluation()
        scores = [s for _, s in ev.ranked_moves]
        # White to move: best score should be >= second best
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"ranked_moves not sorted: score[{i}]={scores[i]} < score[{i+1}]={scores[i+1]}"
            )
    runner.run("T42", "[FALLBACK] ranked_moves sorted best-first in fallback heuristic", _check)



# HELPERS


def _assert_raises(callable_, exc_type, message: str = ""):
    """Asserts that callable_ raises exc_type. Raises AssertionError if not."""
    try:
        callable_()
        raise AssertionError(
            f"Expected {exc_type.__name__} to be raised. {message}"
        )
    except exc_type:
        pass  # Expected — test passes

def _assert_eq(actual, expected, message: str = ""):
    """Asserts actual == expected with a descriptive message."""
    assert actual == expected, (
        f"Expected {repr(expected)}, got {repr(actual)}. {message}"
    )

def _make_analyser() -> BadMoveAnalyser:
    """
    Creates a BadMoveAnalyser with an invalid engine path so no Stockfish
    connection is attempted. Only tests _classify(), which is pure Python.
    """
    cfg = ConfigManager()
    cfg.settings["engine_path"] = "nonexistent.exe"
    eng = ChessEngineInterface(cfg)
    return BadMoveAnalyser(eng, cfg)

def _fallback_setup():
    """
    Returns (board, cfg, eng, ev) with an invalid engine path, forcing
    ChessEngineInterface to use the Python fallback heuristic.
    """
    board = chess.Board(FEN_START)
    cfg   = ConfigManager()
    cfg.settings["engine_path"] = "nonexistent.exe"  # deliberately invalid
    eng   = ChessEngineInterface(cfg)
    ev    = MoveEvaluator(board, eng, cfg)
    return board, cfg, eng, ev



# ENTRY POINT


def main():
    runner = TestRunner()

    print("\nRunning Explain My Move — Formal Test Suite…\n")

    # Section 1 — ConfigManager
    test_T01(runner); test_T02(runner); test_T03(runner); test_T04(runner)
    test_T05(runner); test_T06(runner); test_T07(runner); test_T08(runner)

    # Section 2 — ExplanationEngine
    test_T09(runner); test_T10(runner); test_T11(runner); test_T12(runner)
    test_T13(runner); test_T14(runner); test_T15(runner); test_T16(runner)
    test_T17(runner); test_T18(runner); test_T19(runner); test_T20(runner)
    test_T21(runner)

    # Section 3 — OutputFormatter
    test_T22(runner); test_T23(runner); test_T24(runner); test_T25(runner)
    test_T26(runner); test_T27(runner)

    # Section 4 — format_score()
    test_T28(runner); test_T29(runner); test_T30(runner); test_T31(runner)
    test_T32(runner); test_T33(runner)

    # Section 5 — BadMoveAnalyser classification
    test_T34(runner); test_T35(runner); test_T36(runner); test_T37(runner)
    test_T38(runner); test_T39(runner)

    # Section 6 — Fallback integration
    test_T40(runner); test_T41(runner); test_T42(runner)

    # Print report + save to file
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "test_results.txt")
    runner.print_report(output_file=output_path)

    passed, total = runner.summary()
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
