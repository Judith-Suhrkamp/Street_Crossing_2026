"""
player.py
---------
Video playback module.

Responsible only for displaying videos.
Timing, logging and trial logic are handled in there own scripts.
"""
# Onset_time = None if first frame fails. Acceptable to continue and "just loose one datapoint" or quit entire experiment?

from __future__ import annotations
import time
from pathlib import Path
import cv2
import pygame
from config import config
import os


class VideoPlayer:
    """
    Handles fullscreen video playback.
    """

    def __init__(self):

        os.environ['SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS'] = '0'
        pygame.init()
        self.sizes = pygame.display.get_desktop_sizes()
        flag = pygame.FULLSCREEN if config.fullscreen else 0

        self.screen = pygame.display.set_mode(size= self.sizes[config.display_index],
                                              flags = flag,
                                              display=config.display_index
                                              )
        pygame.display.set_caption("Dynamic Stability Experiment")
        self.clock = pygame.time.Clock()
        width_px = self.sizes[config.display_index][0]
        px_per_cm = width_px /config.screen_width_cm
        self.dot_radius = int(config.dot_diameter_cm * px_per_cm/2)
        self.dot_center = (self.dot_radius, self.dot_radius)

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
                if event.key == pygame.K_r:
                    return "repeat"

        return True
    
    def _draw_dot(self,color):
        pygame.draw.circle(self.screen,color,self.dot_center,self.dot_radius)

    # --------------------------------------------------------

    def play(
            self, 
            video: Path,
            keep_last_frame:bool = True,
            stop_event = None,
            ) -> tuple[float, float]:
        """
        Play one video.

        Parameters
        ----------
        video
            Path to video file.
        Returns
        -------
        onset_time
            Time of first displayed frame.
        end_time
            Time when playback finished.
        """
        #pygame.draw.circle(self.screen, color=3,radius=5,draw_top_left=True)
        cap = cv2.VideoCapture(str(video))

        if not cap.isOpened():
            raise FileNotFoundError(video)

        fps = cap.get(cv2.CAP_PROP_FPS)

        if fps <= 1:
            fps = config.fps

        frame_duration = 0.01 #/ fps

        onset_time = None
        frame_times = []

        while True:

            ok, frame = cap.read()

            if not ok:
                break

            if not self._check_events():
                cap.release()
                pygame.quit()
                raise SystemExit
            
            if stop_event is not None and stop_event.is_set():
                break
                
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            frame = cv2.resize(
                frame,
                (self.sizes[config.display_index])
            )

            surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))

            self.screen.blit(surface, (0, 0))
            self._draw_dot(config.dot_grey)
            pygame.display.flip()
            now = time.perf_counter()
            frame_times.append(now)

            if onset_time is None:
                onset_time = now

            self.clock.tick(fps)
        
        intervals = [b - a for a,b in zip(frame_times,frame_times[1:])]
        self.last_stats = {
            "frame_interval_mean": sum(intervals) / len(intervals) if intervals else None,
            "frame_interval_max": max(intervals) if intervals else None,
            "late_frames": sum(1 for d in intervals if d > 1.5 /fps)
        }

        cap.release()

        if onset_time is None:
            raise OSError(f"No readable frames in video: {video}")
    
        if not keep_last_frame:
            self.screen.fill(config.background_color)
            pygame.display.flip()

        self._draw_dot(config.dot_green)
        pygame.display.flip()

        end_time = time.perf_counter()

        return onset_time, end_time
    
    

    # --------------------------------------------------------

    def wait(self, seconds: float):

        start = time.perf_counter()

        while time.perf_counter() - start < seconds:

            if not self._check_events():
                raise SystemExit

            self.clock.tick(config.fps)

    # --------------------------------------------------------

    def close(self):

        pygame.quit()

#if __name__ == "__main__":
#    player = VideoPlayer(self)
#    self.play()