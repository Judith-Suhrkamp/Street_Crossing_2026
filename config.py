"""
config.py
---------

Central configuration for the Dynamic Stability experiment.

Only modify this file when changing experiment settings.
"""

from pathlib import Path
from dataclasses import dataclass, field


# ==========================================================
# Project directories
# ==========================================================

PROJECT_DIR = Path(__file__).resolve().parent

VIDEO_DIR = PROJECT_DIR / "videos"

DATA_DIR = PROJECT_DIR / "data"
LOG_DIR = PROJECT_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# ==========================================================
# Configuration Dataclass
# ==========================================================

@dataclass(slots=True)
class ExperimentConfig:
    """
    Global experiment configuration.
    """
    # ------------------------------------------------------
    # Dummy naming  
    # ------------------------------------------------------
    name = "T01"
    save_path = r"D:\Qualysis_Projects\Balance_Project_Kim_Suhrkamp\Data"

    # ------------------------------------------------------
    # Display
    # ------------------------------------------------------
    display_index:      int = 2
    fullscreen:         bool = True

    fps:                int = 1000                                               # Necessary for the videos 

    background_color:   tuple[int, int, int] = (255, 255, 255)

    # ------------------------------------------------------
    # Timing
    # ------------------------------------------------------
    break_every:        int = 16
    break_duration:     int = 30
    break_blocks:       int = 180

    wait_after_sound:   float = 0.10

    # ------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------
    quit_key:           str = "escape"
    repeat_key:         str = "r"

    # ------------------------------------------------------
    # Experiment                                                Yet just for the testing. Adapt later ! Change randomisation process!!
    # ------------------------------------------------------
    n_trials:           int = 64
    n_nogo:             int = 16
    n_per_block:        int = 16

    session_default:    str = "01"

    # ------------------------------------------------------
    # Trigger
    # ------------------------------------------------------
    use_trigger: bool = True
    trigger_key: str = "space"                                  # Needs to be adapted if used with QTM

    # ------------------------------------------------------
    # Videos                                                    
    # ------------------------------------------------------

    videos: list[Path] = field(default_factory=lambda: [
        #VIDEO_DIR / "L_R.MP4",
        VIDEO_DIR / "R_S_02.MP4",
        #VIDEO_DIR / "S.MP4",
        VIDEO_DIR / "L_S.MP4",
        VIDEO_DIR / "R_S.MP4",
        VIDEO_DIR / "L_S_02.MP4",
    ])

    nogo_video: list[Path] = field(default_factory=lambda: [
        VIDEO_DIR / "Car_01.MP4",
        #VIDEO_DIR / "Car_02.MP4",
        #VIDEO_DIR / "Car_03.MP4",
        #VIDEO_DIR / "Car_04.MP4",
    ])

    dot_diameter_cm:    float = 10.0
    screen_width_cm:    float = 60.0
    dot_grey:           tuple[int,int,int] = (128,128,128)
    dot_green:          tuple[int,int,int] = (0,255,0)
    # ------------------------------------------------------
    # Sounds
    # ------------------------------------------------------

    nogo_sound: Path = (
        PROJECT_DIR/
        "dragon-studio-car-honk-386166.mp3"
        )

    # ------------------------------------------------------
    # QTM
    # ------------------------------------------------------
    qtmmode:                    str = 'manual'
    duration:                   int = 20 # Legacy value: NOT applied to QTM capture duration.
    fs:                         float = 50 #??
    log:                        bool = False
    analog_python:              bool = True
    force_threshold:            int = 20 #

    # Timeout limits for different cases.
    qtm_start_timeout:          float = 240.0
    qtm_force_wait_timeout:     float = 10.0
    qtm_external_stop_timeout:  float = 30.0
    qtm_capture_stop_timeout:   float = 60.0
    qtm_save_timeout:           float = 60.0

# Global configuration object
config = ExperimentConfig()