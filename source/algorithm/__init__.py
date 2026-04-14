"""Algorithm package for Futoshiki solvers."""

from .astar import astar_solver
from .backtracking import backtracking_solver
from .backward import backward_chaining_solver
from .bruteforce import bruteforce_solver
from .forward import forward_chaining_solver

__all__ = [
    "astar_solver",
    "backtracking_solver",
    "backward_chaining_solver",
    "bruteforce_solver",
    "forward_chaining_solver",
]
