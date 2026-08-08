"""
dummy_port_scanner.py  —  Dummy 机械臂端口智能检测工具

基于 USB 硬件 ID (VID/PID) 定位 CP2102 和 STM32 CDC，
不依赖 COM 号，然后用 #GETJPOS 探活确认。

用法:
    python dummy_port_scanner.py           # 自动检测并报告
    python dummy_port_scanner.py --connect # 检测后尝试连接并查询
"""

import sys
import time
import argparse
import serial
import serial.tools.list_ports

# ── 目标设备 VID/PID ──────────────────────────────────
CP2102_VID = "10C4"
CP2102_PID = "EA60"
STM32_VID  = "0483"
STM32_PID  = "5740"

# ── 探测 ──────────────────────────────────────────────

def scan_all_ports():
    """返回所有串口列表 [(device, desc, hwid)]"""
    return [(p.device, p.description, p.hwid) for p in serial.tools.list_ports.comports()]

def find_by_vid_pid(vid, pid):
    """按 VID/PID 查找端口, 返回 (device, desc, hwid) 或 None"""
    for dev, desc, hwid in scan_all_ports():
        if vid.upper() in hwid.upper() and pid.upper() in hwid.upper():
            return (dev, desc, hwid)
    return None

def probe_dummy(port):
    """
    对指定端口发 #GETJPOS 探活。
    返回 (ok: bool, response: str)
    """
    try:
        s = serial.Serial(port, 115200, timeout=0.8)
    except Exception as e:
        return False, f"无法打开端口: {e}"

    try:
        # 清空缓冲区
        s.reset_input_buffer()
        s.write(b"\n")
        time.sleep(0.05)
        s.reset_input_buffer()

        # 发查询命令
        s.write(b"#GETJPOS\n")
        time.sleep(0.3)

        # 读返回
        lines = []
        deadline = time.time() + 0.5
        while time.time() < deadline:
            try:
                line = s.readline().decode(errors="replace").strip()
                if line:
                    lines.append(line)
            except Exception:
                break

        for line in lines:
            if line.lower().startswith("ok") and len(line.split()) >= 4:
                return True, line

        if lines:
            return False, f"收到非预期数据: {' | '.join(lines[:3])}"
        else:
            return False, "无响应"
    finally:
        s.close()

# ── 主逻辑 ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Dummy 机械臂端口智能检测工具 (基于 VID/PID)")
    parser.add_argument("-c", "--connect", action="store_true",
                        help="检测后尝试连接并查询状态")
    parser.add_argument("-r", "--raw", action="store_true",
                        help="直接输出原始扫描结果")
    args = parser.parse_args()

    # ── 1. 扫描 ──
    all_ports = scan_all_ports()

    if args.raw:
        print(f"共检测到 {len(all_ports)} 个串口:\n")
        for dev, desc, hwid in all_ports:
            print(f"  {dev:8s}  {desc}")
            print(f"           {hwid}")
        return

    # ── 2. VID/PID 精准匹配 ──
    cp2102 = find_by_vid_pid(CP2102_VID, CP2102_PID)
    stm32  = find_by_vid_pid(STM32_VID, STM32_PID)

    print("=" * 56)
    print("  Dummy 端口扫描器")
    print("=" * 56)

    found_any = False

    if cp2102:
        dev, desc, hwid = cp2102
        print(f"\n  [OK] CP2102 (UART4 路径)")
        print(f"     端口:  {dev}")
        print(f"     描述:  {desc}")
        found_any = True

        # 探活
        print(f"     探活:  ", end="", flush=True)
        ok, resp = probe_dummy(dev)
        if ok:
            print(f"[OK] Dummy 固件响应正常")
            print(f"            {resp}")
        else:
            print(f"[!!] {resp}")
            print(f"     提示:  STM32 可能未复位，断电等待 30 秒再试")

    if stm32:
        dev, desc, hwid = stm32
        label = "STM32 CDC (内部 USB)" if cp2102 else "[OK] STM32 CDC (唯一目标)"
        print(f"\n  {label}")
        print(f"     端口:  {dev}")
        print(f"     描述:  {desc}")
        found_any = True

        if not cp2102:
            # 只有 CP2102 不在时才探活 CDC（避免重复）
            print(f"     探活:  ", end="", flush=True)
            ok, resp = probe_dummy(dev)
            if ok:
                print(f"[OK] Dummy 固件响应正常")
                print(f"            {resp}")
            else:
                print(f"[!!] {resp}")

    # ── 3. 其他端口 ──
    if all_ports:
        known_devices = set()
        if cp2102: known_devices.add(cp2102[0])
        if stm32:  known_devices.add(stm32[0])

        other = [(d, desc) for d, desc, _ in all_ports if d not in known_devices]
        if other:
            print(f"\n  [>>]  其他串口 ({len(other)} 个, 非 Dummy 目标):")
            for d, desc in other:
                print(f"     {d:8s}  {desc}")

    if not found_any:
        print(f"\n  [!!] 未检测到 Dummy 目标设备")
        if all_ports:
            print(f"  ({len(all_ports)} 个其他串口, 见上方列表)")
        else:
            print(f"  (系统无任何串口设备)")
        print(f"\n  排查建议:")
        print(f"  1. USB 线是否插好?")
        print(f"  2. Controller 板是否供电?")
        print(f"  3. 断电 30 秒后重新插 USB")

    # ── 4. 连接模式 ──
    if args.connect and found_any:
        target = cp2102 if cp2102 else stm32
        if target:
            dev = target[0]
            print(f"\n{'=' * 56}")
            print(f"  尝试连接 {dev} ...")
            ok, resp = probe_dummy(dev)
            if ok:
                print(f"  [OK] 连接成功!")
                print(f"     当前关节: {resp}")
            else:
                print(f"  [!!] 连接失败: {resp}")

    print()

if __name__ == "__main__":
    main()

