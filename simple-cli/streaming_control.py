#!/usr/bin/env python3
"""Dummy Streaming Control - 50 Hz keyboard jogging with dual mode.

Modes (TAB toggles):
  JOINT mode    — sends >j1..j6,speed   (current behavior)
  CARTESIAN mode — sends @x,y,z,a,b,c,speed  (firmware built-in IK)

Architecture:
  - Single-thread, no background drain (pyserial thread-safety)
  - Responses are consumed every frame; the firmware answers every '>' / '@'
    with the command-FIFO free-slot count plus an 'ok'. Leaving that unread
    fills the host CDC buffer, stalls the controller's USB TX path, and throws
    away the only backpressure signal the protocol offers.
  - Keyboard state is focus-scoped: a key only counts as held if it was pressed
    while this console had focus (console input events) AND is still physically
    down (GetAsyncKeyState). Typing in another window cannot drive the arm.
  - timeBeginPeriod(1) for 1ms timer precision
  - Bounded serial writes (write_timeout=0.01) so a wedged port surfaces as a
    dropped frame instead of an unbounded stall

Coordinate system (Cartesian):
  - XYZ in mm, ABC in degrees (ZYX Euler)
  - Origin = robot base geometric center (fixed by DH params)
  - Firmware FK computes pose from joints; IK computes joints from pose

Status line:
  q=<n>   command-FIFO free slots last reported by the firmware (0..15)
  d=<n>   commands the firmware refused because the FIFO was full (dropped)

Usage:
    python streaming_control.py                  # auto-detect port
    python streaming_control.py -p COM5          # specify port
    python streaming_control.py -l               # list serial ports
    python streaming_control.py -s 30            # default speed = 30 deg/s or mm/s
    python streaming_control.py --no-velocity    # step mode
"""

import argparse
import atexit
import ctypes
import sys
import time

import serial
import serial.tools.list_ports

# ---------------------------------------------------------------------------
# Windows timer: 15.6ms → 1ms
# ---------------------------------------------------------------------------

_WINMM = ctypes.windll.winmm
_WINMM.timeBeginPeriod(1)
atexit.register(lambda: _WINMM.timeEndPeriod(1))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BAUDRATE = 115200
SEND_RATE_HZ = 50
SEND_PERIOD = 1.0 / SEND_RATE_HZ

# The firmware clamps the speed field to 0..100 and this script uses the same
# number as the target integration rate, so anything below the send-side floor
# would make the target crawl while the arm runs ahead of it.
MIN_SPEED = 5.0
MAX_SPEED = 100.0
DEFAULT_SPEED = 30.0

# Bounded write: pyserial's win32 backend only enforces a write timeout when
# write_timeout > 0. With 0 it fires off an overlapped WriteFile and returns
# immediately, reusing one OVERLAPPED struct per port, and SerialTimeoutException
# can never be raised.
WRITE_TIMEOUT = 0.01

# DummyRobot::CommandHandler::Push returns 0xFF when osMessageQueuePut fails,
# i.e. the 16-slot FIFO was full and the command was discarded.
QUEUE_PUSH_FAILED = 0xFF

JOINT_LIMITS = [
    (-170.0, 170.0), (-73.0, 90.0), (35.0, 180.0),
    (-180.0, 180.0), (-120.0, 120.0), (-720.0, 720.0),
]

# Virtual key codes
VK_Q = 0x51; VK_A = 0x41; VK_W = 0x57; VK_S = 0x53
VK_E = 0x45; VK_D = 0x44; VK_R = 0x52; VK_F = 0x46
VK_T = 0x54; VK_G = 0x47; VK_Y = 0x59; VK_H = 0x48
VK_C = 0x43
VK_ESC = 0x1B; VK_SPACE = 0x20; VK_TAB = 0x09
VK_1 = 0x31; VK_2 = 0x32; VK_3 = 0x33; VK_4 = 0x34; VK_5 = 0x35
VK_6 = 0x36; VK_7 = 0x37; VK_8 = 0x38; VK_9 = 0x39; VK_0 = 0x30
VK_OEM_4 = 0xDB; VK_OEM_6 = 0xDD

# Joint mode key map
JOINT_KEY_MAP = {
    VK_Q: (0, +1), VK_A: (0, -1), VK_W: (1, +1), VK_S: (1, -1),
    VK_E: (2, +1), VK_D: (2, -1), VK_R: (3, +1), VK_F: (3, -1),
    VK_T: (4, +1), VK_G: (4, -1), VK_Y: (5, +1), VK_H: (5, -1),
}

# Cartesian mode key map: (axis, direction)
#   axis 0=X, 1=Y, 2=Z, 3=A(roll), 4=B(pitch), 5=C(yaw)
CART_KEY_MAP = {
    VK_Q: (0, +1), VK_E: (0, -1),   # X: Q forward, E back
    VK_A: (1, +1), VK_D: (1, -1),   # Y: A left, D right
    VK_W: (2, +1), VK_S: (2, -1),   # Z: W up, S down
    VK_R: (3, +1), VK_F: (3, -1),   # A(roll): R+, F-
    VK_T: (4, +1), VK_G: (4, -1),   # B(pitch): T+, G-
    VK_Y: (5, +1), VK_H: (5, -1),   # C(yaw): Y+, H-
}

# Speed presets: key → deg/s (joint) or mm/s (Cartesian)
SPEED_PRESETS = {
    VK_1: 5.0, VK_2: 10.0, VK_3: 20.0, VK_4: 35.0, VK_5: 50.0,
    VK_6: 65.0, VK_7: 80.0, VK_8: 100.0, VK_9: 100.0, VK_0: 100.0,
}

_JOINT_KEYS = frozenset(JOINT_KEY_MAP.keys())
_CART_KEYS = frozenset(CART_KEY_MAP.keys())
_SPEED_KEYS = frozenset(SPEED_PRESETS.keys())

# Keys that act on the press transition rather than while held
_EDGE_KEYS = frozenset({VK_TAB, VK_SPACE, VK_OEM_4, VK_OEM_6}) | _SPEED_KEYS

# All watched keys in both modes
_ALL_KEYS = frozenset(
    set(JOINT_KEY_MAP.keys()) | set(CART_KEY_MAP.keys()) | set(_EDGE_KEYS)
    | {VK_ESC}
)


# ---------------------------------------------------------------------------
# Win32 keyboard / console input
# ---------------------------------------------------------------------------

_k32 = ctypes.windll.kernel32
_u32 = ctypes.windll.user32

_GetAsyncKeyState = _u32.GetAsyncKeyState
_GetAsyncKeyState.restype = ctypes.c_short
_GetAsyncKeyState.argtypes = [ctypes.c_int]

_u32.GetForegroundWindow.restype = ctypes.c_void_p
_u32.GetForegroundWindow.argtypes = []
_u32.IsWindowVisible.restype = ctypes.c_int
_u32.IsWindowVisible.argtypes = [ctypes.c_void_p]

_k32.GetConsoleWindow.restype = ctypes.c_void_p
_k32.GetConsoleWindow.argtypes = []
_k32.GetStdHandle.restype = ctypes.c_void_p
_k32.GetStdHandle.argtypes = [ctypes.c_int]
_k32.GetConsoleMode.restype = ctypes.c_int
_k32.GetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
_k32.SetConsoleMode.restype = ctypes.c_int
_k32.SetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
_k32.GetNumberOfConsoleInputEvents.restype = ctypes.c_int
_k32.GetNumberOfConsoleInputEvents.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]

STD_INPUT_HANDLE = -10

ENABLE_PROCESSED_INPUT = 0x0001
ENABLE_LINE_INPUT = 0x0002
ENABLE_ECHO_INPUT = 0x0004
ENABLE_WINDOW_INPUT = 0x0008
ENABLE_MOUSE_INPUT = 0x0010
ENABLE_QUICK_EDIT_MODE = 0x0040
ENABLE_EXTENDED_FLAGS = 0x0080
ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200

KEY_EVENT = 0x0001
FOCUS_EVENT = 0x0010
LEFT_CTRL_PRESSED = 0x0008
RIGHT_CTRL_PRESSED = 0x0004


class _COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]


class _KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bKeyDown", ctypes.c_int),
        ("wRepeatCount", ctypes.c_ushort),
        ("wVirtualKeyCode", ctypes.c_ushort),
        ("wVirtualScanCode", ctypes.c_ushort),
        ("uChar", ctypes.c_wchar),
        ("dwControlKeyState", ctypes.c_ulong),
    ]


class _MOUSE_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("dwMousePosition", _COORD),
        ("dwButtonState", ctypes.c_ulong),
        ("dwControlKeyState", ctypes.c_ulong),
        ("dwEventFlags", ctypes.c_ulong),
    ]


class _WINDOW_BUFFER_SIZE_RECORD(ctypes.Structure):
    _fields_ = [("dwSize", _COORD)]


class _MENU_EVENT_RECORD(ctypes.Structure):
    _fields_ = [("dwCommandId", ctypes.c_uint)]


class _FOCUS_EVENT_RECORD(ctypes.Structure):
    _fields_ = [("bSetFocus", ctypes.c_int)]


class _INPUT_RECORD_EVENT(ctypes.Union):
    _fields_ = [
        ("KeyEvent", _KEY_EVENT_RECORD),
        ("MouseEvent", _MOUSE_EVENT_RECORD),
        ("WindowBufferSizeEvent", _WINDOW_BUFFER_SIZE_RECORD),
        ("MenuEvent", _MENU_EVENT_RECORD),
        ("FocusEvent", _FOCUS_EVENT_RECORD),
    ]


class _INPUT_RECORD(ctypes.Structure):
    _fields_ = [("EventType", ctypes.c_ushort),
                ("Event", _INPUT_RECORD_EVENT)]


_k32.ReadConsoleInputW.restype = ctypes.c_int
_k32.ReadConsoleInputW.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(_INPUT_RECORD),
    ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]

_READ_BATCH = 64


class KeyboardMonitor:
    """Focus-scoped keyboard state.

    GetAsyncKeyState alone reads the global keyboard, so typing in any other
    window drives the arm. The console input queue alone can strand a key in
    the held state, because a key released while we are in the background never
    delivers its key-up event here.

    So both are combined: a key is held only if a console key-down arrived for
    it (which can only happen while we have focus) and it is still physically
    down. Press transitions come from the event queue, so taps shorter than one
    frame are never missed.
    """

    def __init__(self):
        self._h_in = _k32.GetStdHandle(STD_INPUT_HANDLE)
        self._orig_mode = None
        self.console_ok = False
        self._hwnd = _k32.GetConsoleWindow()
        # Under ConPTY (Windows Terminal, VS Code) GetConsoleWindow returns a
        # hidden host window that never matches the foreground window, so the
        # hwnd comparison is only meaningful when it is actually visible.
        self.focus_detectable = bool(self._hwnd) and bool(
            _u32.IsWindowVisible(self._hwnd))
        self._held = set()
        self._edges = set()
        self.quit_requested = False

    # -- setup / teardown ---------------------------------------------------

    def enter(self):
        """Switch the console to raw key-event input. Returns True on success."""
        mode = ctypes.c_ulong(0)
        try:
            if not _k32.GetConsoleMode(self._h_in, ctypes.byref(mode)):
                return False
            self._orig_mode = mode.value
            new_mode = mode.value & ~(
                ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT | ENABLE_PROCESSED_INPUT
                | ENABLE_QUICK_EDIT_MODE | ENABLE_VIRTUAL_TERMINAL_INPUT
                | ENABLE_MOUSE_INPUT)
            # QuickEdit can only be cleared alongside ENABLE_EXTENDED_FLAGS.
            # Leaving it on lets a stray click select text and freeze output.
            new_mode |= ENABLE_EXTENDED_FLAGS | ENABLE_WINDOW_INPUT
            if not _k32.SetConsoleMode(self._h_in, new_mode):
                self._orig_mode = None
                return False
        except OSError:
            self._orig_mode = None
            return False
        self.console_ok = True
        return True

    def restore(self):
        if self._orig_mode is None:
            return
        try:
            _k32.SetConsoleMode(self._h_in, self._orig_mode)
        except OSError:
            pass
        self._orig_mode = None
        self.console_ok = False

    # -- polling ------------------------------------------------------------

    def focused(self):
        if not self.focus_detectable:
            # Cannot tell; the console-event gate already scopes input.
            return True
        return _u32.GetForegroundWindow() == self._hwnd

    def _physical(self):
        return frozenset(vk for vk in _ALL_KEYS
                         if _GetAsyncKeyState(vk) & 0x8000)

    def _pump_events(self):
        pending = ctypes.c_ulong(0)
        read = ctypes.c_ulong(0)
        buf = (_INPUT_RECORD * _READ_BATCH)()
        for _ in range(16):  # bounded, never spin on a flooded queue
            if not _k32.GetNumberOfConsoleInputEvents(
                    self._h_in, ctypes.byref(pending)):
                return
            if not pending.value:
                return
            count = min(pending.value, _READ_BATCH)
            if not _k32.ReadConsoleInputW(
                    self._h_in, buf, count, ctypes.byref(read)):
                return
            for i in range(read.value):
                rec = buf[i]
                if rec.EventType == FOCUS_EVENT:
                    if not rec.Event.FocusEvent.bSetFocus:
                        self._held.clear()
                    continue
                if rec.EventType != KEY_EVENT:
                    continue
                ke = rec.Event.KeyEvent
                vk = ke.wVirtualKeyCode
                if not ke.bKeyDown:
                    self._held.discard(vk)
                    continue
                if vk == VK_C and (ke.dwControlKeyState
                                   & (LEFT_CTRL_PRESSED | RIGHT_CTRL_PRESSED)):
                    # ENABLE_PROCESSED_INPUT is off, so Ctrl+C arrives as a key.
                    self.quit_requested = True
                    continue
                if vk not in _ALL_KEYS:
                    continue
                if vk not in self._held:
                    self._edges.add(vk)  # ignore auto-repeat
                self._held.add(vk)

    def poll(self):
        """Return (held, edges, focused)."""
        focused = self.focused()

        if self.console_ok:
            self._pump_events()
            # Drop anything no longer physically down. This clears keys whose
            # key-up went to another window and stops a stale entry from being
            # revived by a background key press.
            self._held &= self._physical()
            held = frozenset(self._held)
            edges = frozenset(self._edges)
            self._edges.clear()
            if not focused:
                held = frozenset()
                edges = frozenset()
                self._held.clear()
            return held, edges, focused

        # Fallback: no usable console queue (redirected stdin). Read the
        # "pressed since last call" latch so short taps still register, but
        # always consume it so nothing queues up while we are in the
        # background.
        edges = set()
        for vk in _EDGE_KEYS:
            pressed = _GetAsyncKeyState(vk) & 0x0001
            if pressed and focused:
                edges.add(vk)
        phys = self._physical()
        if not focused:
            return frozenset(), frozenset(), False
        return phys, frozenset(edges), True


# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------

SKIP_PORTS = {"COM3", "COM4"}


def _probe_port(dev):
    try:
        s = serial.Serial(dev, BAUDRATE, timeout=0.15, write_timeout=0.3)
    except Exception:
        return False
    try:
        s.timeout = 0.05
        while s.in_waiting:
            s.read(s.in_waiting)
        s.write(b"#GETJPOS\r\n")
        s.timeout = 0.2
        t0 = time.time()
        r = b""
        while time.time() - t0 < 0.6:
            b = s.read(1)
            if not b:
                if r:
                    break
                time.sleep(0.01)
                continue
            r += b
            if b"\n" in r:
                break
        return b"ok" in r
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def find_port():
    for dev in ["COM5", "COM6"]:
        if _probe_port(dev):
            return dev
    for p in serial.tools.list_ports.comports():
        if p.device in SKIP_PORTS:
            continue
        if "Bluetooth" in (p.description or ""):
            continue
        if p.device in ("COM5", "COM6"):
            continue
        if _probe_port(p.device):
            return p.device
    return None


def list_serial_ports():
    return [(p.device, p.description or "", p.hwid or "")
            for p in serial.tools.list_ports.comports()]


# ---------------------------------------------------------------------------
# DummySerial
# ---------------------------------------------------------------------------

class DummySerial:

    def __init__(self, port):
        self.port = port
        self.ser = None
        self._rx = bytearray()
        self.queue_free = None    # free FIFO slots last reported (0..15)
        self.drops = 0            # commands the firmware discarded
        self.acks = 0
        self.write_timeouts = 0
        self.link_lost = False
        self.last_error = ""

    # -- lifecycle ----------------------------------------------------------

    def open(self):
        """Open the port and select the non-blocking command mode.

        !START is deliberately not sent here; the caller enables the arm only
        after it has read the current pose and seeded its targets with it.
        """
        self.ser = serial.Serial(
            self.port, BAUDRATE, timeout=0.02, write_timeout=WRITE_TIMEOUT)
        self._writeline("#CMDMODE 2")
        time.sleep(0.08)
        print(f"  [CMD] CMDMODE 2  => {self._read_response()}")
        self._drain()
        return True

    def enable(self):
        self._writeline("!START")
        time.sleep(0.08)
        print(f"  [CMD] !START     => {self._read_response()}")
        self._drain()

    def close(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b"!DISABLE\r\n")
                time.sleep(0.05)
            except Exception:
                pass
            try:
                self.ser.close()
            except Exception:
                pass

    # -- low level ----------------------------------------------------------

    def _writeline(self, text):
        try:
            self.ser.write((text + "\r\n").encode())
        except serial.SerialException:
            pass

    def _drain(self):
        try:
            self.ser.timeout = 0.001
            while self.ser.in_waiting:
                self.ser.read(max(1, self.ser.in_waiting))
        except Exception:
            pass
        finally:
            del self._rx[:]

    def _read_response(self, timeout=0.2):
        lines = []
        prev_timeout = self.ser.timeout
        try:
            self.ser.timeout = 0.01
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < timeout:
                try:
                    b = self.ser.readline()
                except Exception:
                    break
                if b:
                    line = b.decode(errors="replace").strip()
                    if line:
                        lines.append(line)
                elif self.ser.in_waiting == 0:
                    break
        finally:
            self.ser.timeout = prev_timeout
        return lines[-1] if lines else ""

    # -- streaming ----------------------------------------------------------

    def _send(self, data):
        if self.link_lost:
            return False
        try:
            self.ser.write(data)
            return True
        except serial.SerialTimeoutException:
            # Port accepted nothing within WRITE_TIMEOUT: drop this frame, the
            # next one carries the same absolute target anyway.
            self.write_timeouts += 1
            return False
        except (serial.SerialException, OSError) as exc:
            self.link_lost = True
            self.last_error = str(exc)
            return False

    def send_joints(self, joints, speed_pct):
        """Send >j1..j6,speed  (joint mode)"""
        return self._send(
            f">{joints[0]:.2f},{joints[1]:.2f},{joints[2]:.2f},"
            f"{joints[3]:.2f},{joints[4]:.2f},{joints[5]:.2f},"
            f"{speed_pct:.0f}\r\n".encode())

    def send_pose(self, pose, speed_pct):
        """Send @x,y,z,a,b,c,speed  (Cartesian mode)"""
        return self._send(
            f"@{pose[0]:.2f},{pose[1]:.2f},{pose[2]:.2f},"
            f"{pose[3]:.2f},{pose[4]:.2f},{pose[5]:.2f},"
            f"{speed_pct:.0f}\r\n".encode())

    def pump(self):
        """Consume pending responses. Non-blocking; call once per frame.

        Every '>' / '@' draws two replies: the FIFO free-slot count from the
        ASCII handler and an 'ok' from the command thread. Unread, they fill the
        host CDC buffer within seconds, which wedges the controller's USB TX
        endpoint and leaves any later query reading thousands of stale lines.
        """
        if self.link_lost:
            return
        try:
            pending = self.ser.in_waiting
            if pending:
                self._rx += self.ser.read(pending)
        except (serial.SerialException, OSError) as exc:
            self.link_lost = True
            self.last_error = str(exc)
            return

        if len(self._rx) > 4096:      # unterminated garbage; keep the tail
            del self._rx[:-1024]

        while True:
            idx = self._rx.find(b"\n")
            if idx < 0:
                break
            line = bytes(self._rx[:idx]).strip()
            del self._rx[:idx + 1]
            if line:
                self._on_line(line.decode("ascii", "replace"))

    def _on_line(self, line):
        if line.startswith("ok"):
            self.acks += 1
            return
        if line.isdigit():
            value = int(line)
            if value == QUEUE_PUSH_FAILED:
                self.drops += 1
            else:
                self.queue_free = value
            return
        self.last_error = line

    def query(self, cmd):
        """Send a query (#GETJPOS / #GETLPOS) and parse float response."""
        self._drain()
        self._writeline(cmd)
        resp = self._read_response(0.3)
        if resp:
            resp = resp.replace("ok", "", 1).strip()
            result = []
            for token in resp.split():
                cleaned = "".join(
                    ch for ch in token if ch.isdigit() or ch in ".-+")
                if not cleaned or cleaned in (".", "-", "+"):
                    continue
                try:
                    result.append(float(cleaned))
                except ValueError:
                    pass
            if len(result) >= 6:
                return result[:6]
        return None


# ---------------------------------------------------------------------------
# Streaming loop
# ---------------------------------------------------------------------------

class StreamingControl:

    def __init__(self, port, step_size=DEFAULT_SPEED, velocity_mode=True):
        self.serial = DummySerial(port)
        self.step = min(MAX_SPEED, max(MIN_SPEED, step_size))
        self.velocity_mode = velocity_mode
        self.running = False
        self.keyboard = KeyboardMonitor()
        self._stopped = False
        self._line_width = 0

        # Two independent targets (each mode tracks its own)
        self.joint_target = [0.0] * 6   # degrees
        self.pose_target = [0.0] * 6    # mm / degrees

    def start(self):
        print(f"Connecting to {self.serial.port} ...")
        self.serial.open()

        # Read state before enabling. While the arm is disabled the control
        # thread broadcasts a CAN angle query every tick, so currentJoints is
        # live; seeding the targets first means the very first streamed frame
        # asks for where the arm already is.
        print("Reading current state ...")
        j = self.serial.query("#GETJPOS")
        p = self.serial.query("#GETLPOS")

        if j:
            self.joint_target = j
            print("  Joints: " + "  ".join(
                f"J{i+1}={v:+.1f}" for i, v in enumerate(j)))
        else:
            print("  [WARN] Could not read joints; using rest pose")
            self.joint_target = [0.0, -73.0, 180.0, 0.0, 0.0, 0.0]

        if p:
            self.pose_target = p
            print("  Pose:   " + "  ".join(
                f"{'XYZA'[i] if i < 4 else 'BC'[i-4]}={v:+.1f}"
                for i, v in enumerate(p)))
        else:
            print("  [WARN] Could not read pose")

        self.serial.enable()

        if self.keyboard.enter():
            src = ("console events + key state, focus-scoped"
                   if self.keyboard.focus_detectable
                   else "console events + key state")
        else:
            src = "key state only (no console queue)"
            if not self.keyboard.focus_detectable:
                print("  [WARN] Cannot scope input to this window; keys will be "
                      "read globally.")
        atexit.register(self.keyboard.restore)

        mode_label = "VELOCITY" if self.velocity_mode else "STEP"
        print(f"\n  Speed={self.step:.0f}  |  {mode_label}  |  TAB=switch mode")
        print(f"  Input: {src}")
        print("-" * 68)
        self._print_help(joint_mode=True)
        print("-" * 68 + "\n")

        self.running = True
        self._main_loop()

    def _print_help(self, joint_mode):
        if joint_mode:
            print("  [JOINT] Q/A=J1  W/S=J2  E/D=J3  "
                  "R/F=J4  T/G=J5  Y/H=J6")
        else:
            print("  [CART]  Q/E=X   A/D=Y   W/S=Z   "
                  "R/F=A   T/G=B   Y/H=C")
        print("  1..0=speed  [/]=slow/fast  SPACE=freeze  TAB=mode  ESC=quit")

    def _write_status(self, text):
        pad = max(0, self._line_width - len(text))
        self._line_width = len(text)
        sys.stdout.write("\r" + text + " " * pad)
        sys.stdout.flush()

    def _notify(self, text):
        pad = max(0, self._line_width - len(text))
        self._line_width = 0
        sys.stdout.write("\r" + text + " " * pad + "\n")
        sys.stdout.flush()

    def _main_loop(self):
        frame_count = 0
        fps_timer = time.perf_counter()
        frozen = False
        cartesian = False  # False = joint mode, True = Cartesian mode
        deadline = time.perf_counter() + SEND_PERIOD

        while self.running:
            keys, edges, focused = self.keyboard.poll()

            # ---- quit ----
            if VK_ESC in keys or VK_ESC in edges \
                    or self.keyboard.quit_requested:
                self.running = False
                break

            # ---- TAB: toggle mode ----
            if VK_TAB in edges:
                cartesian = not cartesian
                self._notify(
                    f">>> MODE: {'CARTESIAN' if cartesian else 'JOINT'}")
                self._print_help(joint_mode=not cartesian)

            # ---- SPACE: toggle freeze ----
            if VK_SPACE in edges:
                frozen = not frozen
                self._notify(f">>> {'FROZEN' if frozen else 'UNFROZEN'}")

            # ---- Speed presets ----
            for vk in edges:
                if vk in _SPEED_KEYS:
                    self.step = SPEED_PRESETS[vk]
                elif vk == VK_OEM_4:
                    self.step = max(MIN_SPEED, self.step * 0.7)
                elif vk == VK_OEM_6:
                    self.step = min(MAX_SPEED, self.step * 1.5)

            # ---- Movement (all held keys apply simultaneously) ----
            # Velocity mode integrates while held; step mode advances once per
            # press, which is what the edge set carries. Unioning the edges into
            # velocity mode gives a tap shorter than one frame exactly one
            # frame of travel instead of dropping it.
            active = (keys | edges) if self.velocity_mode else edges
            if not frozen:
                dt = SEND_PERIOD  # 0.02s
                if cartesian:
                    for vk in (active & _CART_KEYS):
                        axis, direction = CART_KEY_MAP[vk]
                        self.pose_target[axis] += self.step * direction * dt
                else:
                    for vk in (active & _JOINT_KEYS):
                        axis, direction = JOINT_KEY_MAP[vk]
                        delta = self.step * direction * dt
                        lo, hi = JOINT_LIMITS[axis]
                        new_val = self.joint_target[axis] + delta
                        if new_val < lo:
                            new_val = lo
                        elif new_val > hi:
                            new_val = hi
                        self.joint_target[axis] = new_val

            # ---- Read the controller's replies before sending the next frame
            self.serial.pump()
            if self.serial.link_lost:
                self._notify(f">>> LINK LOST: {self.serial.last_error}")
                self.running = False
                break

            # ---- Send ----
            spd = int(self.step)
            if spd < 5:
                spd = 5
            elif spd > 100:
                spd = 100

            if cartesian:
                self.serial.send_pose(self.pose_target, spd)
            else:
                self.serial.send_joints(self.joint_target, spd)

            if self.serial.link_lost:
                self._notify(f">>> LINK LOST: {self.serial.last_error}")
                self.running = False
                break

            # ---- Display (10 Hz) ----
            frame_count += 1
            if frame_count % 5 == 0:
                fps = frame_count / (time.perf_counter() - fps_timer + 1e-9)
                mode_str = "[CART]" if cartesian else "[JOINT]"
                if not focused:
                    status = "NOFOCUS"
                elif frozen:
                    status = "FROZEN"
                else:
                    status = "LIVE"
                target = self.pose_target if cartesian else self.joint_target
                labels = ["X", "Y", "Z", "A", "B", "C"] if cartesian \
                    else ["J1", "J2", "J3", "J4", "J5", "J6"]

                parts = [f"{mode_str} {status}"]
                for i in range(6):
                    parts.append(f"{labels[i]}={target[i]:+7.1f}")
                line = "  ".join(parts)
                line += f"  | {self.step:.0f}/s"
                q = self.serial.queue_free
                line += f" q={'-' if q is None else q}"
                if self.serial.drops:
                    line += f" d={self.serial.drops}"
                if self.serial.write_timeouts:
                    line += f" w={self.serial.write_timeouts}"
                line += f" fps={fps:.0f}"
                self._write_status(line)

            # ---- Precise frame timing ----
            now = time.perf_counter()
            remaining = deadline - now
            if remaining > 0.002:
                time.sleep(remaining - 0.0015)
            while time.perf_counter() < deadline:
                pass
            deadline += SEND_PERIOD
            if time.perf_counter() > deadline + SEND_PERIOD:
                deadline = time.perf_counter() + SEND_PERIOD

    def stop(self):
        if self._stopped:
            return
        self._stopped = True
        self.running = False
        self.keyboard.restore()
        print("\n\nDisabling motors ...")
        self.serial.close()
        if self.serial.drops or self.serial.write_timeouts:
            print(f"Link stats: dropped={self.serial.drops}  "
                  f"write timeouts={self.serial.write_timeouts}")
        print("Done.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Dummy Streaming Control - 50 Hz dual-mode jogging"
    )
    parser.add_argument("-p", "--port", help="Serial port, e.g. COM5")
    parser.add_argument("-l", "--list", action="store_true",
                        help="List serial ports and exit")
    parser.add_argument("--no-velocity", action="store_true",
                        help="Step mode: each tap = one increment")
    parser.add_argument("-s", "--step", type=float, default=DEFAULT_SPEED,
                        help=f"Speed in deg/s or mm/s "
                             f"({MIN_SPEED:.0f}-{MAX_SPEED:.0f}, "
                             f"default: {DEFAULT_SPEED:.0f})")
    args = parser.parse_args()

    if args.list:
        ports = list_serial_ports()
        if not ports:
            print("No serial ports found.")
        else:
            print("Available serial ports:")
            for dev, desc, hwid in ports:
                print(f"  {dev}  -  {desc}  [{hwid}]")
        return

    port = args.port or find_port()
    if not port:
        print("ERROR: No Dummy controller found.")
        return

    ctrl = StreamingControl(port, step_size=args.step,
                            velocity_mode=not args.no_velocity)
    atexit.register(ctrl.stop)

    try:
        ctrl.start()
    except KeyboardInterrupt:
        pass
    finally:
        ctrl.stop()


if __name__ == "__main__":
    main()
