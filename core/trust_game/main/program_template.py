from typing import List, Tuple, Generator, Callable
import numpy as np
import random
import csv
import multiprocessing


class UserParameter:
    inequalityAversion: float  # {0, 0.4, 1}
    riskAversion: float  # {0.4, 0.6, 0.8, 1, 1.2, 1.4, 1.6, 1.8}
    theoryOfMindSophistication: int  # {0, 1, 2, 3, 4}
    planning: float  # {1, 2, 3, 4}
    irritability: float  # {0, 0.25, 0.5, 0.75, 1}
    irritationAwareness: int  # {0, 1, 2, 3, 4}
    inverseTemperature: float  # {1/4, 1/3, 1/2, 1/1}

    def __init__(
        self,
        inequalityAversion: float,
        riskAversion: float,
        theoryOfMindSophistication: int,
        planning: float,
        irritability: float,
        irritationAwareness: int,
        inverseTemperature: float,
    ):
        self.inequalityAversion = inequalityAversion
        self.riskAversion = riskAversion
        self.theoryOfMindSophistication = theoryOfMindSophistication
        self.planning = planning
        self.irritability = irritability
        self.irritationAwareness = irritationAwareness
        self.inverseTemperature = inverseTemperature


class State:
    round: int  # round = len(history)
    history: List[Tuple[int, int]]  # [(investor's action), (trustee's action)]
    # history represents the amount invested by the investor and the amount returned by the trustee in the previous i rounds of the game

    def __init__(self, round: int, history: List[Tuple[int, int]]):
        self.round = round
        self.history = history


def policy(user_parameter: UserParameter, state: State) -> List[float]:
    """
    Determines the investor's policy as a probability distribution over possible actions.

    Args:
        user_parameter (UserParameter): The individual parameters that may influence the policy.
        state (State): The current state of the game&individual that which may include various factors affecting the decision.

    Returns:
        List[float]: A list representing the probability distribution over possible actions:
                     [p(invest 0), p(invest 5), p(invest 10), p(invest 15), p(invest 20)].
    """
    # Please fill in this policy function to better fit human behavior