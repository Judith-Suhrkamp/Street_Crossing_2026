#Experiment patch v1: retain external normal stop, finalize no-step trials safely.
"""
experiment.py
---------

retain external normal stop, finalize no-step trials safely
"""

from __future__ import annotations

import json
import random
import sys
import time
import traceback
from pathlib import Path

from trial import create_trials, TrialCondition, NogoMode
from config import config, LOG_DIR


class Experiment:
    def __init__(self, participant_info, player, sound, trigger, logger, reader):
        self.info = participant_info
        self.player, self.sound, self.trigger = player, sound, trigger
        self.logger, self.reader = logger, reader
        self.reader.idle = self._idle
        self._closed = False
        self.last_wait_result = None
        self.repeat_requested = False

    def _idle(self):
        result = self.player._check_events()
        #print(result)
        if result == "repeat":
            self.repeat_requested = True
        elif result is False:
            raise SystemExit

    def _wait_for_threshold(self, timeout=None):
        if timeout is None:
            timeout = config.qtm_force_wait_timeout
        start = time.perf_counter()

        while True:
            self._idle()
            if self.reader.disconnected.is_set():
                raise ConnectionError("QTM disconnected during force wait.")
            if self.reader.packet_error is not None:
                raise RuntimeError(f"Force callback error: {self.reader.packet_error}")
            if self.reader.capture_stopped.is_set():
                self.last_wait_result = "capture_stopped_before_nogo"
                return False
            if self.reader.threshold_crossed.wait(timeout=0.005):
                self.last_wait_result = "threshold_detected"
                return True
            if time.perf_counter() - start >= timeout:
                self.last_wait_result = "no_step_timeout"
                print("NO STEP: threshold wait timed out. No NoGo cue will be presented.")
                return False

    def _status(self, name, status, **details):
        # A separate file avoids changing the unavailable logger.py/CSV interface.
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        record = dict(name=name, status=status, perf_counter=time.perf_counter(), **details)
        with (Path(LOG_DIR) / "trial_status.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def run(self):
        print("Trying to connect QTM")
        self.reader.connect()
        trials = create_trials()
        print(trials)

        order = [(1, NogoMode.SOUND), (2, NogoMode.VIDEO)]
        if self.info.block_order != "normal":
            order.reverse()
        for block, mode in order:
            self.run_block(block, mode, trials)
            

    def run_block(self, block, nogo_mode, trials):
        for trial_number, trial in enumerate(trials):
            repeat_trial = True
            #print(f"Before while {repeat_trial}")
            while repeat_trial:
                repeat_trial = False
                #print(f"In while {repeat_trial}")
                name = f"{self.info.base_name}_B{block}_T{trial_number + 1:d}"

                print(f"Block {block}, Trial {trial_number + 1}, {trial.condition.value}")
                self._status(name, "starting", block=block, trial=trial_number,
                            condition=trial.condition.value, stop_policy="external")
                status = "completed"

                try:
                    # Start the measurement 
                    trigger1 = self.reader.start_recording(name)
                    trial_start = time.perf_counter()

                    # Start the video
                    video_onset, video_end = self.player.play(
                        trial.video, keep_last_frame=True, stop_event=self.reader.capture_stopped)
                    
                    # NoGo settings
                    nogo_start = nogo_end = None
                    if self.reader.packet_error is not None:
                        raise RuntimeError(f"Force callback error: {self.reader.packet_error}")
                    if self.reader.capture_stopped.is_set():
                        status = "capture_stopped_before_trial_end"
                    elif trial.condition is TrialCondition.NOGO:
                        if self._wait_for_threshold():
                            if nogo_mode is NogoMode.SOUND:
                                nogo_start, nogo_end = self.sound.play(trial.side)
                            elif nogo_mode is NogoMode.VIDEO:
                                if not config.nogo_video:
                                    raise ValueError("No NoGo video configured.")
                                nogo_start, nogo_end = self.player.play(
                                    random.choice(config.nogo_video), keep_last_frame=True,
                                    stop_event=self.reader.capture_stopped)
                        else:
                            status = self.last_wait_result

                    # An incomplete trial uses a software Stop. A completed one retains
                    # the original external stop policy; no arbitrary observation time is added.

                    # Stop recording
                    trigger3 = self.reader.stop_recording(force_stop=status != "completed")
                    trial_end = time.perf_counter()
                    self._status(name, status, saved=self.reader.saved,
                                packets=self.reader.packet_count, nogo_presented=nogo_start is not None,
                                valid_for_analysis=status == "completed")
                    
                    #print("here")
                    # Save the data
                    self.logger.log_trial(
                        block=block, trial=trial_number, video=str(trial.video),
                        condition=trial.condition.value, side=trial.side,
                        trial_start=trial_start, trial_end=trial_end,
                        trial_duration=trial_end - trial_start, video_onset=video_onset,
                        video_end=video_end, nogo_start=nogo_start, nogo_end=nogo_end,
                        trigger_1=trigger1, trigger_2=self.reader.threshold_time,
                        trigger_3=trigger3, python_delay=video_onset - trigger1,
                        #screen_delay=1,
                    )
                except BaseException as exc:
                    self._status(name, "aborted", reason=repr(exc),
                                saved=self.reader.saved, valid_for_analysis=False)
                    raise
                except KeyboardInterrupt as r:
                    print("Trial will be repeated")
                    trial - 1
                # Check for keyboard input to repeat the trial
                #print(f"Before keyboard {repeat_trial}")
                if self.repeat_requested:
                    repeat_trial = True
                    #print(f"Inside exception {repeat_trial}")
                print(repeat_trial)
                if (trial_number + 1) % config.break_every == 0:
                    self.player.wait(config.break_duration)
                if (trial_number + 1) % config.n_trials == 0:
                    self.player.wait(config.break_blocks)
                self.repeat_requested = False

    def close(self):
        if self._closed:
            return
        self._closed = True
        primary_error_active = sys.exc_info()[0] is not None
        errors = []
        # QTM must finish before pygame disappears; all other resources still close
        # even if QTM finalization fails.
        for label, resource in [("QTM", self.reader), ("sound", self.sound),
                                ("player", self.player), ("trigger", self.trigger),
                                ("logger", self.logger)]:
            try:
                resource.close()
            except Exception as exc:
                errors.append(exc)
                print(f"Cleanup failed ({label}): {exc}")
                traceback.print_exc()
        if errors and not primary_error_active:
            raise errors[0]
