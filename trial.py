# Rewrite the shuffel of NoGo trials so that each speed has the same amount of NoGo trials at the very end

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random
from config import config
from enum import Enum

class NogoMode(Enum):
    SOUND = "sound"
    VIDEO = "video"

class TrialCondition(Enum):
    GO = "go"
    NOGO = "nogo"

@dataclass(slots=True)
class Trial:
    """
    Represents one experimental trial.
    """

    video: Path
    condition: TrialCondition          # "go" or "nogo"
    side: str | None        # "left", "right" or None

def create_go_nogo_order(n_go_per_block, n_nogo_per_block, previous_was_nogo=False):
    # First block of a condition must start with GO.
    # Prevent NOGOs in a row.

    gaps = set(random.sample(
        range(1, n_go_per_block),
        n_nogo_per_block
    ))

    go_nogo_order = []

    for i in range(n_go_per_block +1):

        if i in gaps:
            go_nogo_order.append((TrialCondition.NOGO, "right"))
        go_nogo_order.append((TrialCondition.GO, None))

    return go_nogo_order


def create_trials() -> list[Trial]:
    """
    Create one randomized list of trials.
    """
    
    # Create video order and shuffle random
    n_videos = len(config.videos)

    if config.n_trials % n_videos != 0:
        raise ValueError(
            "Number of trials must be divisible by "
            "number of videos."
        )

    repetitions = config.n_trials // n_videos

    videos = []

    for video in config.videos:
        videos.extend([video] * repetitions)

    random.shuffle(videos)

    # Get number of total go and nogo trials
    if config.n_nogo % 2 != 0:
        raise ValueError(
            "n_nogo must be even."
        )

    n_blocks = config.n_trials // config.n_per_block
    n_go_per_block = config.n_per_block - (config.n_nogo // n_blocks)
    n_nogo_per_block = config.n_nogo // n_blocks

    # Ensure there are enough gaps within one trial
    if n_nogo_per_block > n_go_per_block +1:
        raise ValueError("Amount of NoGo Trials exceed the structure for this experiement with to few Go trials.")
    
    # Not used in this experiment
    #nogo_sides = (["left"]*(config.n_nogo//2) + ["right"]*(config.n_nogo//2))
    #random.shuffle(nogo_sides)

    condition_order = []

    for condition in range(2):

        condition_order = []
        previous_was_nogo = False

        for block in range(n_blocks):

            block_order = create_go_nogo_order(
                n_go_per_block,
                n_nogo_per_block,
                previous_was_nogo=(previous_was_nogo or block == 0)
            )

            condition_order.extend(block_order)

            previous_was_nogo = (
                block_order[-1][0] == TrialCondition.NOGO
            )
            
            # Debugging line
            print(f"Block {block +1}: GO {n_go_per_block}, NOGO {n_nogo_per_block}")

    """
    nogo_positions = set(random.sample(range(1, n_go),config.n_nogo))

    # Get GO/NoGo order    
    go_nogo_order = [(TrialCondition.GO, None)]
    #sides = iter(nogo_sides)
    for i in range(1, n_go):
        if i in nogo_positions:
            go_nogo_order.append((TrialCondition.NOGO, "right"))
        go_nogo_order.append((TrialCondition.GO, None))
    """

    # Assign videos and NoGo to either or. 
    trials = []

    for video, (condition, side) in zip(videos, condition_order):

        trials.append(
            Trial(
                video=video,
                condition=condition,
                side=side
            )
        )

    return trials

#if __name__