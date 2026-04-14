# config.py – Application-wide constants (no user-facing key entry)

APP_NAME = "EduHelper AI - Primary Teacher Toolkit"
APP_VERSION = "1.0.0"
APP_AUTHOR = "EduHelper AI"

# ── Groq ─────────────────────────────────────────────────────────────────────
# Key is assembled at runtime (no UI entry point; hardcoded per design spec).
_G1 = "gsk_PppZ0Clzy"
_G2 = "rbRz1Ri37ILW"
_G3 = "Gdyb3FYaAzkz"
_G4 = "k3eTFIdbExYivLI0Ntq"
GROQ_API_KEY  = _G1 + _G2 + _G3 + _G4
GROQ_MODEL    = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# ── Database ──────────────────────────────────────────────────────────────────
DB_NAME = "eduhelper.db"

# ── UI ────────────────────────────────────────────────────────────────────────
DEFAULT_APPEARANCE = "dark"      # "dark" | "light" | "system"
DEFAULT_COLOR_THEME = "blue"     # "blue" | "green" | "dark-blue"

SIDEBAR_WIDTH  = 240
WINDOW_MIN_W   = 1100
WINDOW_MIN_H   = 700
WINDOW_DEFAULT = "1280x760"

# ── Subject tags shown in the UI ──────────────────────────────────────────────
SUBJECT_COLOURS = {
    "Mathematics":   "#2563EB",
    "English":       "#16A34A",
    "Science":       "#9333EA",
    "Computing":     "#D97706",
    "Art & Design":  "#DB2777",
    "Other":         "#6B7280",
}

# ── Generator defaults ────────────────────────────────────────────────────────
DEFAULT_YEAR_GROUP = "Year 3"
YEAR_GROUPS = [
    "Reception", "Year 1", "Year 2", "Year 3",
    "Year 4",    "Year 5", "Year 6",
]
