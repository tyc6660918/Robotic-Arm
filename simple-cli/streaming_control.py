#!/usr/bin/env python3
"""Dummy Streaming Control - 50 Hz keyboard jogging with dual mode.

Modes (TAB toggles):
  JOINT mode    — sends >j1..j6,speed   (current behavior)
  CARTESIAN mode — sends @x,y,z,a,b,c,speed  (firmware built-in IK)

Architecture:
  - Single-thread, no background drain (pyserial thread-safety)
  - GetAsyncKeyState for simultaneous multi-key
  - timeBeginPeriod(1) for 1ms timer precision
  - Non-blocking serial writes (write_timeout=0)

Coordinate system (Cartesian):
  - XYZ in mm, ABC in degrees (ZYX Euler)
  - Origin = robot base geometric center (fixed by DH params)
  - Firmware FK computes pose from joints; IK computes joints from pose

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
MIN_SPEED = 1.0
MAX_SPEED = 100.0
DEFAULT_SPEED = 30.0

JOINT_LIMITS = [
    (-170.0, 170.0), (-73.0, 90.0), (35.0, 180.0),
    (-180.0, 180.0), (-120.0, 120.0), (-720.0, 720.0),
]

# Virtual key codes
VK_Q = 0x51; VK_A = 0x41; VK_W = 0x57; VK_S = 0x53
VK_E = 0x45; VK_D = 0x44; VK_R = 0x52; VK_F = 0x46
VK_T = 0x54; VK_G = 0x47; VK_Y = 0x59; VK_H = 0x48
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

# All watched keys in both modes
_ALL_KEYS = (
    set(JOINT_KEY_MAP.keys()) | set(CART_KEY_MAP.keys())
    | set(SPEED_PRESETS.keys())
    | {VK_ESC, VK_SPACE, VK_TAB, VK_OEM_4, VK_OEM_6}
)
_JOINT_KEYS = frozenset(JOINT_KEY_MAP.keys())
_CART_KEYS = frozenset(CART_KEY_MAP.keys())
_SPEED_KEYS = frozenset(SPEED_PRESETS.keys())


# ---------------------------------------------------------------------------
# Keyboard (GetAsyncKeyState)
# ---------------------------------------------------------------------------

_GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState
_GetAsyncKeyState.restype = ctypes.c_short
_GetAsyncKeyState.argtypes = [ctypes.c_int]


def poll_keys():
    return frozenset(vk for vk in _ALL_KEYS
                     if (_GetAsyncKeyState(vk) & 0x8000))


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

    def connect(self):
        self.ser = serial.Serial(
            self.port, BAUDRATE, timeout=0.02, write_timeout=0)

        for cmd, label in [("#CMDMODE 2", "CMDMODE 2"),
                           ("!START", "!START")]:
            self._writeline(cmd)
            time.sleep(0.08)
            resp = self._read_response()
            print(f"  [CMD] {label}  => {resp}")

        self._drain()
        return True

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

    def _read_response(self, timeout=0.2):
        lines = []
        t0 = time.perf_counter()
        self.ser.timeout = 0.01
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
        return lines[-1] if lines else ""

    def send_joints(self, joints, speed_pct):
        """Send >j1..j6,speed  (joint mode)"""
        data = (f">{joints[0]:.2f},{joints[1]:.2f},{joints[2]:.2f},"
                f"{joints[3]:.2f},{joints[4]:.2f},{joints[5]:.2f},"
                f"{speed_pct:.0f}\r\n").encode()
        try:
            self.ser.write(data)
        except serial.SerialTimeoutException:
            pass
        except serial.SerialException:
            pass

    def send_pose(self, pose, speed_pct):
        """Send @x,y,z,a,b,c,speed  (Cartesian mode)"""
        data = (f"@{pose[0]:.2f},{pose[1]:.2f},{pose[2]:.2f},"
                f"{pose[3]:.2f},{pose[4]:.2f},{pose[5]:.2f},"
                f"{speed_pct:.0f}\r\n").encode()
        try:
            self.ser.write(data)
        except serial.SerialTimeoutException:
            pass
        except serial.SerialException:
            pass

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


# ---------------------------------------------------------------------------
# Streaming loop
# ---------------------------------------------------------------------------

class StreamingControl:

    def __init__(self, port, step_size=DEFAULT_SPEED, velocity_mode=True):
        self.serial = DummySerial(port)
        self.step = step_size
        self.velocity_mode = velocity_mode
        self.running = False
        self._prev_keys = frozenset()

        # Two independent targets (each mode tracks its own)
        self.joint_target = [0.0] * 6   # degrees
        self.pose_target = [0.0] * 6    # mm / degrees

    def start(self):
        print(f"Connecting to {self.serial.port} ...")
        self.serial.connect()
        time.sleep(0.5)

        # Read initial state for BOTH modes
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

        mode_label = "VELOCITY" if self.velocity_mode else "STEP"
        print(f"\n  Speed={self.step:.0f}  |  {mode_label}  |  TAB=switch mode")
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

    def _main_loop(self):
        frame_count = 0
        fps_timer = time.perf_counter()
        frozen = False
        cartesian = False  # False = joint mode, True = Cartesian mode
        deadline = time.perf_counter() + SEND_PERIOD

        while self.running:
            keys = poll_keys()

            # ---- ESC always ----
            if VK_ESC in keys:
                self.running = False
                break

            # ---- TAB: toggle mode ----
            if VK_TAB in keys and VK_TAB not in self._prev_keys:
                cartesian = not cartesian
                sys.stdout.write(f"\r>>> MODE: {'CARTESIAN' if cartesian else 'JOINT'}\n")
                self._print_help(joint_mode=not cartesian)
                sys.stdout.flush()

            # ---- SPACE: toggle freeze ----
            if VK_SPACE in keys and VK_SPACE not in self._prev_keys:
                frozen = not frozen
                sys.stdout.write(f"\r>>> {'FROZEN' if frozen else 'UNFROZEN'}\n")
                sys.stdout.flush()

            # ---- Speed presets (edge) ----
            for vk in (keys - self._prev_keys):
                if vk in _SPEED_KEYS:
                    self.step = SPEED_PRESETS[vk]
                elif vk == VK_OEM_4:
                    self.step = max(MIN_SPEED, self.step * 0.7)
                elif vk == VK_OEM_6:
                    self.step = min(MAX_SPEED, self.step * 1.5)

            # ---- Movement (all held keys apply simultaneously) ----
            if not frozen:
                dt = SEND_PERIOD  # 0.02s
                if cartesian:
                    for vk in (keys & _CART_KEYS):
                        axis, direction = CART_KEY_MAP[vk]
                        if not self.velocity_mode and vk in self._prev_keys:
                            continue
                        delta = self.step * direction * dt
                        self.pose_target[axis] += delta
                else:
                    for vk in (keys & _JOINT_KEYS):
                        axis, direction = JOINT_KEY_MAP[vk]
                        if not self.velocity_mode and vk in self._prev_keys:
                            continue
                        delta = self.step * direction * dt
                        lo, hi = JOINT_LIMITS[axis]
                        new_val = self.joint_target[axis] + delta
                        if new_val < lo:
                            new_val = lo
                        elif new_val > hi:
                            new_val = hi
                        self.joint_target[axis] = new_val

            self._prev_keys = keys

            # ---- Send ----
            spd = int(self.step)
            if spd < 5: spd = 5
            elif spd > 100: spd = 100

            if cartesian:
                self.serial.send_pose(self.pose_target, spd)
            else:
                self.serial.send_joints(self.joint_target, spd)

            # ---- Display (10 Hz) ----
            frame_count += 1
            if frame_count % 5 == 0:
                fps = frame_count / (time.perf_counter() - fps_timer + 1e-9)
                mode_str = "[CART]" if cartesian else "[JOINT]"
                status = "FROZEN" if frozen else "LIVE"
                target = self.pose_target if cartesian else self.joint_target
                labels = ["X", "Y", "Z", "A", "B", "C"] if cartesian \
                    else ["J1", "J2", "J3", "J4", "J5", "J6"]

                parts = [f"{mode_str} {status}"]
                for i in range(6):
                    parts.append(f"{labels[i]}={target[i]:+7.1f}")
                line = "  ".join(parts)
                line += f"  | {self.step:.0f}/s  fps={fps:.0f}"
                sys.stdout.write(f"\r{line}")
                sys.stdout.flush()

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
        self.running = False
        print("\n\nDisabling motors ...")
        self.serial.close()
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
                             f"(1-100, default: {DEFAULT_SPEED:.0f})")
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
