#!/usr/bin/env python3
"""Tests for streaming_control's serial and keyboard layers.

The controller cannot be reflashed, so the firmware side is simulated from the
actual sources: ascii_protocol.cpp (replies the FIFO free-slot count to every
'>' / '@', 0xFF when the push failed), dummy_robot.cpp (the command thread
replies 'ok' to USB and UART4), and dummy_robot.h (16-slot osMessageQueue).

Run:  python test_streaming_control.py
"""

import sys
import unittest
from unittest import mock

import serial

import importlib.util
from pathlib import Path

# streaming_control.py is not a valid module name (hyphen-free but the sibling
# CLI is), so load it by path to stay independent of how it is invoked.
_SPEC = importlib.util.spec_from_file_location(
    "streaming_control", Path(__file__).with_name("streaming_control.py"))
sc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sc)


# ---------------------------------------------------------------------------
# Firmware simulator
# ---------------------------------------------------------------------------

class FakeController:
    """Mimics the ASCII protocol of dummy-ref-core-fw over a serial port.

    fifo_depth mirrors osMessageQueueNew(16, 64) in dummy_robot.h. Motion
    commands sit in the queue until drain() runs the command thread, so a test
    can hold the queue full and watch the host react.
    """

    FIFO_DEPTH = 16

    def __init__(self, joints=None, pose=None, auto_drain=True):
        self.rx = bytearray()
        self.tx = bytearray()
        self.fifo = []
        self.auto_drain = auto_drain
        self.joints = joints or [0.0, -73.0, 180.0, 0.0, 0.0, 0.0]
        self.pose = pose or [268.0, 0.0, 118.0, 0.0, 90.0, 0.0]
        self.enabled = False
        self.mode = 1
        self.rejected = 0
        self.accepted = 0

    # -- device side --------------------------------------------------------

    def feed(self, data):
        """Bytes arriving from the host."""
        self.rx += data
        while True:
            idx = self.rx.find(b"\n")
            if idx < 0:
                break
            line = bytes(self.rx[:idx]).strip()
            del self.rx[:idx + 1]
            if line:
                self._on_line(line.decode("ascii", "replace"))

    def _respond(self, text):
        self.tx += (text + "\r\n").encode()

    def _on_line(self, cmd):
        if cmd[0] in ">@&":
            # ascii_protocol.cpp: Push() then Respond("%d", freeSize)
            if len(self.fifo) >= self.FIFO_DEPTH:
                self.rejected += 1
                self._respond("255")          # 0xFF, osMessageQueuePut failed
            else:
                self.fifo.append(cmd)
                self.accepted += 1
                self._respond(str(self.FIFO_DEPTH - len(self.fifo)))
            if self.auto_drain:
                self.drain()
            return
        if cmd[0] == "!":
            if "START" in cmd:
                self.enabled = True
                self._respond("Started ok")
            elif "DISABLE" in cmd:
                self.enabled = False
                self._respond("Disabled ok")
            elif "STOP" in cmd:
                self.enabled = False
                self._respond("Stopped ok")
            return
        if cmd[0] == "#":
            if "GETJPOS" in cmd:
                self._respond("ok " + " ".join(f"{v:.2f}" for v in self.joints))
            elif "GETLPOS" in cmd:
                self._respond("ok " + " ".join(f"{v:.2f}" for v in self.pose))
            elif "CMDMODE" in cmd:
                self.mode = int(cmd.split()[1])
                self._respond(f"ok Set command mode to [{self.mode}]")
            else:
                self._respond("ok")

    def drain(self):
        """Run the command thread: pop everything and ack each one."""
        while self.fifo:
            self.fifo.pop(0)
            self._respond("ok")           # dummy_robot.cpp, INTERRUPTABLE


class FakeSerial:
    """Just enough of pyserial's API for DummySerial."""

    def __init__(self, controller, chunk=None, fail_write=None):
        self.ctl = controller
        self.timeout = 0.02
        self.write_timeout = sc.WRITE_TIMEOUT
        self.is_open = True
        self.chunk = chunk          # cap bytes returned per read (split lines)
        self.fail_write = fail_write  # exception class to raise on write
        self.writes = 0

    @property
    def in_waiting(self):
        n = len(self.ctl.tx)
        return min(n, self.chunk) if self.chunk else n

    def read(self, size=1):
        if self.chunk:
            size = min(size, self.chunk)
        out = bytes(self.ctl.tx[:size])
        del self.ctl.tx[:size]
        return out

    def readline(self):
        idx = self.ctl.tx.find(b"\n")
        if idx < 0:
            out = bytes(self.ctl.tx)
            del self.ctl.tx[:]
            return out
        out = bytes(self.ctl.tx[:idx + 1])
        del self.ctl.tx[:idx + 1]
        return out

    def write(self, data):
        self.writes += 1
        if self.fail_write:
            raise self.fail_write("simulated")
        self.ctl.feed(data)
        return len(data)

    def close(self):
        self.is_open = False


def make_link(controller=None, **kw):
    ctl = controller or FakeController()
    link = sc.DummySerial("COMTEST")
    link.ser = FakeSerial(ctl, **kw)
    return link, ctl


# ---------------------------------------------------------------------------
# Serial layer
# ---------------------------------------------------------------------------

class TestResponseConsumption(unittest.TestCase):

    def test_every_streamed_frame_is_fully_consumed(self):
        """The old code never read; bytes must not accumulate now."""
        link, ctl = make_link()
        for _ in range(500):
            link.send_joints([0, -73, 180, 0, 0, 0], 30)
            link.pump()
        self.assertEqual(len(ctl.tx), 0, "unread bytes left in the port")
        self.assertEqual(len(link._rx), 0, "partial data left buffered")
        self.assertEqual(link.acks, 500)
        self.assertEqual(link.drops, 0)

    def test_unread_bytes_would_otherwise_pile_up(self):
        """Guards the premise: without pump() the buffer grows without bound."""
        link, ctl = make_link()
        for _ in range(500):
            link.send_joints([0, -73, 180, 0, 0, 0], 30)
        self.assertGreater(len(ctl.tx), 2000)

    def test_queue_free_slots_tracked(self):
        link, ctl = make_link(controller=FakeController(auto_drain=False))
        for _ in range(4):
            link.send_joints([0, -73, 180, 0, 0, 0], 30)
        link.pump()
        # 4 queued of 16 → 12 free, reported by the last reply
        self.assertEqual(link.queue_free, 12)
        self.assertEqual(link.acks, 0, "nothing popped yet")
        ctl.drain()
        link.pump()
        self.assertEqual(link.acks, 4)

    def test_full_queue_counts_as_drop_not_as_free_slots(self):
        """0xFF means the command was discarded; it is not a slot count."""
        link, ctl = make_link(controller=FakeController(auto_drain=False))
        for _ in range(20):
            link.send_joints([0, -73, 180, 0, 0, 0], 30)
        link.pump()
        self.assertEqual(ctl.accepted, 16)
        self.assertEqual(ctl.rejected, 4)
        self.assertEqual(link.drops, 4)
        self.assertEqual(link.queue_free, 0,
                         "255 must not be mistaken for a free-slot count")

    def test_lines_split_across_reads_are_reassembled(self):
        link, ctl = make_link(chunk=3)
        for _ in range(50):
            link.send_joints([1.5, -70.25, 179.5, 0, 0, 0], 30)
            for _ in range(10):        # several frames' worth of small reads
                link.pump()
        self.assertEqual(link.acks, 50)
        self.assertEqual(len(ctl.tx), 0)

    def test_pump_is_bounded_when_no_newline_ever_arrives(self):
        link, ctl = make_link()
        ctl.tx += b"x" * 20000
        link.pump()
        self.assertLessEqual(len(link._rx), 4096)

    def test_unexpected_line_is_recorded_not_counted(self):
        link, ctl = make_link()
        ctl.tx += b"error SET MOTOR [9] DCE_KP [1] is wrong\r\n"
        link.pump()
        self.assertIn("error", link.last_error)
        self.assertEqual(link.acks, 0)
        self.assertEqual(link.drops, 0)

    def test_negative_number_is_not_read_as_a_slot_count(self):
        link, ctl = make_link()
        ctl.tx += b"-3\r\n"
        link.pump()
        self.assertIsNone(link.queue_free)


class TestWriteFailures(unittest.TestCase):

    def test_write_timeout_drops_one_frame_and_keeps_streaming(self):
        link, _ = make_link(fail_write=serial.SerialTimeoutException)
        self.assertFalse(link.send_joints([0] * 6, 30))
        self.assertEqual(link.write_timeouts, 1)
        self.assertFalse(link.link_lost, "a slow write is not a dead link")

    def test_port_error_marks_link_lost_and_stops_writing(self):
        link, _ = make_link(fail_write=serial.SerialException)
        self.assertFalse(link.send_joints([0] * 6, 30))
        self.assertTrue(link.link_lost)
        before = link.ser.writes
        link.send_joints([0] * 6, 30)
        self.assertEqual(link.ser.writes, before, "kept writing after loss")

    def test_pump_survives_port_disappearing(self):
        link, ctl = make_link()
        link.ser.fail_write = None

        def boom(size=1):
            raise OSError("device removed")
        link.ser.read = boom
        ctl.tx += b"ok\r\n"
        link.pump()                      # must not raise
        self.assertTrue(link.link_lost)

    def test_write_timeout_is_bounded_not_zero(self):
        """write_timeout=0 makes SerialTimeoutException unreachable on win32."""
        self.assertGreater(sc.WRITE_TIMEOUT, 0)


class TestQueries(unittest.TestCase):

    def test_read_response_restores_timeout(self):
        link, _ = make_link()
        link.ser.timeout = 0.02
        link._read_response()
        self.assertEqual(link.ser.timeout, 0.02)

    def test_read_response_restores_timeout_on_error(self):
        link, _ = make_link()
        link.ser.timeout = 0.02

        def boom():
            raise OSError("gone")
        link.ser.readline = boom
        link._read_response()
        self.assertEqual(link.ser.timeout, 0.02)

    def test_query_parses_joints(self):
        link, _ = make_link(controller=FakeController(
            joints=[1.0, -2.5, 3.25, -4.0, 5.5, -6.75]))
        self.assertEqual(link.query("#GETJPOS"),
                         [1.0, -2.5, 3.25, -4.0, 5.5, -6.75])

    def test_query_is_not_confused_by_pending_stream_replies(self):
        """A query after streaming must not read a stale 'ok' as the answer."""
        link, ctl = make_link()
        for _ in range(30):
            link.send_joints([0, -73, 180, 0, 0, 0], 30)   # backlog, unread
        self.assertEqual(link.query("#GETJPOS"),
                         [0.0, -73.0, 180.0, 0.0, 0.0, 0.0])

    def test_query_clears_the_line_buffer(self):
        link, ctl = make_link(chunk=2)
        link.send_joints([0] * 6, 30)
        link.pump()                       # likely leaves a partial line
        link.query("#GETJPOS")
        self.assertEqual(len(link._rx), 0)


class TestStartupOrder(unittest.TestCase):

    def test_open_does_not_enable(self):
        """Targets are seeded from the read pose before the arm is energised."""
        ctl = FakeController()
        link = sc.DummySerial("COMTEST")
        fake = FakeSerial(ctl)
        with mock.patch.object(sc.serial, "Serial", return_value=fake) as ctor:
            link.open()
        # The port must be opened with a bounded write timeout, not 0.
        self.assertEqual(ctor.call_args.kwargs["write_timeout"],
                         sc.WRITE_TIMEOUT)
        self.assertEqual(ctl.mode, 2)
        self.assertFalse(ctl.enabled)
        link.enable()
        self.assertTrue(ctl.enabled)

    def test_close_disables(self):
        link, ctl = make_link()
        ctl.enabled = True
        link.close()
        self.assertFalse(ctl.enabled)


# ---------------------------------------------------------------------------
# Keyboard layer
# ---------------------------------------------------------------------------

class TestKeyboardFallback(unittest.TestCase):
    """The no-console-queue path, which is testable without a real console."""

    def setUp(self):
        self._real = sc._GetAsyncKeyState
        self.down = set()
        self.latched = set()

        def fake(vk):
            state = 0
            if vk in self.down:
                state |= 0x8000
            if vk in self.latched:
                state |= 0x0001
                self.latched.discard(vk)      # the real latch self-clears
            return state
        sc._GetAsyncKeyState = fake

        self.kb = sc.KeyboardMonitor()
        self.kb.console_ok = False
        self.kb.focus_detectable = True
        self._focused = True
        self.kb.focused = lambda: self._focused

    def tearDown(self):
        sc._GetAsyncKeyState = self._real

    def test_held_keys_reported_when_focused(self):
        self.down = {sc.VK_W, sc.VK_Q}
        held, edges, focused = self.kb.poll()
        self.assertEqual(held, frozenset({sc.VK_W, sc.VK_Q}))
        self.assertTrue(focused)

    def test_background_keys_are_ignored(self):
        """Typing in another window must not jog the arm."""
        self._focused = False
        self.down = {sc.VK_W, sc.VK_A, sc.VK_S}
        held, edges, focused = self.kb.poll()
        self.assertEqual(held, frozenset())
        self.assertEqual(edges, frozenset())
        self.assertFalse(focused)

    def test_escape_in_background_does_not_quit(self):
        self._focused = False
        self.down = {sc.VK_ESC}
        held, edges, _ = self.kb.poll()
        self.assertNotIn(sc.VK_ESC, held)
        self.assertNotIn(sc.VK_ESC, edges)

    def test_short_tap_still_produces_an_edge(self):
        """Pressed and released inside one frame: 0x8000 is already gone."""
        self.latched = {sc.VK_TAB}
        held, edges, _ = self.kb.poll()
        self.assertIn(sc.VK_TAB, edges)
        self.assertNotIn(sc.VK_TAB, held)

    def test_background_latch_is_consumed_not_queued(self):
        """A tap while unfocused must not fire on the next focused frame."""
        self._focused = False
        self.latched = {sc.VK_TAB}
        self.kb.poll()
        self._focused = True
        held, edges, _ = self.kb.poll()
        self.assertNotIn(sc.VK_TAB, edges)


class TestKeyboardConsolePath(unittest.TestCase):
    """The console-event path, with the queue and key state both faked."""

    def setUp(self):
        self._real = sc._GetAsyncKeyState
        self.down = set()
        sc._GetAsyncKeyState = lambda vk: 0x8000 if vk in self.down else 0

        self.kb = sc.KeyboardMonitor()
        self.kb.console_ok = True
        self.kb.focus_detectable = True
        self._focused = True
        self.kb.focused = lambda: self._focused
        self.events = []
        self.kb._pump_events = self._drain_events

    def tearDown(self):
        sc._GetAsyncKeyState = self._real

    def _drain_events(self):
        for vk, is_down in self.events:
            if is_down:
                if vk not in self.kb._held:
                    self.kb._edges.add(vk)
                self.kb._held.add(vk)
            else:
                self.kb._held.discard(vk)
        self.events = []

    def test_press_yields_edge_once_then_held(self):
        self.events = [(sc.VK_TAB, True)]
        self.down = {sc.VK_TAB}
        held, edges, _ = self.kb.poll()
        self.assertIn(sc.VK_TAB, edges)
        self.assertIn(sc.VK_TAB, held)

        held, edges, _ = self.kb.poll()     # still down, no new event
        self.assertNotIn(sc.VK_TAB, edges, "auto-repeat must not re-fire")
        self.assertIn(sc.VK_TAB, held)

    def test_key_released_while_unfocused_does_not_stick(self):
        """The key-up goes to the other window; 0x8000 clears it here."""
        self.events = [(sc.VK_W, True)]
        self.down = {sc.VK_W}
        held, _, _ = self.kb.poll()
        self.assertIn(sc.VK_W, held)

        self.down = set()                   # physically released elsewhere
        held, _, _ = self.kb.poll()
        self.assertEqual(held, frozenset(), "stale key would jog forever")

    def test_background_key_cannot_revive_a_held_entry(self):
        self.events = [(sc.VK_W, True)]
        self.down = {sc.VK_W}
        self.kb.poll()

        self._focused = False
        held, edges, focused = self.kb.poll()
        self.assertEqual(held, frozenset())
        self.assertFalse(focused)

        self._focused = True                # no new key event delivered
        held, _, _ = self.kb.poll()
        self.assertEqual(held, frozenset(),
                         "focus loss must clear the held set")

    def test_ctrl_c_flag_is_exposed(self):
        self.assertFalse(self.kb.quit_requested)
        self.kb.quit_requested = True
        self.assertTrue(self.kb.quit_requested)


# ---------------------------------------------------------------------------
# Speed handling
# ---------------------------------------------------------------------------

class TestSpeed(unittest.TestCase):

    def test_floor_matches_the_send_side_clamp(self):
        """Below the clamp the target crawls while the arm runs at 5."""
        self.assertEqual(sc.MIN_SPEED, 5.0)

    def test_slow_key_cannot_go_under_the_floor(self):
        ctrl = sc.StreamingControl.__new__(sc.StreamingControl)
        ctrl.step = 10.0
        for _ in range(20):
            ctrl.step = max(sc.MIN_SPEED, ctrl.step * 0.7)
        self.assertEqual(ctrl.step, sc.MIN_SPEED)

    def test_cli_step_is_clamped_into_range(self):
        c = sc.StreamingControl("COMTEST", step_size=0.5)
        self.assertEqual(c.step, sc.MIN_SPEED)
        c = sc.StreamingControl("COMTEST", step_size=1e6)
        self.assertEqual(c.step, sc.MAX_SPEED)

    def test_every_watched_key_has_a_role(self):
        roles = (set(sc.JOINT_KEY_MAP) | set(sc.CART_KEY_MAP)
                 | set(sc._EDGE_KEYS) | {sc.VK_ESC})
        self.assertEqual(set(sc._ALL_KEYS), roles)


if __name__ == "__main__":
    unittest.main(verbosity=2, buffer=True)
