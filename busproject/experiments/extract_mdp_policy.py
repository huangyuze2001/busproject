"""Convenience entry point for the baseline MDP optimal-action map.

The action extraction is implemented in mdp_dt_sensitivity.py so that the
policy and the reward calculation always use identical finite-horizon semantics.
Running this script regenerates the full dt sensitivity and policy outputs.
"""
from mdp_dt_sensitivity import main

if __name__ == "__main__":
    main()
