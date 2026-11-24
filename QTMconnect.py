"""
qtmconnect.py
-------------

Connecting to and streaming realtime data from qtm.
"""
#Necessary for connection to QTM and real time output (coding two threads)
import qtm_rt 
import asyncio
import concurrent.futures

# Additional packages for synch
from config import config, LOG_DIR
import time
import logging
from pathlib import Path
import threading

# dataclass import (keeps eveything nice and clean)
#from dataclasses import dataclass, field

#@dataclass
class QTMReader:
    #threshold_crossed:          threading.Event     = field(default_factory=threading.Event)
    #threshold_time:             int                 = field(default=0)
    #capture_started:            threading.Event     = field(default_factory=threading.Event)
    #capture_stopped:            threading.Event     = field(default_factory=threading.Event)
    def __init__(self):
        self.threshold_crossed = threading.Event()
        self.capture_started = threading.Event()
        self.capture_stopped = threading.Event()
        self.threshold_time = 0
        self.qtm_starting_time = None
        self.qtm_stop_time = None
        self.qsys_save_path = None
        self.recording = False
        self.saved = True
        self.idle = None
        self.connection = None
        self.loop = None
        self.thread = None
        self._closed = False
        self._streaming = False
        self._pending_capture = False
        self._finish_attempted = False
        self._connected_event = threading.Event()
        self.disconnected = threading.Event()
        self.packet_error = None
        self.packet_count = 0
        self.last_packet_time = None
        self.last_state = None

        self.log = logging.getLogger(f"qtm_patch.{id(self)}")
        self.log.setLevel(logging.INFO)
        self.log.propagate = False
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(Path(LOG_DIR) / "qtm_patch.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        self.log.addHandler(handler)

    def start_loop(self):
        if self._closed:
            raise RuntimeError("This QTMReader has already been closed.")
        if self.loop is not None:
            return
        self.loop = asyncio.new_event_loop()
        ready = threading.Event()
        def worker():
            asyncio.set_event_loop(self.loop)
            self.loop.call_soon(ready.set)
            self.loop.run_forever()
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()
        self.thread = threading.Thread(target=worker, name="QTM-asyncio", daemon=True)
        self.thread.start()
        if not ready.wait(timeout=5):
            raise RuntimeError("QTM worker loop did not start.")

    def _run(self, coro, timeout=120.0, pump_ui=True):
        if self._closed or self.loop is None or not self.loop.is_running():
            coro.close()
            raise RuntimeError("QTM event loop is not running.")
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        deadline = time.monotonic() + timeout
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("QTM operation exceeded its total time limit.")
                try:
                    return future.result(timeout=min(0.05, remaining))
                except concurrent.futures.TimeoutError:
                    # A TimeoutError raised BY the task must not be mistaken for polling.
                    if future.done():
                        return future.result()
                    if pump_ui and self.idle is not None:
                        self.idle()
        except BaseException:
            future.cancel()
            raise

    async def _command(self, label, coro):
        self.log.info("COMMAND BEGIN %s", label)
        try:
            result = await coro
        except BaseException:
            self.log.exception("COMMAND FAILED %s", label)
            raise
        self.log.info("COMMAND DONE %s: %r", label, result)
        return result

    def on_event(self, event):
        now = time.perf_counter()
        self.last_state = event
        self.log.info("EVENT %s perf_counter=%.6f", event, now)
        E = qtm_rt.QRTEvent
        if event == E.EventConnected:
            self._connected_event.set()
        elif event == E.EventCaptureStarted:
            if not self.capture_started.is_set():
                self.qtm_starting_time = now
            self.recording = True
            self.capture_started.set()
        elif event == E.EventCaptureStopped:
            if not self.capture_stopped.is_set():
                self.qtm_stop_time = now
            self.recording = False
            self.capture_stopped.set()

    def on_disconnect(self, *args):
        self.disconnected.set()
        self.log.error("QTM connection lost: %r", args)

    def on_packet(self, packet):
        self.packet_count += 1
        self.last_packet_time = time.perf_counter()
        try:
            data = packet.get_force()
            if data is None:
                return
            _, plates = data
            for plate, forces in plates:
                # Intentionally preserve original detection rule in this lifecycle patch.
                if plate.id == 2 and forces:
                    fy = forces[-1].y
                    if fy > config.force_threshold and not self.threshold_crossed.is_set():
                        self.threshold_time = time.perf_counter()
                        self.threshold_crossed.set()
                        self.log.info("FORCE THRESHOLD plate=2 Fy=%r", fy)
                        print(f"Threshold crossed at: {self.threshold_time:.6f}")
        except Exception as exc:
            self.packet_error = repr(exc)
            self.log.exception("Force packet callback failed")

    async def _wait_flag(self, flag, timeout, label):
        deadline = time.monotonic() + timeout
        while not flag.is_set():
            if self.disconnected.is_set():
                raise ConnectionError(f"QTM disconnected while waiting for {label}.")
            if time.monotonic() >= deadline:
                raise TimeoutError(f"QTM did not report {label} within {timeout:g} seconds.")
            await asyncio.sleep(0.01)

    def connect(self):
        self.start_loop()
        return self._run(self._connect(), timeout=20)

    async def _connect(self):
        self.connection = await qtm_rt.connect(
            "127.0.0.1", port=22223, version="1.22", timeout=5,
            on_event=self.on_event, on_disconnect=self.on_disconnect,
        )
        if self.connection is None:
            raise ConnectionError("Could not connect to QTM.")
        await self._command("TakeControl", self.connection.take_control("Hello"))
        print(f"QTM diagnostic log: {Path(LOG_DIR) / 'qtm_patch.log'}")

    def start_recording(self, name):
        return self._run(self._start_recording(name), timeout=config.qtm_start_timeout + 30)

    async def _start_recording(self, name):
        if self._pending_capture or not self.saved:
            raise RuntimeError("Previous capture has not been saved; no new capture was started.")
        state = await self._command("GetState before start", self.connection.get_state())
        E = qtm_rt.QRTEvent
        if state in (E.EventCaptureStarted, E.EventWaitingForTrigger):
            raise RuntimeError("QTM already has an active capture. Finish it in QTM first.")
        if state != E.EventConnected:
            self._connected_event.clear()
            await self._command("New", self.connection.new())
            # An event can arrive before the New command returns; the flag retains it.
            if not self._connected_event.is_set():
                await self._command("GetState after New", self.connection.get_state())
            await self._wait_flag(self._connected_event, 15, "camera connection")

        self.qsys_save_path = str(Path(config.save_path) / f"{name}.qtm")
        self.threshold_time = 0
        self.qtm_starting_time = self.qtm_stop_time = None
        self.threshold_crossed.clear()
        self.capture_started.clear()
        self.capture_stopped.clear()
        self.packet_error = None
        self.packet_count = 0
        self.last_packet_time = None
        self._finish_attempted = False
        self._pending_capture = True
        self.saved = False
        print(f"QTM START: {name}. Press the external START trigger if QTM requests it.")
        await self._command("Start", self.connection.start())
        await self._wait_flag(self.capture_started, config.qtm_start_timeout, "CaptureStarted")
        await self._command("StreamFrames Force", self.connection.stream_frames(
            components=["force"], on_packet=self.on_packet))
        self._streaming = True
        return self.qtm_starting_time

    def stop_recording(self, force_stop=False):
        total = config.qtm_external_stop_timeout + config.qtm_capture_stop_timeout + config.qtm_save_timeout + 40
        return self._run(self._stop_recording(force_stop), timeout=total)

    async def _stop_recording(self, force_stop=False):
        if not self._pending_capture:
            if self.saved:
                return self.qtm_stop_time
            raise RuntimeError("No capture is available to finish.")
        if self._finish_attempted:
            raise RuntimeError("Capture finalization already failed; inspect QTM and save manually.")
        self._finish_attempted = True
        external_stop_missing = False
        if not self.capture_stopped.is_set():
            if not force_stop:
                print("QTM STOP: press the external STOP trigger now.")
                try:
                    await self._wait_flag(self.capture_stopped, config.qtm_external_stop_timeout, "external capture stop")
                except TimeoutError:
                    external_stop_missing = True
                    force_stop = True
                    print("No external stop received. Attempting controlled Stop and Save; run will then abort.")
            if force_stop and not self.capture_stopped.is_set():
                print("QTM STOP: sending Stop command for an incomplete/aborted trial.")
                # Command acknowledgement alone does not mean the capture has stopped.
                await self._command("Stop", self.connection.stop())
                await self._wait_flag(self.capture_stopped, config.qtm_capture_stop_timeout, "CaptureStopped")
        if self._streaming:
            await self._command("StreamFrames Stop", self.connection.stream_frames_stop())
            self._streaming = False
        await self._save_when_ready()
        self._pending_capture = False
        self.log.info("CAPTURE FINALIZED packets=%d callback_error=%r", self.packet_count, self.packet_error)
        if external_stop_missing:
            raise RuntimeError("External STOP trigger timed out. QTM capture was saved; this run is aborted.")
        return self.qtm_stop_time

    async def _save_when_ready(self):
        deadline = time.monotonic() + config.qtm_save_timeout
        retry_notified = False
        while True:
            try:
                await self._command("Save", self.connection.save(self.qsys_save_path))
                self.saved = True
                print(f"QTM SAVED: {self.qsys_save_path}")
                return
            except Exception as exc:
                # Only this transient QTM response is retried, never arbitrary errors.
                if "active camera connection exists" not in str(exc).lower():
                    raise
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "QTM still has an active camera connection after CaptureStopped. "
                        "Capture was NOT confirmed saved. Check QTM Messages; "
                        "do not start another capture. Save the current measurement manually."
                    ) from exc
                if not retry_notified:
                    print("QTM is still finishing data handling; waiting before Save retry...")
                    retry_notified = True
                await asyncio.sleep(0.5)

    def close(self):
        if self._closed:
            return
        try:
            if self.loop is not None and self.loop.is_running():
                total = config.qtm_capture_stop_timeout + config.qtm_save_timeout + 40
                self._run(self._async_shutdown(), timeout=total, pump_ui=False)
        finally:
            self._closed = True
            if self.loop is not None and self.loop.is_running():
                # Stop the loop from the caller AFTER the coroutine result was delivered.
                self.loop.call_soon_threadsafe(self.loop.stop)
            if self.thread is not None:
                self.thread.join(timeout=5)
            for handler in list(self.log.handlers):
                handler.close()
                self.log.removeHandler(handler)

    async def _async_shutdown(self):
        if self.connection is None:
            return
        try:
            if self._pending_capture and not self._finish_attempted and self.capture_started.is_set():
                await self._stop_recording(force_stop=True)
            elif self._pending_capture and not self.saved:
                print("QTM capture was not confirmed saved. Inspect/save it in QTM before restarting.")
                self.log.error("Unfinalized capture left for manual recovery: %s", self.qsys_save_path)
        finally:
            # Never issue QTM Close: it could discard an unsaved measurement.
            try:
                if self._streaming:
                    await self._command("StreamFrames Stop during cleanup", self.connection.stream_frames_stop())
                    self._streaming = False
            finally:
                try:
                    await self._command("ReleaseControl", self.connection.release_control())
                finally:
                    self.connection.disconnect()
                    print("QTM client disconnected.")


if __name__ == "__main__":
    reader = QTMReader
    reader.start_recording
    reader.stop_recording