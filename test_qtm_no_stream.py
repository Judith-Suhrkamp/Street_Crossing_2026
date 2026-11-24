"""QTM v1 patch companion diagnostic: capture/Stop/Save WITHOUT RT force streaming.

한국어 사용법
1. 이 파일을 v1 수정본 QTMconnect.py, config.py와 같은 Master-Code 폴더에 둡니다.
2. QTM의 이전 측정은 먼저 수동으로 정리합니다. 저장할 데이터가 있으면 저장합니다.
3. 이 파일을 실행하고 QTM이 요청하면 외부 시작 트리거를 한 번 누릅니다.
4. 반력기를 밟거나 종료 트리거를 누르지 않습니다. 영상/소리도 사용하지 않습니다.
5. 10초 후 Stop을 보냅니다. RT Force 스트리밍만 생략하며 아날로그 보드는 유지합니다.
6. 결과와 logs/qtm_patch.log를 확인합니다. 이 진단 측정은 실험 분석용이 아닙니다.

QTM 설정이나 기존 Python 파일을 수정하지 않습니다. 정상 참가자 실험용이 아닙니다.
"""
from datetime import datetime
from pathlib import Path
import traceback
import asyncio

import qtm_rt
from config import config
from QTMconnect import QTMReader


async def capture_without_stream(reader, name):
    conn = reader.connection
    reader.log.info("=== DIAGNOSTIC NO_STREAM: analog board enabled, no StreamFrames request ===")
    state = await reader._command("NO_STREAM GetState", conn.get_state())
    E = qtm_rt.QRTEvent
    if state in (E.EventCaptureStarted, E.EventWaitingForTrigger):
        raise RuntimeError("QTM has an active/waiting capture. Finish/recover it in QTM first.")
    if state != E.EventConnected:
        reader._connected_event.clear()
        await reader._command("NO_STREAM New", conn.new())
        if not reader._connected_event.is_set():
            await reader._command("NO_STREAM GetState after New", conn.get_state())
        await reader._wait_flag(reader._connected_event, 15, "camera connection")

    reader.qsys_save_path = str(Path(config.save_path) / f"{name}.qtm")
    reader.qtm_starting_time = reader.qtm_stop_time = None
    reader.capture_started.clear()
    reader.capture_stopped.clear()
    reader.threshold_crossed.clear()
    reader._finish_attempted = False
    reader._pending_capture = True
    reader.saved = False
    print("NO_STREAM TEST: press the external START trigger if QTM requests it.")
    await reader._command("NO_STREAM Start", conn.start())
    await reader._wait_flag(reader.capture_started, config.qtm_start_timeout, "CaptureStarted")

    # The only intended change from test_qtm_shutdown.py:
    # do not request StreamFrames. QTM still acquires the configured analog devices.
    print("Capture started. Do not step or press STOP; waiting 10 seconds without RT streaming.")
    deadline = asyncio.get_running_loop().time() + config.qtm_force_wait_timeout
    while asyncio.get_running_loop().time() < deadline and not reader.capture_stopped.is_set():
        if reader.disconnected.is_set():
            raise ConnectionError("QTM disconnected during NO_STREAM test.")
        await asyncio.sleep(0.1)
    await reader._stop_recording(force_stop=True)
    print("PASS NO_STREAM: QTM reported CaptureStopped and accepted Save.")
    print("Check QTM Messages separately; this does not validate analog data quality.")


def main():
    reader = QTMReader()
    failed = False
    try:
        reader.connect()
        name = "DIAGNOSTIC_NO_STREAM_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        total = (config.qtm_start_timeout + config.qtm_force_wait_timeout +
                 config.qtm_capture_stop_timeout + config.qtm_save_timeout + 60)
        reader._run(capture_without_stream(reader, name), timeout=total, pump_ui=False)
    except BaseException:
        failed = True
        print("FAIL NO_STREAM: keep QTM open to inspect/recover its current measurement.")
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
