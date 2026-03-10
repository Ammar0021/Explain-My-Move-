# Explain My Move  v1.3  (Final)
# Module structure
# ─────────────────────────────────────────────────────────────────────────────
#   explain_my_move.py    ← this file  (GUI layer)
#   explanation_engine.py ← Rule, ExplanationEngine     (Design Classes 3 & 4)
#   engine_config.py      ← ConfigManager, path helper  (Design Class 5)
#   engine_interface.py   ← ChessEngineInterface, MoveEvaluator,
#                            BadMoveAnalyser, format_score (Classes 1, 2, 7)
#   output_formatter.py   ← OutputFormatter             (Design Class 6)
#
# v1.3 changes over v1.3
# ─────────────────────────────────────────────────────────────────────────────
#   • "Check My Move" tab removed — bad-move analysis is now integrated
#     directly into the Analyse tab (same experience, unified workflow)
#   • PGN Game Review mode: analyses every move in a game, shows per-move
#     classification (Brilliant / Best / Good / Inaccuracy / Mistake / Blunder)
#     and explanation for both the engine's best move and the player's move
#     — similar to chess.com's game review
#   • Explanation output redesigned — clean card layout showing:
#       move badge  |  evaluation bar  |  explanation text
#     No more console-log-style output
#   • Buttons completely restyled using rounded tk.Canvas pill buttons
#   • About page redesigned — contextual project description, no OOP list
#   • All version strings updated to v1.3

import tkinter as tk
from tkinter import ttk, messagebox
import chess
import chess.pgn
import threading
import io

from engine_config      import ConfigManager, APP_VERSION
from engine_interface   import ChessEngineInterface, MoveEvaluator, BadMoveAnalyser
from output_formatter   import OutputFormatter
from explanation_engine import ExplanationEngine


 
# LAYOUT CONSTANTS
 

BOARD_PX  = 480
SQ        = BOARD_PX // 8      # 60 px per square
GUTTER    = 22                  # rank/file label strip
EVAL_W    = 16                  # eval bar width

PIECES = {
    chess.PAWN:   ("♙", "♟"),
    chess.ROOK:   ("♖", "♜"),
    chess.KNIGHT: ("♘", "♞"),
    chess.BISHOP: ("♗", "♝"),
    chess.QUEEN:  ("♕", "♛"),
    chess.KING:   ("♔", "♚"),
}

# Move classification metadata
CLASSIFICATIONS = {
    "Brilliant":  {"icon": "!!",  "color_l": "#1B998B", "color_d": "#2DD4BF"},
    "Best":       {"icon": "★",   "color_l": "#16A34A", "color_d": "#4ADE80"},
    "Good":       {"icon": "✓",   "color_l": "#2563EB", "color_d": "#60A5FA"},
    "Inaccuracy": {"icon": "?!",  "color_l": "#D97706", "color_d": "#FBB040"},
    "Mistake":    {"icon": "?",   "color_l": "#EA580C", "color_d": "#FB923C"},
    "Blunder":    {"icon": "??",  "color_l": "#DC2626", "color_d": "#F87171"},
    "OK":         {"icon": "✓",   "color_l": "#16A34A", "color_d": "#4ADE80"},
}


 
# COLOUR PALETTES
 

LIGHT = {
    "root":           "#F0F4F8",
    "header":         "#162032",
    "header_fg":      "#F8FAFC",
    "header_accent":  "#38BDF8",
    "panel":          "#FFFFFF",
    "card":           "#FFFFFF",
    "card_border":    "#E2E8F0",
    "card2":          "#F8FAFC",
    "fg":             "#1E293B",
    "fg_muted":       "#64748B",
    "fg_head":        "#0F172A",
    "primary":        "#2563EB",
    "primary_fg":     "#FFFFFF",
    "primary_dark":   "#1D4ED8",
    "success":        "#16A34A",
    "success_fg":     "#FFFFFF",
    "danger":         "#DC2626",
    "danger_fg":      "#FFFFFF",
    "warning":        "#D97706",
    "warning_fg":     "#FFFFFF",
    "teal":           "#0D9488",
    "teal_fg":        "#FFFFFF",
    "b_ghost":        "#F1F5F9",
    "b_ghost_fg":     "#475569",
    "ready":          "#16A34A",
    "thinking":       "#D97706",
    "fallback":       "#DC2626",
    "board_bg":       "#1A1A2E",
    "sq_light":       "#F0D9B5",
    "sq_dark":        "#B58863",
    "sq_from":        "#F6F64A",
    "sq_to":          "#BACA2B",
    "sq_bad":         "#FF6B6B",
    "sq_best":        "#4ADE80",
    "coord":          "#999999",
    "eval_w":         "#F1F5F9",
    "eval_b":         "#1A1A2E",
    "eval_mid":       "#94A3B8",
    "out_bg":         "#FAFAFA",
    "out_fg":         "#1E293B",
    "in_bg":          "#FFFFFF",
    "in_border":      "#CBD5E1",
    "sep":            "#E2E8F0",
    "r1":             "#16A34A",
    "r2":             "#2563EB",
    "r3":             "#7C3AED",
    "tag_bg":         "#EFF6FF",
    "tag_fg":         "#1D4ED8",
    "review_bg":      "#F8FAFC",
    "review_border":  "#E2E8F0",
    "nb_bg":          "#F0F4F8",
}

DARK = {
    "root":           "#090E1A",
    "header":         "#050810",
    "header_fg":      "#F1F5F9",
    "header_accent":  "#38BDF8",
    "panel":          "#111827",
    "card":           "#1E293B",
    "card_border":    "#2D3F55",
    "card2":          "#162032",
    "fg":             "#E2E8F0",
    "fg_muted":       "#94A3B8",
    "fg_head":        "#F8FAFC",
    "primary":        "#3B82F6",
    "primary_fg":     "#FFFFFF",
    "primary_dark":   "#2563EB",
    "success":        "#22C55E",
    "success_fg":     "#FFFFFF",
    "danger":         "#EF4444",
    "danger_fg":      "#FFFFFF",
    "warning":        "#F59E0B",
    "warning_fg":     "#FFFFFF",
    "teal":           "#14B8A6",
    "teal_fg":        "#FFFFFF",
    "b_ghost":        "#1E293B",
    "b_ghost_fg":     "#CBD5E1",
    "ready":          "#4ADE80",
    "thinking":       "#FBB040",
    "fallback":       "#F87171",
    "board_bg":       "#060A14",
    "sq_light":       "#C9B07A",
    "sq_dark":        "#7A5A38",
    "sq_from":        "#E6E030",
    "sq_to":          "#8DB040",
    "sq_bad":         "#EF4444",
    "sq_best":        "#22C55E",
    "coord":          "#555555",
    "eval_w":         "#E2E8F0",
    "eval_b":         "#060A14",
    "eval_mid":       "#475569",
    "out_bg":         "#0F172A",
    "out_fg":         "#E2E8F0",
    "in_bg":          "#0F172A",
    "in_border":      "#334155",
    "sep":            "#1E293B",
    "r1":             "#4ADE80",
    "r2":             "#60A5FA",
    "r3":             "#C084FC",
    "tag_bg":         "#1E3A5F",
    "tag_fg":         "#93C5FD",
    "review_bg":      "#111827",
    "review_border":  "#1E293B",
    "nb_bg":          "#090E1A",
}


 
# STYLED BUTTON  — tk.Button with hover feedback and theme support
#
# Replaces the previous PillButton (Canvas subclass) which caused:
#   _tkinter.TclError: bad argument "67": must be name of window
# when running as a PyInstaller .exe.  Canvas-based custom widgets require
# the Tcl window to be fully registered before .pack()/.grid() is called,
# which is not guaranteed in a compiled entry point.
#
# tk.Button is natively handled by Tkinter/Tcl and is always safe to pack
# immediately. We achieve the modern look via flat relief, padx/pady, a
# hand cursor, and Enter/Leave hover bindings that swap the background.
 

class PillButton(tk.Button):
    """
    A styled tk.Button that mimics a pill/rounded button appearance.
    Uses flat relief + hover colour swap for a modern look.
    Named PillButton to keep all call sites unchanged.

    Supports:
        update_palette(palette, style)  — re-theme on dark mode toggle
        config(state=DISABLED/NORMAL)   — enable/disable with visual feedback
    """

    _STYLE_MAP = {
        "primary": ("primary",  "primary_fg",  "primary_dark"),
        "success": ("success",  "success_fg",  "success"),
        "danger":  ("danger",   "danger_fg",   "danger"),
        "teal":    ("teal",     "teal_fg",     "teal"),
        "warning": ("warning",  "warning_fg",  "warning"),
        "ghost":   ("b_ghost",  "b_ghost_fg",  "card_border"),
    }

    def __init__(self, parent, text, command, palette,
                 style="ghost", font=("Segoe UI", 10, "bold"),
                 width=None, height=32, icon="", **kw):
        self._p      = palette
        self._style  = style
        self._label  = (icon + "  " + text) if icon else text
        self._disabled_flag = False

        bg, fg, hv = self._resolve(palette, style)
        self._bg = bg
        self._fg = fg
        self._hv = hv

        btn_kw = dict(
            text=self._label,
            command=command,
            font=font,
            bg=bg, fg=fg,
            activebackground=hv,
            activeforeground=fg,
            relief=tk.FLAT,
            bd=0,
            padx=14, pady=5,
            cursor="hand2",
            takefocus=0,
        )
        if width:
            btn_kw["width"] = width

        # Strip any kwargs that tk.Button doesn't accept
        kw.pop("highlightthickness", None)

        super().__init__(parent, **btn_kw)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _resolve(self, p, style):
        keys = self._STYLE_MAP.get(style, self._STYLE_MAP["ghost"])
        bg = p.get(keys[0], p["b_ghost"])
        fg = p.get(keys[1], p["b_ghost_fg"])
        hv = p.get(keys[2], p["card_border"])
        return bg, fg, hv

    def _on_enter(self, e):
        if not self._disabled_flag:
            self.configure(bg=self._hv, activebackground=self._hv)

    def _on_leave(self, e):
        if not self._disabled_flag:
            self.configure(bg=self._bg, activebackground=self._hv)

    def update_palette(self, palette, style=None):
        """Re-apply colours after a dark/light mode switch."""
        self._p = palette
        s = style or self._style
        bg, fg, hv = self._resolve(palette, s)
        self._bg = bg
        self._fg = fg
        self._hv = hv
        if self._disabled_flag:
            self.configure(
                bg=palette.get("card_border", "#cccccc"),
                fg=palette.get("fg_muted", "#888888"),
                activebackground=palette.get("card_border", "#cccccc"),
            )
        else:
            self.configure(bg=bg, fg=fg, activebackground=hv, activeforeground=fg)

    def config(self, **kw):
        """
        Extended config: intercepts state= to also swap visual appearance.
        All other kwargs are forwarded to tk.Button.config() unchanged.
        """
        if "state" in kw:
            state = kw["state"]
            if state == tk.DISABLED:
                self._disabled_flag = True
                kw.setdefault("bg",              self._p.get("card_border", "#cccccc"))
                kw.setdefault("fg",              self._p.get("fg_muted",    "#888888"))
                kw.setdefault("activebackground", kw["bg"])
            else:
                self._disabled_flag = False
                kw.setdefault("bg",              self._bg)
                kw.setdefault("fg",              self._fg)
                kw.setdefault("activebackground", self._hv)
        super().config(**kw)


 
# MAIN APPLICATION
 

class ExplainMyMoveApp:
    """
    Explain My Move v1.3 — main application controller.

    Single Analyse tab handles both FEN and PGN input:
        FEN mode  → analyses position, shows best move explanation card
        PGN mode  → game review — classifies every move like chess.com,
                    shows per-move explanation for both player and engine
    """

    def __init__(self, root: tk.Tk):
        self.root   = root
        self._dark  = True
        self.p      = DARK

        # Backend
        self._cfg    = ConfigManager()
        self._eng    = ChessEngineInterface(self._cfg)
        self._expl   = ExplanationEngine(mode="Beginner")
        self._fmt    = OutputFormatter(mode="Beginner")
        self._bad_an = BadMoveAnalyser(self._eng, self._cfg)

        # State
        self._board         = chess.Board()
        self._flipped       = False
        self._ranked        = []
        self._last_ev       = None
        self._hi_from       = None
        self._hi_to         = None
        self._last_json     = {}
        self._fullscreen    = False

        # Game review state
        self._review_moves  = []   # list of ReviewEntry (populated after PGN analysis)
        self._review_idx    = 0    # currently shown move in review
        self._review_mode   = False

        self._window()
        self._build_menu()
        self._build_ui()
        self._apply_palette()
        self._draw_board()

     
    # WINDOW
     

    def _window(self):
        self.root.title(
            f"Explain My Move  v{APP_VERSION}  —  Ammar  —  OCR A-Level NEA"
        )
        self.root.geometry("1320x780")
        self.root.minsize(1100, 680)
        self.root.configure(bg=self.p["root"])
        self.root.bind("<F11>",       lambda _: self._toggle_fullscreen())
        self.root.bind("<Escape>",    lambda _: self._exit_fullscreen())
        self.root.bind("<Control-d>", lambda _: self._toggle_dark())
        self.root.bind("<Control-f>", lambda _: self._flip())
        self.root.bind("<Return>",    lambda _: self._analyse())
        self.root.bind("<Left>",      lambda _: self._review_prev())
        self.root.bind("<Right>",     lambda _: self._review_next())

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)
        if not self._fullscreen:
            self.root.geometry("1320x780")

    def _exit_fullscreen(self):
        if self._fullscreen:
            self._fullscreen = False
            self.root.attributes("-fullscreen", False)
            self.root.geometry("1320x780")

     
    # MENU
     

    def _build_menu(self):
        mb = tk.Menu(self.root, tearoff=0)
        fm = tk.Menu(mb, tearoff=0)
        fm.add_command(label="Copy FEN",      command=self._copy_fen)
        fm.add_command(label="Export PGN",    command=self._export_pgn)
        fm.add_command(label="Copy JSON",     command=self._copy_json)
        fm.add_separator()
        fm.add_command(label="Exit",          command=self.root.quit)
        mb.add_cascade(label="File", menu=fm)

        vm = tk.Menu(mb, tearoff=0)
        vm.add_command(label="Fullscreen  F11",  command=self._toggle_fullscreen)
        vm.add_command(label="Flip Board  Ctrl+F", command=self._flip)
        vm.add_command(label="Dark Mode   Ctrl+D", command=self._toggle_dark)
        mb.add_cascade(label="View", menu=vm)

        hm = tk.Menu(mb, tearoff=0)
        hm.add_command(label="About", command=self._show_about)
        mb.add_cascade(label="Help", menu=hm)

        self.root.config(menu=mb)

     
    # TOP-LEVEL UI
     

    def _build_ui(self):
        p = self.p

        # ── Header ────────────────────────────────────────────────────────────
        self.header = tk.Frame(self.root, bg=p["header"], height=56)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)

        hrow = tk.Frame(self.header, bg=p["header"])
        hrow.pack(fill=tk.BOTH, expand=True, padx=18, pady=0)

        # Logo / title
        self.lbl_title = tk.Label(
            hrow,
            text="♟  Explain My Move",
            font=("Georgia", 15, "bold"),
            bg=p["header"], fg=p["header_fg"]
        )
        self.lbl_title.pack(side=tk.LEFT, pady=14)

        self.lbl_ver = tk.Label(
            hrow, text=f"v{APP_VERSION}",
            font=("Segoe UI", 9),
            bg=p["header"], fg=p["header_accent"]
        )
        self.lbl_ver.pack(side=tk.LEFT, padx=(8, 0), pady=18)

        # Right side controls
        rh = tk.Frame(hrow, bg=p["header"])
        rh.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        self._hdr_buttons = []
        for label, cmd in [("⛶", self._toggle_fullscreen),
                            ("◑", self._toggle_dark)]:
            b = tk.Button(rh, text=label, font=("Segoe UI", 14),
                          bg=p["header"], fg=p["header_fg"],
                          relief=tk.FLAT, bd=0, padx=8,
                          cursor="hand2", activebackground=p["header"],
                          activeforeground=p["header_accent"],
                          command=cmd)
            b.pack(side=tk.RIGHT)
            self._hdr_buttons.append(b)

        self.lbl_hint = tk.Label(
            rh,
            text="F11 fullscreen  ·  Ctrl+F flip  ·  Ctrl+D dark  ·  ← → navigate",
            font=("Segoe UI", 8),
            bg=p["header"], fg=p["header_accent"]
        )
        self.lbl_hint.pack(side=tk.RIGHT, padx=(0, 16))

        # ── Main two-column layout ────────────────────────────────────────────
        self.main = tk.Frame(self.root, bg=p["root"])
        self.main.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        self._build_left_col()
        self._build_right_col()

     
    # LEFT COLUMN — board
     

    def _build_left_col(self):
        p   = self.p
        col = tk.Frame(self.main, bg=p["root"])
        col.pack(side=tk.LEFT, fill=tk.Y)
        self._left_col = col

        # Eval bar + board row
        brow = tk.Frame(col, bg=p["root"])
        brow.pack()

        self.eval_cv = tk.Canvas(
            brow, width=EVAL_W, height=BOARD_PX,
            bg=p["eval_b"], highlightthickness=0
        )
        self.eval_cv.pack(side=tk.LEFT, padx=(0, 6))

        self.board_cv = tk.Canvas(
            brow,
            width=GUTTER + BOARD_PX,
            height=BOARD_PX + GUTTER,
            bg=p["board_bg"],
            highlightthickness=2,
            highlightbackground="#2D3F55"
        )
        self.board_cv.pack(side=tk.LEFT)

        # Board controls
        ctrl = tk.Frame(col, bg=p["root"])
        ctrl.pack(fill=tk.X, pady=(8, 0))

        self.btn_flip = PillButton(
            ctrl, "Flip", self._flip, p,
            style="teal", font=("Segoe UI", 9, "bold"), icon="⇅", height=28
        )
        self.btn_flip.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_copy_fen = PillButton(
            ctrl, "Copy FEN", self._copy_fen, p,
            style="ghost", font=("Segoe UI", 9), height=28
        )
        self.btn_copy_fen.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_pgn_exp = PillButton(
            ctrl, "Export PGN", self._export_pgn, p,
            style="ghost", font=("Segoe UI", 9), height=28
        )
        self.btn_pgn_exp.pack(side=tk.LEFT)

        self.lbl_persp = tk.Label(
            col, text="White at bottom",
            font=("Segoe UI", 8, "italic"),
            bg=p["root"], fg=p["fg_muted"]
        )
        self.lbl_persp.pack(anchor="w", pady=(3, 0))

        # ── Review navigator (hidden until game review is active) ─────────────
        self.review_nav = tk.Frame(col, bg=p["root"])
        # Packed/unpacked dynamically

        nav_inner = tk.Frame(self.review_nav, bg=p["root"])
        nav_inner.pack()

        self.btn_rev_prev = PillButton(
            nav_inner, "Prev", self._review_prev, p,
            style="ghost", font=("Segoe UI", 9, "bold"), icon="◀", height=30
        )
        self.btn_rev_prev.pack(side=tk.LEFT, padx=(0, 6))

        self.lbl_rev_pos = tk.Label(
            nav_inner, text="Move 0 / 0",
            font=("Segoe UI", 10, "bold"),
            bg=p["root"], fg=p["fg"]
        )
        self.lbl_rev_pos.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_rev_next = PillButton(
            nav_inner, "Next", self._review_next, p,
            style="ghost", font=("Segoe UI", 9, "bold"), icon="▶", height=30
        )
        self.btn_rev_next.pack(side=tk.LEFT)

     
    # RIGHT COLUMN — controls + output
     

    def _build_right_col(self):
        p   = self.p
        col = tk.Frame(self.main, bg=p["root"])
        col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14, 0))
        self._right_col = col

        # ── Input card ────────────────────────────────────────────────────────
        self._build_input_card(col)

        # ── Analyse / Review controls ─────────────────────────────────────────
        self._build_action_row(col)

        # ── Mode + depth strip ────────────────────────────────────────────────
        self._build_mode_strip(col)

        # ── Separator ─────────────────────────────────────────────────────────
        tk.Frame(col, bg=p["sep"], height=1).pack(fill=tk.X, pady=(4, 8))

        # ── EXPLANATION CARD (clean, non-console) ────────────────────────────
        self._build_explanation_card(col)

        # ── Move buttons (ranked) ─────────────────────────────────────────────
        self._build_move_buttons(col)

        # ── Game review list (hidden until PGN review active) ────────────────
        self._build_review_list(col)

        # ── JSON tab (collapsible) ────────────────────────────────────────────
        self._build_json_section(col)

    # ── Input card ────────────────────────────────────────────────────────────

    def _build_input_card(self, parent):
        p = self.p
        f = tk.Frame(parent, bg=p["card"],
                     highlightbackground=p["card_border"],
                     highlightthickness=1)
        f.pack(fill=tk.X, pady=(0, 6))
        self._input_card = f

        inner = tk.Frame(f, bg=p["card"], padx=10, pady=8)
        inner.pack(fill=tk.X)

        # Top row: label + format toggle
        top = tk.Frame(inner, bg=p["card"])
        top.pack(fill=tk.X, pady=(0, 4))

        tk.Label(top, text="POSITION INPUT",
                 font=("Segoe UI", 8, "bold"),
                 bg=p["card"], fg=p["fg_muted"]).pack(side=tk.LEFT)

        fmt_row = tk.Frame(top, bg=p["card"])
        fmt_row.pack(side=tk.RIGHT)

        tk.Label(fmt_row, text="Format:",
                 font=("Segoe UI", 9),
                 bg=p["card"], fg=p["fg_muted"]).pack(side=tk.LEFT, padx=(0, 6))

        self.fmt_var = tk.StringVar(value="FEN")
        for m in ("FEN", "PGN"):
            tk.Radiobutton(
                fmt_row, text=m, variable=self.fmt_var, value=m,
                font=("Segoe UI", 10, "bold"),
                bg=p["card"], fg=p["primary"],
                selectcolor=p["card"], activebackground=p["card"],
                command=self._on_fmt_change
            ).pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_input_hint = tk.Label(
            inner,
            text="Enter a FEN string or leave blank for starting position",
            font=("Segoe UI", 8, "italic"),
            bg=p["card"], fg=p["fg_muted"]
        )
        self.lbl_input_hint.pack(anchor="w", pady=(0, 4))

        ef = tk.Frame(inner, bg=p["in_border"], bd=1, relief=tk.SOLID)
        ef.pack(fill=tk.X)
        self.input_box = tk.Text(
            ef, height=3, width=52,
            font=("Consolas", 10),
            bg=p["in_bg"], fg=p["fg"],
            insertbackground=p["fg"],
            relief=tk.FLAT, padx=6, pady=5, wrap=tk.WORD
        )
        self.input_box.pack(fill=tk.X)

    def _on_fmt_change(self):
        fmt = self.fmt_var.get()
        hints = {
            "FEN": "Enter a FEN string or leave blank for starting position",
            "PGN": "Paste full PGN to review every move in the game",
        }
        self.lbl_input_hint.config(text=hints[fmt])

    # ── Action row ────────────────────────────────────────────────────────────

    def _build_action_row(self, parent):
        p   = self.p
        row = tk.Frame(parent, bg=p["root"])
        row.pack(fill=tk.X, pady=(0, 6))

        self.btn_analyse = PillButton(
            row, "Analyse Position", self._analyse, p,
            style="primary", font=("Segoe UI", 11, "bold"),
            icon="▶", height=36, width=200
        )
        self.btn_analyse.pack(side=tk.LEFT, padx=(0, 10))

        # Status indicator
        sf = tk.Frame(row, bg=p["root"])
        sf.pack(side=tk.LEFT)

        self.lbl_status = tk.Label(
            sf, text="● READY",
            font=("Segoe UI", 10, "bold"),
            bg=p["root"], fg=p["ready"]
        )
        self.lbl_status.pack(anchor="w")

        self.lbl_time = tk.Label(
            sf, text="",
            font=("Segoe UI", 8),
            bg=p["root"], fg=p["fg_muted"]
        )
        self.lbl_time.pack(anchor="w")

    # ── Mode + depth strip ────────────────────────────────────────────────────

    def _build_mode_strip(self, parent):
        p   = self.p
        row = tk.Frame(parent, bg=p["root"])
        row.pack(fill=tk.X, pady=(0, 2))
        self._mode_strip = row

        # Mode
        tk.Label(row, text="Mode:",
                 font=("Segoe UI", 9),
                 bg=p["root"], fg=p["fg_muted"]).pack(side=tk.LEFT, padx=(0, 4))

        self.mode_var = tk.StringVar(value="Beginner")
        for m in ("Beginner", "Intermediate"):
            tk.Radiobutton(
                row, text=m, variable=self.mode_var, value=m,
                font=("Segoe UI", 10), bg=p["root"], fg=p["fg"],
                selectcolor=p["root"], activebackground=p["root"],
                command=self._on_mode
            ).pack(side=tk.LEFT, padx=(0, 10))

        # Depth
        tk.Label(row, text="Depth:",
                 font=("Segoe UI", 9),
                 bg=p["root"], fg=p["fg_muted"]).pack(side=tk.LEFT, padx=(16, 4))

        self.lbl_depth_n = tk.Label(
            row, text="12",
            font=("Segoe UI", 10, "bold"),
            bg=p["root"], fg=p["primary"]
        )
        self.lbl_depth_n.pack(side=tk.LEFT, padx=(0, 4))

        self.depth_sl = tk.Scale(
            row,
            from_=ConfigManager.DEPTH_MIN, to=ConfigManager.DEPTH_MAX,
            orient=tk.HORIZONTAL, length=140, showvalue=False,
            command=self._on_depth,
            bg=p["root"], fg=p["fg"],
            troughcolor=p["sep"], highlightthickness=0, bd=0
        )
        self.depth_sl.set(12)
        self.depth_sl.pack(side=tk.LEFT)

        self.lbl_wlimit = tk.Label(
            row, text="≤30 words",
            font=("Segoe UI", 8, "italic"),
            bg=p["root"], fg=p["fg_muted"]
        )
        self.lbl_wlimit.pack(side=tk.LEFT, padx=(10, 0))

    # ── Explanation card ──────────────────────────────────────────────────────

    def _build_explanation_card(self, parent):
        """
        The main explanation output — clean card design.
        Shows:  [Badge]  Move in SAN  |  Score  |  Explanation text
        """
        p = self.p
        outer = tk.Frame(parent, bg=p["card"],
                         highlightbackground=p["card_border"],
                         highlightthickness=1)
        outer.pack(fill=tk.X, pady=(0, 6))
        self._expl_card = outer

        # Header strip
        hdr = tk.Frame(outer, bg=p["card2"], padx=10, pady=6)
        hdr.pack(fill=tk.X)

        self.lbl_expl_title = tk.Label(
            hdr, text="BEST MOVE",
            font=("Segoe UI", 8, "bold"),
            bg=p["card2"], fg=p["fg_muted"]
        )
        self.lbl_expl_title.pack(side=tk.LEFT)

        # Right side of header: eval score
        self.lbl_eval_score = tk.Label(
            hdr, text="—",
            font=("Segoe UI", 10, "bold"),
            bg=p["card2"], fg=p["primary"]
        )
        self.lbl_eval_score.pack(side=tk.RIGHT)

        # Main body
        body = tk.Frame(outer, bg=p["card"], padx=12, pady=10)
        body.pack(fill=tk.X)
        self._expl_body = body

        # Classification badge + move name row
        badge_row = tk.Frame(body, bg=p["card"])
        badge_row.pack(fill=tk.X, pady=(0, 6))

        self.lbl_class_badge = tk.Label(
            badge_row, text="",
            font=("Segoe UI", 13, "bold"),
            bg=p["card"], fg=p["fg_muted"],
            padx=8, pady=3
        )
        self.lbl_class_badge.pack(side=tk.LEFT)

        self.lbl_move_name = tk.Label(
            badge_row, text="—",
            font=("Georgia", 16, "bold"),
            bg=p["card"], fg=p["fg_head"]
        )
        self.lbl_move_name.pack(side=tk.LEFT, padx=(8, 0))

        # Mini horizontal eval bar
        self.mini_eval_cv = tk.Canvas(
            body, height=8, bg=p["card"], highlightthickness=0
        )
        self.mini_eval_cv.pack(fill=tk.X, pady=(0, 8))

        # Explanation text — NO scrollbar, clean wrapping label
        self.lbl_expl_text = tk.Label(
            body,
            text="Enter a position and press Analyse.",
            font=("Segoe UI", 11),
            bg=p["card"], fg=p["fg"],
            wraplength=420, justify=tk.LEFT, anchor="w"
        )
        self.lbl_expl_text.pack(fill=tk.X, anchor="w")

        # Divider
        tk.Frame(outer, bg=p["card_border"], height=1).pack(fill=tk.X)

        # Footer: "Also consider:" row for alternative moves
        footer = tk.Frame(outer, bg=p["card2"], padx=10, pady=6)
        footer.pack(fill=tk.X)

        tk.Label(footer, text="Also consider:",
                 font=("Segoe UI", 8),
                 bg=p["card2"], fg=p["fg_muted"]).pack(side=tk.LEFT, padx=(0, 8))

        self._alt_labels = []
        for i in range(2):
            lbl = tk.Label(
                footer, text="",
                font=("Consolas", 9, "bold"),
                bg=p["tag_bg"], fg=p["tag_fg"],
                padx=6, pady=2, relief=tk.FLAT
            )
            lbl.pack(side=tk.LEFT, padx=(0, 5))
            self._alt_labels.append(lbl)

    def _update_expl_card(self, title: str, move_san: str, score_cp,
                          explanation: str, classification: str = "Best",
                          alt_moves: list = None):
        """
        Populates the explanation card with new data.

        Parameters:
            title          — header label e.g. "BEST MOVE" / "YOUR MOVE"
            move_san       — SAN of the move
            score_cp       — centipawn score (int or None)
            explanation    — explanation string
            classification — "Best" / "Good" / "Inaccuracy" / "Mistake" / "Blunder"
            alt_moves      — list of SAN strings for alternatives (max 2)
        """
        p    = self.p
        meta = CLASSIFICATIONS.get(classification, CLASSIFICATIONS["Good"])
        col  = meta["color_d"] if self._dark else meta["color_l"]
        icon = meta["icon"]

        self.lbl_expl_title.config(text=title)
        self.lbl_class_badge.config(text=icon, fg=col)
        self.lbl_move_name.config(text=move_san if move_san else "—")

        # Score
        if score_cp is not None:
            from engine_interface import format_score as _fs
            mode = self.mode_var.get()
            self.lbl_eval_score.config(text=_fs(score_cp, mode), fg=col)
        else:
            self.lbl_eval_score.config(text="—", fg=p["fg_muted"])

        # Explanation text
        self.lbl_expl_text.config(text=explanation if explanation else "—",
                                  fg=p["fg"])

        # Mini eval bar
        self._draw_mini_eval(score_cp)

        # Alt moves
        for i, lbl in enumerate(self._alt_labels):
            if alt_moves and i < len(alt_moves):
                lbl.config(text=alt_moves[i],
                           bg=p["tag_bg"], fg=p["tag_fg"])
                lbl.pack(side=tk.LEFT, padx=(0, 5))
            else:
                lbl.config(text="")
                lbl.pack_forget()

    def _draw_mini_eval(self, cp=None):
        """Thin horizontal evaluation bar below the move label."""
        cv = self.mini_eval_cv
        cv.delete("all")
        W = cv.winfo_width() or 420
        H = 8
        p = self.p

        if cp is None:
            cv.create_rectangle(0, 0, W, H, fill=p["sep"], outline="")
            return

        if abs(cp) >= 9000:
            frac = 1.0 if cp > 0 else 0.0
        else:
            frac = (max(-600, min(600, cp)) + 600) / 1200.0

        white_w = int(W * frac)
        # Black portion (left) — from Black's side the bar reads left=black
        cv.create_rectangle(0, 0, W - white_w, H, fill=p["eval_b"], outline="")
        # White portion (right)
        if white_w > 0:
            cv.create_rectangle(W - white_w, 0, W, H, fill=p["eval_w"], outline="")
        # Midpoint tick
        cv.create_line(W // 2, 0, W // 2, H, fill=p["eval_mid"], width=1)

    # ── Ranked move buttons ───────────────────────────────────────────────────

    def _build_move_buttons(self, parent):
        p = self.p
        f = tk.Frame(parent, bg=p["card"],
                     highlightbackground=p["card_border"],
                     highlightthickness=1)
        f.pack(fill=tk.X, pady=(0, 6))
        self._moves_card = f

        inner = tk.Frame(f, bg=p["card"], padx=10, pady=6)
        inner.pack(fill=tk.X)

        tk.Label(inner, text="RANKED MOVES  (click any to view)",
                 font=("Segoe UI", 8, "bold"),
                 bg=p["card"], fg=p["fg_muted"]).pack(anchor="w", pady=(0, 4))

        self.move_btns = []
        rk = ["r1", "r2", "r3"]
        for i in range(self._cfg.get_setting("multipv_count")):
            b = tk.Button(
                inner, text="—", state=tk.DISABLED,
                width=48, anchor="w",
                font=("Consolas", 10),
                fg=p[rk[i]], bg=p["card2"],
                relief=tk.FLAT, bd=0, cursor="hand2",
                pady=4, padx=6,
                command=lambda i=i: self._show(i)
            )
            b.pack(fill=tk.X, pady=1)
            self.move_btns.append(b)

    # ── Game review list ──────────────────────────────────────────────────────

    def _build_review_list(self, parent):
        """
        Scrollable list of all moves in a game review.
        Each entry shows: move number, SAN, classification badge.
        Hidden by default; shown after PGN review completes.
        """
        p   = self.p
        f   = tk.Frame(parent, bg=p["card"],
                       highlightbackground=p["card_border"],
                       highlightthickness=1)
        self._review_list_frame = f
        # Not packed yet — only shown during review mode

        inner = tk.Frame(f, bg=p["card"], padx=10, pady=6)
        inner.pack(fill=tk.X)

        hrow = tk.Frame(inner, bg=p["card"])
        hrow.pack(fill=tk.X, pady=(0, 4))

        tk.Label(hrow, text="GAME REVIEW",
                 font=("Segoe UI", 8, "bold"),
                 bg=p["card"], fg=p["fg_muted"]).pack(side=tk.LEFT)

        self.btn_close_review = PillButton(
            hrow, "Close Review", self._close_review, p,
            style="ghost", font=("Segoe UI", 8), height=22
        )
        self.btn_close_review.pack(side=tk.RIGHT)

        # Scrollable canvas for move list
        list_container = tk.Frame(inner, bg=p["card"])
        list_container.pack(fill=tk.X)

        self.review_canvas = tk.Canvas(
            list_container, height=120,
            bg=p["card"], highlightthickness=0
        )
        rev_scroll = ttk.Scrollbar(
            list_container, orient="horizontal",
            command=self.review_canvas.xview
        )
        self.review_canvas.configure(xscrollcommand=rev_scroll.set)
        rev_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.review_canvas.pack(fill=tk.X)

        self.review_inner = tk.Frame(self.review_canvas, bg=p["card"])
        self._review_window = self.review_canvas.create_window(
            (0, 0), window=self.review_inner, anchor="nw"
        )
        self.review_inner.bind(
            "<Configure>",
            lambda e: self.review_canvas.configure(
                scrollregion=self.review_canvas.bbox("all")
            )
        )

    # ── JSON section ──────────────────────────────────────────────────────────

    def _build_json_section(self, parent):
        p = self.p
        self._json_visible = False          # hidden by default

        f = tk.Frame(parent, bg=p["card"],
                     highlightbackground=p["card_border"],
                     highlightthickness=1)
        f.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        self._json_frame = f

        # ── Header row with toggle + copy ─────────────────────────────────────
        hrow = tk.Frame(f, bg=p["card2"], padx=10, pady=5)
        hrow.pack(fill=tk.X)
        self._json_hrow = hrow

        self.lbl_json_title = tk.Label(
            hrow, text="▶  JSON OUTPUT",
            font=("Segoe UI", 8, "bold"),
            bg=p["card2"], fg=p["fg_muted"],
            cursor="hand2"
        )
        self.lbl_json_title.pack(side=tk.LEFT)
        self.lbl_json_title.bind("<Button-1>", lambda e: self._toggle_json())

        self.btn_toggle_json = PillButton(
            hrow, "Show", self._toggle_json, p,
            style="ghost", font=("Segoe UI", 8), height=22
        )
        self.btn_toggle_json.pack(side=tk.RIGHT, padx=(4, 0))

        self.btn_copy_json = PillButton(
            hrow, "Copy", self._copy_json, p,
            style="ghost", font=("Segoe UI", 8), height=22
        )
        self.btn_copy_json.pack(side=tk.RIGHT)

        # ── Collapsible body ──────────────────────────────────────────────────
        self._json_body = tk.Frame(f, bg=p["card"])
        # Not packed yet — shown only when _json_visible is True

        self.json_txt = tk.Text(
            self._json_body, height=6, width=52, wrap=tk.NONE,
            font=("Consolas", 8),
            bg=p["out_bg"], fg=p["out_fg"],
            relief=tk.FLAT, padx=8, pady=4
        )
        s = ttk.Scrollbar(self._json_body, orient="vertical",
                          command=self.json_txt.yview)
        self.json_txt.configure(yscrollcommand=s.set)
        s.pack(side=tk.RIGHT, fill=tk.Y)
        self.json_txt.pack(fill=tk.BOTH, expand=True)

    def _toggle_json(self):
        """Show or hide the JSON output body."""
        self._json_visible = not self._json_visible
        p = self.p
        if self._json_visible:
            self._json_body.pack(fill=tk.BOTH, expand=True)
            self.lbl_json_title.config(text="▼  JSON OUTPUT")
            self.btn_toggle_json.config(text="Hide")
        else:
            self._json_body.pack_forget()
            self.lbl_json_title.config(text="▶  JSON OUTPUT")
            self.btn_toggle_json.config(text="Show")

     
    # BOARD RENDERING
     

    def _draw_board(self, hi_from=None, hi_to=None, bad_sq=None, best_sq=None):
        cv = self.board_cv
        cv.delete("all")
        p  = self.p
        fl = self._flipped

        for vrow in range(8):
            for vcol in range(8):
                x1 = GUTTER + vcol * SQ
                y1 = vrow * SQ
                x2, y2 = x1 + SQ, y1 + SQ

                file_idx = (7 - vcol) if fl else vcol
                rank_idx = vrow       if fl else (7 - vrow)
                sq       = chess.square(file_idx, rank_idx)

                if sq == bad_sq:
                    fill = p["sq_bad"]
                elif sq == best_sq:
                    fill = p["sq_best"]
                elif sq == hi_from:
                    fill = p["sq_from"]
                elif sq == hi_to:
                    fill = p["sq_to"]
                else:
                    fill = p["sq_light"] if (vrow + vcol) % 2 == 0 else p["sq_dark"]

                cv.create_rectangle(x1, y1, x2, y2, fill=fill, outline="")

                piece = self._board.piece_at(sq)
                if piece:
                    sym = PIECES[piece.piece_type][
                        0 if piece.color == chess.WHITE else 1
                    ]
                    cv.create_text(
                        x1 + SQ // 2, y1 + SQ // 2,
                        text=sym, font=("Arial", 30)
                    )

        for vcol in range(8):
            fidx = (7 - vcol) if fl else vcol
            cv.create_text(
                GUTTER + vcol * SQ + SQ // 2, BOARD_PX + 11,
                text=chess.FILE_NAMES[fidx],
                font=("Segoe UI", 11), fill=p["coord"]
            )
        for vrow in range(8):
            ridx = vrow if fl else (7 - vrow)
            cv.create_text(
                GUTTER // 2, vrow * SQ + SQ // 2,
                text=str(ridx + 1),
                font=("Segoe UI", 11), fill=p["coord"]
            )

        if hasattr(self, "lbl_persp"):
            self.lbl_persp.config(
                text="Black at bottom" if fl else "White at bottom"
            )

    def _draw_eval_bar(self, cp=None):
        cv = self.eval_cv
        cv.delete("all")
        p  = self.p
        H  = BOARD_PX

        if cp is None:
            cv.create_rectangle(0, 0, EVAL_W, H, fill=p["eval_mid"], outline="")
            return

        if abs(cp) >= 9000:
            white_frac = 1.0 if cp > 0 else 0.0
        else:
            clamped    = max(-600, min(600, cp))
            white_frac = (clamped + 600) / 1200.0

        white_h = int(H * white_frac)
        black_h = H - white_h

        if black_h > 0:
            cv.create_rectangle(0, 0, EVAL_W, black_h, fill=p["eval_b"], outline="")
        if white_h > 0:
            cv.create_rectangle(0, black_h, EVAL_W, H, fill=p["eval_w"], outline="")
        cv.create_line(0, black_h, EVAL_W, black_h, fill=p["eval_mid"], width=2)

     
    # PARSING
     

    def _parse_fen(self, text: str):
        try:
            board = chess.Board(text) if text.strip() else chess.Board()
        except ValueError:
            return None, "Invalid FEN format."
        if not board.is_valid():
            return None, "This FEN describes an illegal position."
        return board, None

    def _parse_pgn(self, text: str):
        try:
            game = chess.pgn.read_game(io.StringIO(text.strip()))
            if game is None:
                return None, None, "Could not parse PGN."
            board = game.end().board()
            return game, board, None
        except Exception as e:
            return None, None, f"PGN parsing failed: {e}"

     
    # STATUS
     

    def _st_ready(self):
        self.lbl_status.config(text="● READY",      fg=self.p["ready"])
        self.lbl_time.config(text="")

    def _st_thinking(self, label="ANALYSING…"):
        self.lbl_status.config(text=f"● {label}", fg=self.p["thinking"])
        self.lbl_time.config(text="")

    def _st_done(self, ms: int, fallback: bool):
        if fallback:
            self.lbl_status.config(text="● FALLBACK", fg=self.p["fallback"])
        else:
            self.lbl_status.config(text="● READY",    fg=self.p["ready"])
        warn = "  ⚠ exceeds 2s target" if ms > 2000 else ""
        self.lbl_time.config(text=f"{ms} ms{warn}")

     
    # CALLBACKS
     

    def _on_mode(self):
        mode = self.mode_var.get()
        self._expl.set_mode(mode)
        self._fmt.set_mode(mode)
        self._cfg.update_setting("mode", mode)
        lim = 30 if mode == "Beginner" else 40
        self.lbl_wlimit.config(text=f"≤{lim} words")
        if self._ranked:
            self._show(0)
        elif self._review_mode and self._review_moves:
            self._render_review_entry(self._review_idx)

    def _on_depth(self, val):
        nd = int(float(val))
        try:
            self._cfg.update_setting("engine_depth", nd)
            self._eng.update_from_config(self._cfg)
            self.lbl_depth_n.config(text=str(nd))
        except ValueError as e:
            messagebox.showerror("Invalid Depth", str(e))

    def _flip(self):
        self._flipped = not self._flipped
        if self._review_mode and self._review_moves:
            entry = self._review_moves[self._review_idx]
            self._draw_board(hi_from=entry["move"].from_square,
                             hi_to=entry["move"].to_square,
                             bad_sq=entry["move"].to_square if entry.get("is_bad") else None)
        else:
            self._draw_board(
                hi_from=getattr(self, "_hi_from", None),
                hi_to=getattr(self, "_hi_to", None)
            )

     
    # MAIN ANALYSIS PIPELINE — FEN mode
     

    def _analyse(self):
        raw = self.input_box.get("1.0", tk.END).strip()
        fmt = self.fmt_var.get()

        if fmt == "PGN":
            self._analyse_pgn(raw)
            return

        # FEN mode
        board, err = self._parse_fen(raw)
        if err:
            messagebox.showerror("Input Error", err)
            return

        self._board   = board
        self._hi_from = None
        self._hi_to   = None
        self._close_review()
        self._draw_board()
        self._draw_eval_bar()
        self._clear_expl_card()

        self.btn_analyse.config(state=tk.DISABLED)
        self._st_thinking()

        for b in self.move_btns:
            b.config(state=tk.DISABLED, text="—")

        self._eng.update_from_config(self._cfg)
        container = {}
        done      = threading.Event()

        def worker():
            ev = MoveEvaluator(board, self._eng, self._cfg)
            ev.run_full_evaluation()
            container["ev"] = ev
            done.set()

        def poll():
            if not done.is_set():
                self.root.after(80, poll)
                return

            self.btn_analyse.config(state=tk.NORMAL)
            ev = container.get("ev")

            if ev is None or not ev.ranked_moves:
                self._st_ready()
                if any((board.is_checkmate(), board.is_stalemate(),
                        board.is_insufficient_material())):
                    msg = self._fmt._terminal_message(board)
                    self._update_expl_card(
                        "POSITION", "—", None, msg, "Good"
                    )
                else:
                    messagebox.showerror(
                        "Engine Error",
                        "No results returned.\n"
                        "Verify Stockfish is at the configured path."
                    )
                return

            self._ranked  = ev.ranked_moves
            self._last_ev = ev
            self._st_done(ev.analysis_time_ms, ev.timeout_flag)
            _, best_cp = ev.ranked_moves[0]
            self._draw_eval_bar(best_cp)
            self._show(0)

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(80, poll)

    def _show(self, idx: int):
        """Show ranked move idx in the explanation card (FEN mode)."""
        if idx >= len(self._ranked) or self._board is None:
            return

        move, score = self._ranked[idx]
        board       = self._board
        ev          = self._last_ev

        self._hi_from = move.from_square
        self._hi_to   = move.to_square
        self._draw_board(hi_from=move.from_square, hi_to=move.to_square)
        self._draw_eval_bar(score)

        explanation = self._expl.generate_explanation(board, move)

        # Alt moves (the other ranked candidates)
        alts = [
            self._fmt._san(board, m)
            for m, _ in self._ranked
            if m != move
        ][:2]

        title = ["BEST MOVE", "2ND BEST", "3RD BEST"][idx] if idx < 3 else f"MOVE #{idx+1}"
        classification = "Best" if idx == 0 else "Good"

        self._update_expl_card(
            title=title,
            move_san=self._fmt._san(board, move),
            score_cp=score,
            explanation=explanation,
            classification=classification,
            alt_moves=alts,
        )

        # Ranked move buttons
        rk_keys = ["r1", "r2", "r3"]
        labels  = ["1st (Best)", "2nd", "3rd"]
        for i, btn in enumerate(self.move_btns):
            if i < len(self._ranked):
                m, s    = self._ranked[i]
                san     = self._fmt._san(board, m)
                score_s = self._fmt._fmt_score(s)
                lbl     = labels[i] if i < len(labels) else f"#{i+1}"
                col     = self.p[rk_keys[i]] if i < len(rk_keys) else self.p["fg"]
                btn.config(
                    state=tk.NORMAL,
                    text=f"  {lbl}:  {san}    {score_s}",
                    fg=col
                )
            else:
                btn.config(state=tk.DISABLED, text="—")

        # JSON
        triggered = self._expl.apply_rules(board, move)
        selected  = self._expl.select_top_rules(triggered)
        jout = self._fmt.generate_json_output(
            board, self._ranked, explanation, ev
        )
        self._last_json = jout
        self._write_json(self._fmt.to_json_string(jout))

     
    # GAME REVIEW — PGN mode
     

    # A ReviewEntry is a dict with keys:
    #   board_before   : chess.Board  — position before the move
    #   move           : chess.Move
    #   move_san       : str
    #   move_num       : int
    #   color          : chess.WHITE | chess.BLACK
    #   best_move      : chess.Move | None
    #   best_move_san  : str
    #   best_score     : int | None
    #   user_score     : int | None  — score after user's move
    #   cp_loss        : int
    #   classification : str
    #   is_bad         : bool
    #   explanation_best : str
    #   explanation_user : str

    def _analyse_pgn(self, raw: str):
        """
        Triggered when format=PGN and Analyse is clicked.
        Parses the PGN, then analyses every move in a background thread.
        Shows a progress indicator during analysis.
        """
        if not raw:
            messagebox.showerror("Input Error", "Please paste a PGN to review.")
            return

        game, _, err = self._parse_pgn(raw)
        if err:
            messagebox.showerror("PGN Error", err)
            return

        # Collect all moves
        moves_list = []
        node = game
        while node.variations:
            next_node = node.variations[0]
            moves_list.append((node.board(), next_node.move))
            node = next_node

        if not moves_list:
            messagebox.showerror("PGN Error", "No moves found in PGN.")
            return

        total = len(moves_list)
        self.btn_analyse.config(state=tk.DISABLED)
        self._st_thinking(f"REVIEWING 0 / {total}")
        self._close_review()
        self._review_mode   = False
        self._review_moves  = []
        self._ranked        = []

        # Reset board to start
        self._board = chess.Board()
        self._draw_board()
        self._draw_eval_bar()
        self._clear_expl_card()

        self._eng.update_from_config(self._cfg)
        self._bad_an.threshold = self._cfg.get_setting("bad_move_threshold")
        mode      = self.mode_var.get()
        container = {"entries": [], "done": False, "progress": 0}
        done_ev   = threading.Event()

        def worker():
            entries = []
            for i, (board_before, move) in enumerate(moves_list):
                # Classify via BadMoveAnalyser (it does before+after eval)
                result = self._bad_an.analyse(board_before, move, mode=mode)

                # Also get best-move explanation
                explanation_best = self._expl.generate_explanation(
                    board_before, result.best_move
                ) if result.best_move else "No better move found."

                explanation_user = self._expl.generate_explanation(
                    board_before, move
                )

                entry = {
                    "board_before":     board_before.copy(),
                    "move":             move,
                    "move_san":         result.user_move_san,
                    "move_num":         board_before.fullmove_number,
                    "color":            board_before.turn,
                    "best_move":        result.best_move,
                    "best_move_san":    result.best_move_san,
                    "best_score":       result.score_before,
                    "user_score":       result.score_after,
                    "cp_loss":          result.cp_loss,
                    "classification":   result.classification,
                    "is_bad":           result.is_bad,
                    "reasons":          result.reasons,
                    "better_lines":     result.better_lines,
                    "explanation_best": explanation_best,
                    "explanation_user": explanation_user,
                }
                entries.append(entry)
                container["entries"] = entries
                container["progress"] = i + 1

                # Update progress label on main thread
                self.root.after(
                    0,
                    lambda i=i: self.lbl_status.config(
                        text=f"● REVIEWING {i+1} / {total}",
                        fg=self.p["thinking"]
                    )
                )

            container["done"] = True
            done_ev.set()

        def poll():
            if not done_ev.is_set():
                self.root.after(150, poll)
                return

            self.btn_analyse.config(state=tk.NORMAL)
            entries = container["entries"]

            if not entries:
                self._st_ready()
                messagebox.showerror("Review Error", "No moves could be analysed.")
                return

            self._review_moves = entries
            self._review_mode  = True
            self._review_idx   = 0

            # Show final board position
            self._board = entries[-1]["board_before"].copy()
            self._board.push(entries[-1]["move"])

            self._st_ready()
            self._show_review_ui()
            self._render_review_entry(0)

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(150, poll)

    def _show_review_ui(self):
        """Shows the review navigator + move list, hides regular move buttons."""
        self._moves_card.pack_forget()
        self._json_frame.pack_forget()

        self._review_list_frame.pack(fill=tk.X, pady=(0, 6))
        self.review_nav.pack(fill=tk.X, pady=(6, 0))

        self._populate_review_list()

    def _populate_review_list(self):
        """Fills the horizontal scrollable move list with classification badges."""
        for w in self.review_inner.winfo_children():
            w.destroy()

        p = self.p
        for i, entry in enumerate(self._review_moves):
            meta  = CLASSIFICATIONS.get(entry["classification"], CLASSIFICATIONS["Good"])
            col   = meta["color_d"] if self._dark else meta["color_l"]
            icon  = meta["icon"]
            color_label = entry["color"]
            prefix = ("W" if color_label == chess.WHITE else "B")
            num   = entry["move_num"]
            san   = entry["move_san"]

            btn = tk.Button(
                self.review_inner,
                text=f"{num}{'.' if color_label == chess.WHITE else '…'}{san}\n{icon}",
                font=("Segoe UI", 8, "bold"),
                fg=col,
                bg=p["card2"],
                relief=tk.FLAT, bd=0,
                padx=6, pady=4,
                cursor="hand2",
                command=lambda idx=i: self._review_jump(idx)
            )
            btn.pack(side=tk.LEFT, padx=1, pady=2)

        self.lbl_rev_pos.config(
            text=f"Move 1 / {len(self._review_moves)}"
        )

    def _review_jump(self, idx: int):
        self._review_idx = idx
        self._render_review_entry(idx)

    def _review_prev(self):
        if self._review_mode and self._review_idx > 0:
            self._review_idx -= 1
            self._render_review_entry(self._review_idx)

    def _review_next(self):
        if self._review_mode and self._review_idx < len(self._review_moves) - 1:
            self._review_idx += 1
            self._render_review_entry(self._review_idx)

    def _render_review_entry(self, idx: int):
        """
        Renders a single review entry — updates board, eval bar,
        and explanation card for the move at index idx.

        Shows TWO sections depending on whether the move was bad:
            Always:  Best move card with engine's best move + explanation
            If bad:  Your move card showing classification + reasons
        """
        if not self._review_moves or idx >= len(self._review_moves):
            return

        entry  = self._review_moves[idx]
        board  = entry["board_before"]
        move   = entry["move"]
        p      = self.p

        # Update board to position before the move
        self._board = board.copy()
        hi_from = move.from_square
        hi_to   = move.to_square
        bad_sq  = hi_to if entry["is_bad"] else None

        self._draw_board(hi_from=hi_from, hi_to=hi_to, bad_sq=bad_sq)
        self._draw_eval_bar(entry["best_score"])

        # Update review position label
        self.lbl_rev_pos.config(
            text=f"Move {idx+1} / {len(self._review_moves)}"
        )

        # ── Build explanation card content ────────────────────────────────────
        classification = entry["classification"]
        meta           = CLASSIFICATIONS.get(classification, CLASSIFICATIONS["Good"])
        col            = meta["color_d"] if self._dark else meta["color_l"]

        if entry["is_bad"]:
            # Show: your move was classified as X, here's why + engine's best
            title = f"YOUR MOVE  ·  {classification.upper()}"

            # Compose explanation text
            parts = []
            parts.append(f"You played: {entry['move_san']}")
            if entry["best_move_san"] and entry["best_move_san"] != entry["move_san"]:
                parts.append(f"Engine best: {entry['best_move_san']}")
            parts.append("")

            # Reason
            if entry["reasons"]:
                parts.append(entry["reasons"][0])

            # Engine explanation
            if entry["explanation_best"] and entry["explanation_best"] != entry["explanation_user"]:
                parts.append("")
                parts.append(f"Best move idea: {entry['explanation_best']}")

            explanation = "\n".join(parts)

            # Alternatives
            alts = entry.get("better_lines", [])[:2]

            self._update_expl_card(
                title          = title,
                move_san       = entry["move_san"],
                score_cp       = entry["user_score"],
                explanation    = explanation,
                classification = classification,
                alt_moves      = alts if alts else None,
            )

        else:
            # Good move — show engine's best and user's move (which agrees)
            title = f"YOUR MOVE  ·  {classification.upper()}"
            explanation = entry["explanation_user"]

            alts = [
                self._fmt._san(board, m)
                for m, _ in []   # no ranked_moves in review mode
            ][:2]

            self._update_expl_card(
                title          = title,
                move_san       = entry["move_san"],
                score_cp       = entry["best_score"],
                explanation    = explanation,
                classification = classification,
                alt_moves      = None,
            )

        # Update mini eval bar with a slight delay (widget needs to be mapped)
        self.root.after(20, lambda: self._draw_mini_eval(
            entry["user_score"] if entry["is_bad"] else entry["best_score"]
        ))

        # Hide ranked move buttons in review mode
        for b in self.move_btns:
            b.config(state=tk.DISABLED, text="—")

    def _close_review(self):
        """Exits game review mode and restores normal UI."""
        self._review_mode  = False
        self._review_moves = []
        self._review_idx   = 0

        try:
            self._review_list_frame.pack_forget()
            self.review_nav.pack_forget()
        except Exception:
            pass

        # Restore ranked moves card and JSON section
        try:
            self._moves_card.pack(fill=tk.X, pady=(0, 6))
            self._json_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        except Exception:
            pass

        self._clear_expl_card()
        self._draw_board()
        self._draw_eval_bar()

    def _clear_expl_card(self):
        self.lbl_expl_title.config(text="BEST MOVE")
        self.lbl_class_badge.config(text="", fg=self.p["fg_muted"])
        self.lbl_move_name.config(text="—")
        self.lbl_eval_score.config(text="—")
        self.lbl_expl_text.config(
            text="Enter a position and press Analyse.",
            fg=self.p["fg_muted"]
        )
        for lbl in self._alt_labels:
            lbl.config(text="")
            lbl.pack_forget()
        self._draw_mini_eval(None)

     
    # OUTPUT HELPERS
     

    def _write_json(self, text: str):
        self.json_txt.config(state=tk.NORMAL)
        self.json_txt.delete("1.0", tk.END)
        self.json_txt.insert(tk.END, text)

    def _copy_fen(self):
        fen = self._fmt.get_fen(self._board)
        self.root.clipboard_clear()
        self.root.clipboard_append(fen)
        messagebox.showinfo("FEN Copied", f"FEN copied to clipboard:\n\n{fen}")

    def _export_pgn(self):
        pgn = self._fmt.generate_pgn_output(self._board)
        self.root.clipboard_clear()
        self.root.clipboard_append(pgn)
        messagebox.showinfo("PGN Exported", "PGN copied to clipboard.")

    def _copy_json(self):
        if not self._last_json:
            messagebox.showinfo("No Output", "Run an analysis first.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self._fmt.to_json_string(self._last_json))
        messagebox.showinfo("Copied", "JSON output copied to clipboard.")

     
    # DARK MODE
     

    def _toggle_dark(self):
        self._dark = not self._dark
        self.p     = DARK if self._dark else LIGHT
        try:
            self._cfg.update_setting("dark_mode", self._dark)
        except Exception:
            pass
        self._apply_palette()
        # Redraw dynamic canvas elements
        self._draw_board(
            hi_from=getattr(self, "_hi_from", None),
            hi_to=getattr(self, "_hi_to", None)
        )
        self._draw_eval_bar(
            self._ranked[0][1] if self._ranked else None
        )
        self.root.after(20, lambda: self._draw_mini_eval(
            self._ranked[0][1] if self._ranked else None
        ))

    def _apply_palette(self):
        p = self.p
        self.root.configure(bg=p["root"])

        # Header
        for w in [self.header, self.lbl_title, self.lbl_ver, self.lbl_hint]:
            try:
                if isinstance(w, tk.Label):
                    if w is self.lbl_title:
                        w.configure(bg=p["header"], fg=p["header_fg"])
                    else:
                        w.configure(bg=p["header"], fg=p["header_accent"])
                else:
                    w.configure(bg=p["header"])
            except Exception:
                pass
        for b in self._hdr_buttons:
            try:
                b.configure(bg=p["header"], fg=p["header_fg"],
                            activebackground=p["header"])
            except Exception:
                pass

        # Main frame + left/right cols
        for w in [self.main, self._left_col, self._right_col]:
            try:
                w.configure(bg=p["root"])
            except Exception:
                pass

        # Board canvas
        self.board_cv.configure(bg=p["board_bg"])
        self.eval_cv.configure(bg=p["eval_b"])
        self.mini_eval_cv.configure(bg=p["card"])

        # Recursively style everything in the right column
        self._palette_widget(self._left_col, p)
        self._palette_widget(self._right_col, p)

        # Pill buttons — re-theme
        pill_map = [
            (self.btn_flip,      "teal"),
            (self.btn_copy_fen,  "ghost"),
            (self.btn_pgn_exp,   "ghost"),
            (self.btn_analyse,   "primary"),
            (self.btn_copy_json, "ghost"),
        ]
        optional_pills = [
            ("btn_close_review",  "ghost"),
            ("btn_rev_prev",      "ghost"),
            ("btn_rev_next",      "ghost"),
            ("btn_toggle_json",   "ghost"),
        ]
        for btn, style in pill_map:
            try:
                btn.update_palette(p, style)
            except Exception:
                pass
        for attr, style in optional_pills:
            try:
                getattr(self, attr).update_palette(p, style)
            except Exception:
                pass

        # Text widgets
        try:
            self.json_txt.configure(bg=p["out_bg"], fg=p["out_fg"])
        except Exception:
            pass
        try:
            self.lbl_json_title.configure(bg=p["card2"], fg=p["fg_muted"])
        except Exception:
            pass
        try:
            self._json_hrow.configure(bg=p["card2"])
        except Exception:
            pass
        try:
            self._json_body.configure(bg=p["card"])
        except Exception:
            pass
        try:
            self.input_box.configure(bg=p["in_bg"], fg=p["fg"],
                                     insertbackground=p["fg"])
        except Exception:
            pass

        # Move buttons
        rk = ["r1", "r2", "r3"]
        for i, b in enumerate(self.move_btns):
            col = p[rk[i]] if i < len(rk) else p["fg"]
            try:
                b.configure(bg=p["card2"], fg=col)
            except Exception:
                pass

        # Review inner
        try:
            self.review_canvas.configure(bg=p["card"])
            self.review_inner.configure(bg=p["card"])
        except Exception:
            pass

        # Explanation card specific labels
        for w, key in [
            (self.lbl_expl_title, "fg_muted"),
            (self.lbl_eval_score, "primary"),
            (self.lbl_move_name,  "fg_head"),
            (self.lbl_expl_text,  "fg"),
        ]:
            try:
                bg = p["card2"] if w is self.lbl_expl_title else p["card"]
                w.configure(bg=bg, fg=p[key])
            except Exception:
                pass

        for lbl in self._alt_labels:
            try:
                lbl.configure(bg=p["tag_bg"], fg=p["tag_fg"])
            except Exception:
                pass

        # Repopulate review list colours if active
        if self._review_mode and self._review_moves:
            self._populate_review_list()

    def _palette_widget(self, w, p: dict):
        """Recursive palette propagation."""
        try:
            cls = w.winfo_class()
            if cls == "Frame":
                try:
                    par_bg = w.master.cget("bg")
                    if par_bg in (LIGHT["root"], DARK["root"], p["root"]):
                        w.configure(bg=p["root"])
                    elif par_bg in (LIGHT["card2"], DARK["card2"]):
                        w.configure(bg=p["card2"])
                    else:
                        w.configure(bg=p["card"])
                except Exception:
                    w.configure(bg=p["card"])
            elif cls == "Label":
                try:
                    pbg = w.master.cget("bg")
                    w.configure(bg=pbg, fg=p["fg"])
                except Exception:
                    w.configure(fg=p["fg"])
            elif cls == "Button":
                # Check common specific buttons
                if hasattr(self, "btn_analyse") and isinstance(self.btn_analyse, tk.Button) and w is self.btn_analyse:
                    w.configure(bg=p["primary"], fg=p["primary_fg"])
                elif hasattr(self, "btn_flip") and isinstance(self.btn_flip, tk.Button) and w is self.btn_flip:
                    w.configure(bg=p["teal"], fg=p["teal_fg"])
                else:
                    w.configure(bg=p["b_ghost"], fg=p["b_ghost_fg"])
            elif cls == "Radiobutton":
                try:
                    pbg = w.master.cget("bg")
                    w.configure(bg=pbg, fg=p["fg"],
                                selectcolor=pbg, activebackground=pbg)
                except Exception:
                    pass
            elif cls == "Scale":
                try:
                    pbg = w.master.cget("bg")
                    w.configure(bg=pbg, fg=p["fg"], troughcolor=p["sep"])
                except Exception:
                    pass
        except Exception:
            pass

        for child in w.winfo_children():
            # Skip pill buttons (Canvas) — handled separately
            if isinstance(child, PillButton):
                continue
            self._palette_widget(child, p)

     
    # ABOUT
     

    def _show_about(self):
        """Opens a styled About dialog."""
        win = tk.Toplevel(self.root)
        win.title("About — Explain My Move")
        win.geometry("520x440")
        win.resizable(False, False)
        win.configure(bg=self.p["panel"])
        win.grab_set()

        p = self.p

        # Header
        hdr = tk.Frame(win, bg=p["header"], height=60)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr,
                 text="♟  Explain My Move",
                 font=("Georgia", 14, "bold"),
                 bg=p["header"], fg=p["header_fg"]).pack(side=tk.LEFT, padx=18, pady=16)
        tk.Label(hdr,
                 text=f"v{APP_VERSION}",
                 font=("Segoe UI", 9),
                 bg=p["header"], fg=p["header_accent"]).pack(side=tk.LEFT, pady=22)

        body = tk.Frame(win, bg=p["panel"], padx=24, pady=18)
        body.pack(fill=tk.BOTH, expand=True)

        sections = [
            ("Project", (
                "An intelligent chess move evaluation tool that explains why a move is good "
                "or bad in plain English. Designed to help beginner and intermediate players "
                "understand engine recommendations and learn from their mistakes."
            )),
            ("Author", "Ammar  —  OCR A-Level Computer Science NEA  (Component 03/04)"),
            ("Technology", "Python 3  ·  Tkinter  ·  python-chess  ·  Stockfish 16"),
            ("Features", (
                "• Analyse any position by FEN string\n"
                "• Full game review from PGN  (like chess.com Game Review)\n"
                "• Bad-move detection: OK / Inaccuracy / Mistake / Blunder\n"
                "• Beginner and Intermediate explanation modes\n"
                "• Dark mode  ·  Board flip  ·  Fullscreen"
            )),
            ("Keyboard Shortcuts", (
                "Enter — Analyse    F11 — Fullscreen\n"
                "Ctrl+D — Dark mode    Ctrl+F — Flip board\n"
                "← / → — Navigate game review"
            )),
        ]

        for heading, content in sections:
            tk.Label(body, text=heading,
                     font=("Segoe UI", 9, "bold"),
                     bg=p["panel"], fg=p["primary"]).pack(anchor="w", pady=(8, 1))
            tk.Label(body, text=content,
                     font=("Segoe UI", 10),
                     bg=p["panel"], fg=p["fg"],
                     wraplength=460, justify=tk.LEFT).pack(anchor="w")

        tk.Frame(body, bg=p["sep"], height=1).pack(fill=tk.X, pady=(16, 8))

        PillButton(
            body, "Close", win.destroy, p,
            style="primary", font=("Segoe UI", 10, "bold"), height=32, width=100
        ).pack()


 
# ENTRY POINT
 

if __name__ == "__main__":
    root = tk.Tk()
    app  = ExplainMyMoveApp(root)
    root.mainloop()