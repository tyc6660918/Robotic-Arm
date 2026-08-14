#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 STEP 文件提取电机尺寸信息
"""

import re
from pathlib import Path

def extract_step_info(step_file_path):
    """从 STEP 文件提取基本信息"""

    print("=" * 80)
    print(f"Analyzing STEP file: {Path(step_file_path).name}")
    print("=" * 80)
    print()

    try:
        with open(step_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 提取文件头信息
        header_match = re.search(r'FILE_DESCRIPTION.*?ENDSEC;', content, re.DOTALL)
        if header_match:
            print("FILE HEADER:")
            print("-" * 80)
            header = header_match.group(0)
            # 提取描述
            desc_match = re.search(r"'([^']*)'", header)
            if desc_match:
                print(f"Description: {desc_match.group(1)}")
            print()

        # 查找产品信息
        product_matches = re.findall(r"PRODUCT\('([^']*)'", content)
        if product_matches:
            print("PRODUCT INFORMATION:")
            print("-" * 80)
            for i, product in enumerate(set(product_matches), 1):
                print(f"{i}. {product}")
            print()

        # 尝试找到尺寸相关的数值
        # STEP 文件中的坐标和尺寸通常是实数
        numbers = re.findall(r'[-+]?\d*\.\d+|\d+', content[:50000])  # 只看前50k字符

        # 转换为浮点数并过滤
        floats = []
        for num in numbers:
            try:
                f = float(num)
                if 1 < f < 200:  # 假设电机尺寸在 1-200mm 范围内
                    floats.append(f)
            except:
                pass

        if floats:
            print("POTENTIAL DIMENSIONS (mm):")
            print("-" * 80)
            # 找出常见的数值（可能是主要尺寸）
            from collections import Counter
            common = Counter(floats).most_common(20)

            print("Most common values (could be key dimensions):")
            for value, count in common[:10]:
                if count > 3:  # 出现多次的可能是关键尺寸
                    print(f"  {value:8.2f} mm  (appears {count} times)")
            print()

        # 文件大小分析
        file_size = Path(step_file_path).stat().st_size
        print("FILE STATISTICS:")
        print("-" * 80)
        print(f"File size: {file_size / 1024:.1f} KB")
        print(f"Total lines: {len(content.splitlines())}")

        # 计算实体数量（粗略估计）
        solid_count = content.count('CLOSED_SHELL')
        print(f"Approximate solid count: {solid_count}")
        print()

        print("=" * 80)
        print("RECOMMENDATIONS:")
        print("=" * 80)
        print()
        print("To get exact dimensions, you should:")
        print("1. Open the STEP file in SOLIDWORKS")
        print("2. Use Measure tool to get:")
        print("   - Motor body diameter")
        print("   - Motor total length")
        print("   - Output shaft diameter")
        print("   - Output shaft length")
        print("   - Mounting hole positions and sizes")
        print("   - Mounting flange dimensions")
        print()
        print("Or provide the PDF specifications if you can open it.")
        print("=" * 80)

    except Exception as e:
        print(f"Error reading STEP file: {e}")
        return None

def compare_step_files():
    """对比新旧电机的 STEP 文件"""

    new_motor = Path(r"D:\BaiduNetdiskDownload\WHEELTEC 直流电机附送资料\三维模型\直流电机_MG513\直流电机_MG513P10-12V(GMR）.stp")

    print("\n")
    print("#" * 80)
    print("# NEW MOTOR: WHEELTEC MG513P10-12V")
    print("#" * 80)

    if new_motor.exists():
        extract_step_info(new_motor)
    else:
        print(f"File not found: {new_motor}")

    # 查找现有装配体的 STEP 文件
    print("\n")
    print("#" * 80)
    print("# EXISTING DRIVE UNIT")
    print("#" * 80)

    existing_step = Path(r"E:\Robotic-Arm\OpenRST-main\CAD Files\drive_unit\STEP\drive_unit.step")
    if existing_step.exists():
        print(f"\nFound existing assembly STEP: {existing_step}")
        print(f"Size: {existing_step.stat().st_size / (1024*1024):.1f} MB")
        print("\nNote: This is the full assembly, not just the motor.")
        print("The Maxon motor is likely embedded inside this assembly.")

if __name__ == "__main__":
    compare_step_files()
