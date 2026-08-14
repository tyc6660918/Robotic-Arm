#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Drive Unit 结构分析工具（基于文件系统）
"""

import os
import json
from datetime import datetime
from pathlib import Path

def analyze_drive_unit_structure():
    """分析驱动单元的文件结构"""

    base_path = Path(r"E:\Robotic-Arm\OpenRST-main\CAD Files\drive_unit\SolidWorks")
    parts_path = base_path / "Parts"

    # 分类零件
    motor_related = []
    actuation_parts = []
    structure_parts = []
    mechanism_parts = []

    print("=" * 70)
    print("OpenRST Drive Unit - Component Analysis")
    print("=" * 70)
    print()

    if not parts_path.exists():
        print(f"[ERROR] Parts directory not found: {parts_path}")
        return

    # 扫描所有零件
    parts = sorted([f for f in parts_path.iterdir() if f.suffix.upper() == '.SLDPRT'])

    print(f"Total parts found: {len(parts)}")
    print()

    # 分类分析
    for part_file in parts:
        name = part_file.stem.lower()
        size_mb = part_file.stat().st_size / (1024 * 1024)

        part_info = {
            'filename': part_file.name,
            'name': part_file.stem,
            'size_mb': round(size_mb, 2),
            'category': 'unknown'
        }

        # 根据关键词分类
        if 'motor' in name:
            part_info['category'] = 'motor_related'
            part_info['description'] = 'Motor mounting/interface component'
            motor_related.append(part_info)

        elif 'actuation' in name or 'disk' in name:
            part_info['category'] = 'actuation'
            part_info['description'] = 'Actuation disk for cable drive'
            actuation_parts.append(part_info)

        elif 'coupling' in name:
            part_info['category'] = 'transmission'
            part_info['description'] = 'Coupling between motor and actuation disk'
            mechanism_parts.append(part_info)

        elif 'base' in name or 'cover' in name:
            part_info['category'] = 'structure'
            part_info['description'] = 'Structural/housing component'
            structure_parts.append(part_info)

        elif 'release' in name or 'engagement' in name or 'lever' in name or 'button' in name or 'cam' in name:
            part_info['category'] = 'mechanism'
            part_info['description'] = 'Tool exchange mechanism'
            mechanism_parts.append(part_info)

        elif 'cable' in name:
            part_info['category'] = 'cable'
            part_info['description'] = 'Cable management component'
            mechanism_parts.append(part_info)
        else:
            part_info['category'] = 'other'
            structure_parts.append(part_info)

    # 打印分类结果
    print("\n" + "="*70)
    print("1. MOTOR & TRANSMISSION (Most Critical for Motor Change)")
    print("="*70)
    for part in motor_related + [p for p in actuation_parts + mechanism_parts if 'coupling' in p['filename'].lower()]:
        print(f"  [{part['category'].upper():15}] {part['filename']:35} ({part['size_mb']:>6.2f} MB)")
        if 'description' in part:
            print(f"                     -> {part['description']}")

    print("\n" + "="*70)
    print("2. ACTUATION DISKS (Gear Interface)")
    print("="*70)
    for part in actuation_parts:
        print(f"  [{part['category'].upper():15}] {part['filename']:35} ({part['size_mb']:>6.2f} MB)")
        if 'description' in part:
            print(f"                     -> {part['description']}")

    print("\n" + "="*70)
    print("3. TOOL EXCHANGE MECHANISM")
    print("="*70)
    for part in mechanism_parts:
        if 'coupling' not in part['filename'].lower():
            print(f"  [{part['category'].upper():15}] {part['filename']:35} ({part['size_mb']:>6.2f} MB)")
            if 'description' in part:
                print(f"                     -> {part['description']}")

    print("\n" + "="*70)
    print("4. STRUCTURAL COMPONENTS")
    print("="*70)
    for part in structure_parts:
        print(f"  [{part['category'].upper():15}] {part['filename']:35} ({part['size_mb']:>6.2f} MB)")
        if 'description' in part:
            print(f"                     -> {part['description']}")

    # 生成详细报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'analysis_type': 'filesystem_based',
        'total_parts': len(parts),
        'categories': {
            'motor_related': motor_related,
            'actuation': actuation_parts,
            'mechanism': mechanism_parts,
            'structure': structure_parts
        },
        'motor_change_impact': {
            'critical_parts': [
                'motor_base.SLDPRT',
                'coupling_M2_M4.SLDPRT',
                'actuation_disk_M0.SLDPRT',
                'actuation_disk_M1.SLDPRT',
                'actuation_disk_M2.SLDPRT'
            ],
            'considerations': [
                'Motor mounting holes position and diameter',
                'Motor shaft diameter (affects coupling)',
                'Motor body diameter and length (clearance check)',
                'Gear center distance (motor to actuation disk)',
                'Cable routing space',
                'Weight distribution and moment of inertia'
            ]
        },
        'current_motor': {
            'model': 'Maxon RE10 1.5W 10mm',
            'diameter_mm': 10,
            'max_torque_mNm': 3,
            'gearbox': {
                'pitch': 'Maxon GP10A 1:256',
                'jaw': 'Maxon GP10A 1:64'
            }
        }
    }

    report_path = base_path.parent.parent / f"drive_unit_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "="*70)
    print(f"Report saved to: {report_path}")
    print("="*70)

    return report

if __name__ == "__main__":
    analyze_drive_unit_structure()
