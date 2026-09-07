"""Shared configuration for supervisor-review experiments.

These settings reproduce the additional validation/sensitivity experiments added
in response to the dissertation review. The original model files and baseline
scripts are intentionally left unchanged; revision experiments write only to
results/revision/.
"""

# Single-stop validation
N_REPLICATIONS = 30
SIM_HORIZON_MIN = 40_000.0
BASE_SEED = 0
LAMBDA = 2.0
MU_BUS = 0.22
THETA = 0.03
EFFECTIVE_CAPACITY = 10
TAGGED_MAX_AHEAD = 80
SERVICE_DEADLINE_MIN = 15.0

# MDP sensitivity
MDP_HORIZON_MIN = 20.0
MDP_DT_VALUES = (0.25, 0.125, 0.0625)
MDP_QUEUE_BOUND = 30

# Corridor controlled experiment
CORRIDOR_REPLICATIONS = 3
CORRIDOR_HORIZON_MIN = 50_000.0
CORRIDOR_STOPS = 3

# Schedule-replay monitor (mirrors real_data/rv_monitor.py)
RV_WINDOW_GAPS = 4
RV_THRESHOLD = 0.50
SYNTHETIC_PASSENGER_SLA = 0.95
