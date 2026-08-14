"""Dummy CLI v4 - fully aligned with dummy_cli.py protocol + debug mode"""

import serial
import serial.tools.list_ports
import time
import sys
import cmd
import argparse

DEBUG = False
ser = None
SERIAL_PORT = ""
SKIP_PORTS = {"COM3", "COM4"}

def list_ports():
    return [(p.device, p.description, p.hwid) for p in serial.tools.list_ports.comports()]

def find_port():
    for dev in ["COM5", "COM6"]:
        try:
            s = serial.Serial(dev, 115200, timeout=0.3, write_timeout=0.5)
            s.timeout = 0.1
            try:
                while s.in_waiting: s.read(s.in_waiting)
                s.read(512)
            except: pass
            s.timeout = 0.3
            s.reset_input_buffer()
            s.write(b"#GETJPOS\r\n")
            t0 = time.time(); r = b""
            while time.time() - t0 < 0.8:
                if s.in_waiting: r += s.read(s.in_waiting)
                if b"\n" in r: break
                time.sleep(0.02)
            s.close()
            if b"ok" in r:
                return dev
        except: pass
    for p in serial.tools.list_ports.comports():
        if p.device in SKIP_PORTS: continue
        if "Bluetooth" in (p.description or ""): continue
        if p.device in ("COM5", "COM6"): continue
        try:
            s = serial.Serial(p.device, 115200, timeout=0.3, write_timeout=0.5)
            s.timeout = 0.1
            try:
                while s.in_waiting: s.read(s.in_waiting)
                s.read(512)
            except: pass
            s.timeout = 0.3
            s.reset_input_buffer()
            s.write(b"#GETJPOS\r\n")
            t0 = time.time(); r = b""
            while time.time() - t0 < 0.6:
                if s.in_waiting: r += s.read(s.in_waiting)
                if b"\n" in r: break
                time.sleep(0.02)
            s.close()
            if b"ok" in r:
                return p.device
        except: pass
    return None

def drain():
    if ser is None or not ser.is_open: return
    try:
        ser.timeout = 0.05
        while ser.in_waiting: ser.read(ser.in_waiting)
        ser.read(256)
    except: pass
    ser.timeout = 2

def raw(cmd, timeout_s=1.5):
    if ser is None or not ser.is_open: return ""
    drain()
    data = (cmd + "\r\n").encode()
    if DEBUG: print(f"    [SEND] {data}")
    ser.write(data)
    ser.timeout = timeout_s
    t0 = time.time(); lines = []
    while time.time() - t0 < timeout_s:
        try:
            r = ser.read_until(b"\n")
            if r:
                line = r.decode(errors="replace").strip()
                if line:
                    lines.append(line)
                    if DEBUG: print(f"    [RECV] {line}")
            else:
                if lines: break
        except: break
        if r and ser.in_waiting == 0:
            time.sleep(0.02)
            if ser.in_waiting == 0: break
    ser.timeout = 2
    return lines[-1] if lines else ""

def joints():
    r = raw("#GETJPOS")
    if r:
        parts = r.replace("ok", "").strip().split()
        if len(parts) >= 6:
            return [float(x) for x in parts[:6]]
    return None

class DummyCLI(cmd.Cmd):
    intro = "  Dummy CLI v4  (debug 切换调试)"
    prompt = ">>> "

    def preloop(self):
        global SERIAL_PORT, ser
        if not SERIAL_PORT:
            SERIAL_PORT = find_port()
            if not SERIAL_PORT:
                print("[!!] Controller 未找到")
                print("    用 -p COM5 手动指定, -l 查串口, quit 退出")
                return
        if ser is None or not ser.is_open:
            try:
                ser = serial.Serial(SERIAL_PORT, 115200, timeout=2, write_timeout=1)
                print(f"Connected: {SERIAL_PORT}")
            except Exception as e:
                print(f"无法连接 {SERIAL_PORT}: {e}")
                return
        raw("#CMDMODE 2")
        j = joints()
        if j:
            print(f"  J1={j[0]:6.1f} J2={j[1]:6.1f} J3={j[2]:6.1f} J4={j[3]:6.1f} J5={j[4]:6.1f} J6={j[5]:6.1f}")

    def do_start(self, args):
        global ser, SERIAL_PORT
        if ser and ser.is_open:
            print("已连接")
            return
        port = args.strip() or SERIAL_PORT
        if not port:
            print("用法: start COM5")
            return
        try:
            ser = serial.Serial(port, 115200, timeout=2, write_timeout=1)
            SERIAL_PORT = port
            print(f"Connected: {port}")
            raw("#CMDMODE 2")
        except Exception as e:
            print(f"无法连接: {e}")

    def do_enable(self, args): print(raw("!START"))
    def do_disable(self, args): print(raw("!DISABLE"))
    def do_stop(self, args): print(raw("!STOP"))
    def do_home(self, args):
        raw("#CMDMODE 2")
        print(raw(">0,-70,180,0,0,0", timeout_s=8))
    def do_status(self, args):
        j = joints()
        if j:
            print(f"  J1={j[0]:6.1f} J2={j[1]:6.1f} J3={j[2]:6.1f} J4={j[3]:6.1f} J5={j[4]:6.1f} J6={j[5]:6.1f}")
    def do_jpos(self, args): self.do_status(args)
    def do_lpos(self, args): print(raw("#GETLPOS"))

    def do_move(self, args):
        parts = args.split()
        if len(parts) != 6: print("用法: move j1 j2 j3 j4 j5 j6"); return
        raw("#CMDMODE 2")
        j = [float(x) for x in parts]
        print(raw(f">{j[0]:.1f},{j[1]:.1f},{j[2]:.1f},{j[3]:.1f},{j[4]:.1f},{j[5]:.1f}"))

    def do_movej(self, args):
        parts = args.split()
        if len(parts) != 2: print("用法: movej <1-6> <角度>"); return
        idx = int(parts[0]) - 1; val = float(parts[1])
        if idx < 0 or idx > 5: print("关节号 1~6"); return
        if DEBUG: print(f"--- movej J{idx+1} -> {val} ---")
        raw("#CMDMODE 2")
        j = joints()
        if j is None: print("无法读取关节角度"); return
        if DEBUG: print(f"  当前: {j}")
        j[idx] = val
        cmd = f">{j[0]:.1f},{j[1]:.1f},{j[2]:.1f},{j[3]:.1f},{j[4]:.1f},{j[5]:.1f}"
        if DEBUG: print(f"  发送: {cmd}")
        r = raw(cmd)
        print(r)
        if DEBUG:
            time.sleep(0.5)
            j2 = joints()
            if j2:
                d = [j2[i]-j[i] for i in range(6)]
                print(f"  变化: {d}")

    def do_kp(self, args):
        p = args.split()
        if len(p) >= 2: print(raw(f"#SET_DCE_KP {p[0]} {p[1]}"))
    def do_ki(self, args):
        p = args.split()
        if len(p) >= 2: print(raw(f"#SET_DCE_KI {p[0]} {p[1]}"))
    def do_kd(self, args):
        p = args.split()
        if len(p) >= 2: print(raw(f"#SET_DCE_KD {p[0]} {p[1]}"))
    def do_reboot(self, args):
        if args.strip(): print(raw(f"#REBOOT {args.strip()}"))
    def do_mode(self, args):
        if args.strip(): print(raw(f"#CMDMODE {args.strip()}"))
    def do_raw(self, args):
        if args.strip(): print(raw(args.strip()))

    def do_scan(self, args):
        SKIP = {"COM3", "COM4"}
        for p in serial.tools.list_ports.comports():
            d = p.description or ""; tag = ""
            if p.device in SKIP: tag = " [SKIP]"
            elif "Bluetooth" in d: tag = " [SKIP]"
            elif "CP210" in d or "Silicon" in d: tag = " [CP2102]"
            elif "STM" in d or "Virtual COM" in d: tag = " [STM32 CDC]"
            print(f"  {p.device}: {d}{tag}")

    def do_debug(self, args):
        global DEBUG; DEBUG = not DEBUG
        print(f"调试: {'ON' if DEBUG else 'OFF'}")

    def do_quit(self, args): return True
    def emptyline(self): pass

    def postcmd(self, stop, line):
        if stop:
            if ser and ser.is_open:
                raw("!DISABLE"); ser.close(); print("Bye.")
        return stop


def main():
    global SERIAL_PORT, DEBUG
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port")
    parser.add_argument("-l", "--list", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args()
    if args.debug: DEBUG = True
    if args.list:
        for dev, desc, _ in list_ports(): print(f"  {dev}  -  {desc}")
        return
    if args.port: SERIAL_PORT = args.port
    try:
        DummyCLI().cmdloop()
    except KeyboardInterrupt:
        if ser and ser.is_open: raw("!DISABLE"); ser.close()
        print("\n已退出")

if __name__ == "__main__":
    main()
