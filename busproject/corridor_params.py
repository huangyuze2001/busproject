"""
Shared corridor parameters and PRISM reference values (single source of truth).

PARAMS: the model parameters used by the corridor CTMC. These MUST match the
constants declared in corridor_2stop.sm and corridor_3stop.sm. (PRISM .sm files
cannot import Python, so this module is the canonical record -- keep the .sm
files in sync with the values here.)

PRISM_REF: results obtained by independently verifying the .sm models in
PRISM 4.10.1 (GUI -> Build -> Verify) and recorded here so the Monte-Carlo
simulation can cross-check against them. These values are NOT produced by the
simulation script; they are the PRISM ground truth it is compared against.
"""

# --- model parameters (must equal the constants in the .sm files) ----------
LAM     = 1.6    # passenger arrival rate per stop (per minute)
MU_BUS  = 0.5    # bus arrival rate at stop 1 (per minute)
MU_TRAV = 0.6    # inter-stop travel rate (per minute)
THETA   = 0.03   # reneging rate per waiting passenger (per minute)
CAP     = 10     # bus capacity
K       = 20     # platform capacity per stop

# --- PRISM-verified reference results (PRISM 4.10.1, Verify) ----------------
# keyed by number of stops; each maps a property name -> verified value.
PRISM_REF = {
    2: {"queue1": 4.637, "queue2": 11.228, "P(full2)": 0.128},
    3: {"queue1": 6.643, "queue2": 16.983, "queue3": 19.424, "P(full3)": 0.631},
}
