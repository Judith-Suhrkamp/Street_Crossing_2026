"""Entry point with cleanup that preserves the original failure traceback."""
import traceback

from gui import get_participant_info
from logger import ExperimentLogger
from player import VideoPlayer
from sound import SoundPlayer
from trigger import Trigger
from experiment import Experiment
from QTMconnect import QTMReader


def main():
    experiment = None
    resources = []
    try:
        info = get_participant_info()
        if info is None:
            print("No participant registered.")
            return
        print(info.base_name)
        logger = ExperimentLogger(info)
        resources.append(logger)

        player = VideoPlayer()
        resources.append(player)

        sound = SoundPlayer()
        resources.append(sound)

        trigger = Trigger()
        resources.append(trigger)

        reader = QTMReader()
        resources.append(reader)
        
        experiment = Experiment(info, player, sound, trigger, logger, reader)
        experiment.run()
    except (SystemExit, KeyboardInterrupt):
        print("Experiment interrupted by user.")
    except Exception:
        print("Experiment crashed; full traceback follows:")
        raise
    finally:
        if experiment is not None:
            experiment.close()
        else:
            # Also clean up partially constructed experiments.
            for resource in reversed(resources):
                try:
                    resource.close()
                except Exception:
                    traceback.print_exc()


if __name__ == "__main__":
    main()
