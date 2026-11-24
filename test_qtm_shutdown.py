"""Lab diagnostic: start -> wait 10 s -> software Stop -> confirmed stop -> Save.

Run this file first. No participant GUI, video, sound or force threshold is used.
The output is diagnostic data, not a valid experimental trial.
"""
from datetime import datetime
import time
import traceback

from config import config
from QTMconnect import QTMReader


def main():
    reader = QTMReader()
    failed = False
    try:
        reader.connect()
        name = "DIAGNOSTIC_NO_STEP_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        reader.start_recording(name)
        print("NO-STEP TEST: do not step on the force plate; do not press STOP.")
        started = time.perf_counter()
        while time.perf_counter() - started < config.qtm_force_wait_timeout:
            if reader.disconnected.is_set():
                raise ConnectionError("QTM disconnected during diagnostic.")
            if reader.packet_error is not None:
                raise RuntimeError(f"Force callback error: {reader.packet_error}")
            if reader.capture_stopped.is_set():
                print("QTM capture ended before the test interval elapsed.")
                break
            time.sleep(0.1)
        print(f"Force packets received: {reader.packet_count}")
        reader.stop_recording(force_stop=True)
        print("PASS: QTM reported CaptureStopped and accepted Save.")
        print("Check QTM Messages too: this PASS does not validate analog data quality.")
    except BaseException:
        failed = True
        print("FAIL: diagnostic did not complete. Keep QTM open to inspect/recover its measurement.")
        raise
    finally:
        try:
            reader.close()
        except Exception:
            if not failed:
                raise
            traceback.print_exc()


if __name__ == "__main__":
    main()
