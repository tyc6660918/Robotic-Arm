#!/usr/bin/env python3
"""Dummy Robot 3D Viewer - matplotlib skeleton + thick links.

Draws the kinematic chain as thick colored tubes connecting joint
positions, plus spheres at each joint and the end-effector.

Run:
    python robot_viewer.py --no-connect    # offline demo
    python robot_viewer.py                 # live mode
"""

import argparse
import atexit
import math
import sys
import threading
import time

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection
import numpy as np

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    sys.exit("pip install pyserial")

from fk_solver import JOINT_DEFS

BAUDRATE = 115200
QUERY_HZ = 15
QUERY_PERIOD = 1.0 / QUERY_HZ
REST_ANGLES = [0.0, -73.0, 180.0, 0.0, 0.0, 0.0]
SKIP_PORTS = {"COM3", "COM4"}

LINK_COLORS = ["#CC4444", "#44CC44", "#4444CC", "#CCCC44", "#CC44CC", "#44CCCC"]
LINK_RADII = [0.018, 0.015, 0.012, 0.010, 0.008, 0.006]


def rot_mat_4x4(axis, angle_deg):
    a = math.radians(angle_deg)
    x, y, z = axis
    c = math.cos(a); s = math.sin(a); t = 1 - c
    return np.array([
        [t*x*x+c,   t*x*y-s*z, t*x*z+s*y, 0],
        [t*x*y+s*z, t*y*y+c,   t*y*z-s*x, 0],
        [t*x*z-s*y, t*y*z+s*x, t*z*z+c,   0],
        [0, 0, 0, 1],
    ])


def trans_mat_4x4(tx, ty, tz):
    return np.array([[1,0,0,tx],[0,1,0,ty],[0,0,1,tz],[0,0,0,1]])


def compute_joint_positions(angles_deg):
    """Return list of 7 world-space (x,y,z) tuples: base + 6 joints."""
    positions = [(0.0, 0.0, 0.0)]
    current = np.eye(4)
    for i, (name, pidx, ox, oy, oz, ax, ay, az, vx, vy, vz) in enumerate(JOINT_DEFS):
        t = trans_mat_4x4(ox, oy, oz)
        r = rot_mat_4x4((ax, ay, az), angles_deg[i])
        current = current @ t @ r
        positions.append((current[0, 3], current[1, 3], current[2, 3]))
    return positions


def make_tube_segments(p1, p2, radius, n_sides=8):
    """Return a list of quad faces forming a thick tube from p1 to p2."""
    p1, p2 = np.array(p1), np.array(p2)
    axis = p2 - p1
    length = np.linalg.norm(axis)
    if length < 1e-9:
        return []
    axis = axis / length
    # Find two perpendicular vectors
    if abs(axis[0]) < 0.9:
        perp = np.cross(axis, [1, 0, 0])
    else:
        perp = np.cross(axis, [0, 1, 0])
    perp = perp / np.linalg.norm(perp)
    perp2 = np.cross(axis, perp)

    angles = np.linspace(0, 2*np.pi, n_sides, endpoint=False)
    faces = []
    for j in range(n_sides):
        a0, a1 = angles[j], angles[(j+1) % n_sides]
        u0 = perp*np.cos(a0) + perp2*np.sin(a0)
        u1 = perp*np.cos(a1) + perp2*np.sin(a1)
        faces.append([
            p1 + u0*radius, p1 + u1*radius,
            p2 + u1*radius, p2 + u0*radius,
        ])
    return faces


def _probe_port(dev):
    try:
        s = serial.Serial(dev, BAUDRATE, timeout=0.15, write_timeout=0.3)
    except Exception:
        return False
    try:
        s.timeout = 0.05
        while s.in_waiting: s.read(s.in_waiting)
        s.write(b"#GETJPOS\r\n")
        s.timeout = 0.2; t0 = time.time(); r = b""
        while time.time() - t0 < 0.6:
            b = s.read(1)
            if not b:
                if r: break
                time.sleep(0.01); continue
            r += b
            if b"\n" in r: break
        return b"ok" in r
    except Exception:
        return False
    finally:
        try: s.close()
        except: pass


def find_port():
    for dev in ["COM5", "COM6"]:
        if _probe_port(dev): return dev
    for p in serial.tools.list_ports.comports():
        if p.device in SKIP_PORTS: continue
        if "Bluetooth" in (p.description or ""): continue
        if _probe_port(p.device): return p.device
    return None


class SerialReader:
    def __init__(self, port):
        self.port = port; self.ser = None
        self.joint_angles = list(REST_ANGLES)
        self.running = False
        self._lock = threading.Lock(); self._thread = None

    def connect(self):
        self.ser = serial.Serial(self.port, BAUDRATE, timeout=0.05, write_timeout=0.1)
        for cmd in ["#CMDMODE 2", "!START"]:
            self.ser.write((cmd + "\r\n").encode())
            time.sleep(0.08); self._drain()
        return True

    def _drain(self):
        try:
            self.ser.timeout = 0.001
            while self.ser.in_waiting: self.ser.read(max(1, self.ser.in_waiting))
        except: pass

    def _query(self, cmd, timeout=0.2):
        self._drain(); self.ser.write((cmd + "\r\n").encode()); self.ser.timeout = 0.05
        result = b""; t0 = time.perf_counter()
        while time.perf_counter() - t0 < timeout:
            try: b = self.ser.read(1)
            except: break
            if b: result += b
            if b == b"\n" or (not b and result): break
        return result.decode(errors="replace").strip()

    def _parse(self, text):
        text = text.replace("ok", "", 1).strip(); vals = []
        for token in text.split():
            c = "".join(ch for ch in token if ch.isdigit() or ch in ".-+")
            if not c or c in (".", "-", "+"): continue
            try: vals.append(float(c))
            except: pass
        return vals

    def _run(self):
        while self.running:
            t0 = time.perf_counter()
            try:
                resp = self._query("#GETJPOS"); angles = self._parse(resp)
                if len(angles) >= 6:
                    with self._lock: self.joint_angles = angles[:6]
            except: time.sleep(0.01)
            elapsed = time.perf_counter() - t0
            sleep_t = QUERY_PERIOD - elapsed
            if sleep_t > 0: time.sleep(sleep_t)

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self.ser:
            try: self.ser.close()
            except: pass

    def get_angles(self):
        with self._lock: return list(self.joint_angles)


class RobotViewer:
    def __init__(self, reader=None):
        self.reader = reader
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.ax.set_facecolor("#1a1a22")
        self.fig.patch.set_facecolor("#1a1a22")
        self.ax.set_xlim(-0.2, 0.3)
        self.ax.set_ylim(-0.4, 0.15)
        self.ax.set_zlim(-0.15, 0.35)
        self.ax.set_xlabel("X (m)", color="white")
        self.ax.set_ylabel("Y (m)", color="white")
        self.ax.set_zlabel("Z (m)", color="white")
        self.ax.tick_params(colors="white")
        self.ax.set_title("Dummy Robot Viewer", color="white")

        self._tube_cols = []   # Poly3DCollection per link
        self._joint_dots = None
        self._ee_dot = None
        self._base_dot = None
        self._build_scene()

    def _build_scene(self):
        angles = REST_ANGLES
        if self.reader: angles = self.reader.get_angles()
        pts = compute_joint_positions(angles)

        # Tubes for each link
        for i in range(6):
            faces = make_tube_segments(pts[i], pts[i+1], LINK_RADII[i])
            if faces:
                pc = Poly3DCollection(faces, alpha=0.9, linewidths=0,
                                      edgecolors="none")
                pc.set_facecolor(LINK_COLORS[i])
                self.ax.add_collection3d(pc)
                self._tube_cols.append(pc)
            else:
                self._tube_cols.append(None)

        # Joint dots
        jp = np.array(pts[1:])  # skip base, show 6 joints
        self._joint_dots = self.ax.scatter(
            jp[:, 0], jp[:, 1], jp[:, 2],
            c="yellow", s=40, marker="o", edgecolors="black", linewidths=0.5)

        # Base dot
        self._base_dot = self.ax.scatter(
            [0], [0], [0], c="white", s=60, marker="s")

        # End effector
        ee = pts[6]
        self._ee_dot = self.ax.scatter(
            [ee[0]], [ee[1]], [ee[2]], c="red", s=100, marker="o",
            edgecolors="white", linewidths=1)

        # Ground grid
        xx, yy = np.meshgrid(np.linspace(-0.2, 0.3, 8),
                             np.linspace(-0.4, 0.15, 8))
        self.ax.plot_surface(xx, yy, np.zeros_like(xx),
                             alpha=0.15, color="#444444")

    def update(self, frame):
        angles = REST_ANGLES
        if self.reader: angles = self.reader.get_angles()
        pts = compute_joint_positions(angles)

        # Update tubes
        for i in range(6):
            if self._tube_cols[i] is not None:
                faces = make_tube_segments(pts[i], pts[i+1], LINK_RADII[i])
                self._tube_cols[i].set_verts(faces)

        # Update joint dots
        jp = np.array(pts[1:])
        self._joint_dots._offsets3d = (jp[:, 0], jp[:, 1], jp[:, 2])

        # Update EE
        ee = pts[6]
        self._ee_dot._offsets3d = ([ee[0]], [ee[1]], [ee[2]])

        text = "  ".join(f"J{i+1}={a:+6.1f}" for i, a in enumerate(angles))
        text += f"  |  EE=({ee[0]:.3f},{ee[1]:.3f},{ee[2]:.3f})"
        self.ax.set_title(text, color="white", fontfamily="monospace",
                          fontsize=9)
        return (self._tube_cols + [self._joint_dots, self._ee_dot,
                                   self._base_dot])

    def show(self):
        self.ani = animation.FuncAnimation(
            self.fig, self.update, interval=1000 // QUERY_HZ,
            blit=False, cache_frame_data=False)
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Dummy Robot 3D Viewer")
    parser.add_argument("-p", "--port", help="Serial port, e.g. COM5")
    parser.add_argument("--no-connect", action="store_true",
                        help="Offline demo (rest pose)")
    args = parser.parse_args()

    reader = None
    if not args.no_connect:
        port = args.port or find_port()
        if not port:
            print("ERROR: No Dummy controller found."); return
        print(f"Connecting to {port} ...")
        reader = SerialReader(port); reader.connect(); reader.start()
        print("Reader started.")
    else:
        print("Offline demo - rest pose")

    viewer = RobotViewer(reader=reader)
    atexit.register(lambda: reader.stop() if reader else None)
    viewer.show()


if __name__ == "__main__":
    main()