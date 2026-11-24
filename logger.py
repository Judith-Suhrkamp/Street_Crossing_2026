"""
logger.py
----------

Handles saving experiment data.

Creates:
    - CSV trial data
    - text log file
"""

from __future__ import annotations
import csv
import logging
import uuid
from dataclasses import asdict
from config import DATA_DIR, LOG_DIR
from gui import ParticipantInfo
from gui import get_participant_info


class ExperimentLogger:
    """
    Saves trial data and experiment events.
    """

    def __init__(
        self,
        participant_info: ParticipantInfo
    ):

        self.info = participant_info
        filename = self.info.base_name


        self.csv_path = (
            DATA_DIR /
            f"{filename}.csv"
        )

        self.log_path = (
            LOG_DIR /
            f"{filename}.log"
        )


        # -----------------------------
        # Text logging
        # -----------------------------

        logging.basicConfig(
            filename=self.log_path,
            level=logging.INFO,
            format="%(asctime)s | %(message)s",
            #force=True #in case logger is ever re-instantiated in one process
        )

        # -----------------------------
        # CSV logging
        # -----------------------------

        self.file = open(
            self.csv_path,
            "w",
            newline="",
            encoding="utf-8"
        )


        self.writer = csv.DictWriter(
            self.file,
            fieldnames=[

                "trial_id",

                "participant",
                "session",
                "block_order",
                "date",

                "block",
                "trial",
                "video",
                "condition",
                "side",

                "trial_start",
                "trial_end",
                "trial_duration",

                "video_onset",
                "video_end",

                "nogo_start",
                "nogo_end",

                "trigger_1",
                "trigger_2",
                "trigger_3",
                "python_delay",
                #"screen_delay"
            ]
        )


        self.writer.writeheader()
        self.file.flush()


    # -------------------------------------------------

    def log_trial(
        self,
        *,
        block: int,
        trial: int,

        video: str,

        condition: str,
        side: str | None,

        trial_start: float,
        trial_end: float,
        trial_duration: float,

        video_onset: float,
        video_end: float,

        nogo_start: float,
        nogo_end: float,

        trigger_1: float | None = None,
        trigger_2: float | None = None,
        trigger_3: float | None = None,
        python_delay: float | None = None,
        #screen_delay: float | None = None,
    ):
        """
        Save one completed trial.
        """


        trial_id = uuid.uuid4().hex[:8]

        row = {
            "trial_id":         trial_id,

            **asdict(self.info),

            "block":            block,
            "trial":            trial,

            "video":            video,

            "condition":        condition,
            "side":             side,

            "trial_start":      trial_start,
            "trial_end":        trial_end,
            "trial_duration":   trial_duration,

            "video_onset":      video_onset,
            "video_end":        video_end,

            "nogo_start":       nogo_start,
            "nogo_end":         nogo_end,

            "trigger_1":        trigger_1,
            "trigger_2":        trigger_2,
            "trigger_3":        trigger_3,
            "python_delay":     python_delay,
            #"screen_delay":     screen_delay,
        }


        self.writer.writerow(row)

        self.file.flush()


        logging.info(
            f"Saved block {block}, trial {trial}"
        )


    # -------------------------------------------------

    def close(self):

        logging.info(
            "Experiment finished."
        )

        self.file.close()
        

if __name__ == "__main__":
    info = get_participant_info()
    if info is None:
        print("No participant registered.")
    test = ExperimentLogger(info)
    #print(csv.DictReader(test))