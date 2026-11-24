"""
example_trials.py
---------

Run single Go/No_go trials WITHOUT QTM to familiarise the participant with test procedure. 

1. Menu appears to choose between:
    G = Go trial
    L = NoGo left SOUND
    R = NoGo right SOUND
    V = NoGo VIDEO
    Esc = quit
2. Main video plays
3. If cond == NoGo 
    Threshold is simulated by experimenter pressing the trigger key (config.trigger_key, default = space). 
    NoGo fires imediately after the trigger.
4. Timings are printed in the terminal.

!! IMPORTANT !! For this to run config.use_trigger needs to be True!!

Run with: python example_trials.py in any terminal when the folder is opened.
"""
## IMPORTS ##
from __future__ import annotations
import random
import pygame

from config import config
from player import VideoPlayer
from sound import SoundPlayer
from trigger import Trigger

# ----------------------------------------------------------
# Menu
# ----------------------------------------------------------

MENU_LINES = [
    "Choose a test trial:",
    "G  =  Go",
    "L  =  No-Go, sound left",
    "R  =  No-Go, sound right",
    "V  =  No-Go, video",
    "Esc  =  quit",
]

# key -> (condition, nogo mode, side)
KEYMAP = {
    pygame.K_g: ("go", None, None),
    pygame.K_l: ("nogo", "sound", "left"),
    pygame.K_r: ("nogo", "sound", "right"),
    pygame.K_v: ("nogo", "video", None),
}


def choose_trial(player):
    """Show the menu and return (condition, mode, side), or None to quit."""
    font = pygame.font.SysFont(None, 64)

    player.screen.fill(config.background_color)
    y = 100
    for line in MENU_LINES:
        text = font.render(line, True, (0, 0, 0))
        player.screen.blit(text, (150, y))
        y += 90
    pygame.display.flip()

    print("\nMenu: G = Go | L = NoGo sound left | R = NoGo sound right | V = NoGo video | Esc = quit")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in KEYMAP:
                    return KEYMAP[event.key]
        pygame.time.wait(10)


# ----------------------------------------------------------
# One trial
# ----------------------------------------------------------

def pick(value):
    """config.nogo_video can be a single path or a list of paths."""
    if isinstance(value, (list, tuple)):
        return random.choice(value)
    return value


def ms(start, end):
    return f"{(end - start) * 1000:.1f} ms"


def run_trial(player, sound, trigger, condition, mode, side):
    video = random.choice(config.videos)
    label = "GO" if condition == "go" else f"NOGO ({mode}{', ' + side if side else ''})"
    print(f"\n--- {label} trial | video: {video.name} ---")

    # Main video
    video_onset, video_end = player.play(video, keep_last_frame=True)
    main_stats = getattr(player, "last_stats", None)   # only exists once frame timing is added

    print(f"Video duration: {ms(video_onset, video_end)}")
    if main_stats:
        print(f"Frame timing (main video): {main_stats}")

    # No-Go cue
    if condition == "nogo":
        key = config.trigger_key.upper()
        print(f"Press [{key}] to simulate the step onto the force plate ...")
        threshold_time = trigger.wait_for_trigger()

        if mode == "sound":
            nogo_start, nogo_end = sound.play(side)
        else:
            nogo_start, nogo_end = player.play(pick(config.nogo_video), keep_last_frame=True)

        print(f"Step -> No-Go onset (software): {ms(threshold_time, nogo_start)}")
        print(f"No-Go cue duration: {ms(nogo_start, nogo_end)}")
        nogo_stats = getattr(player, "last_stats", None)
        if mode == "video" and nogo_stats:
            print(f"Frame timing (No-Go video): {nogo_stats}")

    player.wait(1.5)        # let the last frame stay on screen briefly


## MAIN ##
def main ():
    player = VideoPlayer()
    sound = SoundPlayer()
    trigger = Trigger()

    try:
        while True:
            choice = choose_trial(player)
            if choice is None:
                break
            run_trial(player,sound,trigger,*choice)
    
    except SystemExit:
        print("Trial stopped by experimenter")

    finally:
        player.close()
        sound.close()
        trigger.close()

if __name__ == "__main__":
    main()