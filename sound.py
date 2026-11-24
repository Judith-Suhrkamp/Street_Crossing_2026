"""
sound.py
---------

Stereo sound playback for the Dynamic Stability experiment.

Responsible only for playing sounds.
Timing, logging and trial logic are handled elsewhere.
"""

from __future__ import annotations
import time
from pathlib import Path
import pygame
from config import config


class SoundPlayer:
    """
    Handles stereo sound playback.
    """

    def __init__(self):
        pygame.mixer.init()
        self.sound = pygame.mixer.Sound(str(config.nogo_sound))

    # --------------------------------------------------------

    def _check_events(self):
        """
        Handle keyboard events.
        Returns
        -------
        False
            if user wants to quit.
        True
            otherwise.
        """
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:
                    return False
        return True

    def play(self, side: str) -> tuple[float, float]:
        """
        Play the NoGo sound.

        Parameters
        ----------
        side
            "left" or "right"
        Returns
        -------
        onset_time
            Time when playback started.
        end_time
            Time when playback finished.
        """
        if side not in ("left", "right"):
            raise ValueError(f"Unknown sound side: {side}")

        channel = pygame.mixer.find_channel(True)

        if side == "left":
            channel.set_volume(1.0, 0.0)

        else: #side == "right":
            channel.set_volume(0.0, 1.0)

        channel.play(self.sound)
        onset_time = time.perf_counter()

        while channel.get_busy():
            if not self._check_events():
                raise SystemExit
            time.sleep(0.001)

        end_time = time.perf_counter()

        return onset_time, end_time

    # --------------------------------------------------------

    def close(self):

        pygame.mixer.quit()