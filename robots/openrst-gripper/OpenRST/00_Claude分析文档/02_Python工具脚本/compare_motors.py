#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电机规格对比分析工具
对比 Maxon RE10 和 WHEELTEC MG513 电机
"""

import json
from pathlib import Path
from datetime import datetime

def compare_motors():
    """对比两种电机的规格"""

    print("=" * 80)
    print("Motor Comparison: Maxon RE10 vs WHEELTEC MG513P10-12V")
    print("=" * 80)
    print()

    # 现有电机：Maxon RE10
    maxon_re10 = {
        "name": "Maxon RE10 1.5W 10mm",
        "type": "Brushless DC Motor",
        "manufacturer": "Maxon",
        "specifications": {
            "diameter_mm": 10,
            "length_mm": "~30 (without gearbox)",
            "shaft_diameter_mm": "~2-3 (估计值)",
            "weight_g": "~10-15 (估计值)",
            "voltage_v": 12,
            "power_w": 1.5,
            "max_torque_mNm": 3,
            "speed_rpm": "~10000 (no load)",
            "motor_type": "Brushless DC",
            "encoder": "16 CPT incremental encoder",
            "gearbox": {
                "model": "Maxon GP10A",
                "pitch_joint_ratio": "1:256",
                "jaw_joint_ratio": "1:64",
                "diameter_mm": 10
            },
            "mounting": "Planetary gearbox mounting",
            "price_range": "Very expensive (Maxon premium brand)"
        },
        "pros": [
            "Very high precision",
            "Excellent quality and reliability",
            "Compact size (10mm diameter)",
            "Integrated encoder",
            "Medical-grade quality"
        ],
        "cons": [
            "Very expensive",
            "May be overkill for some applications",
            "Proprietary gearbox interface"
        ]
    }

    # 新电机：WHEELTEC MG513P10-12V
    # 注意：MG513 系列通常是带减速器的有刷直流电机
    wheeltec_mg513 = {
        "name": "WHEELTEC MG513P10-12V",
        "type": "Brushed DC Geared Motor",
        "manufacturer": "WHEELTEC",
        "specifications": {
            "diameter_mm": "~25 (估计，需要从STEP文件确认)",
            "length_mm": "~50-60 (估计，需要从STEP文件确认)",
            "shaft_diameter_mm": "~6 (估计，需要从STEP文件确认)",
            "weight_g": "~100-150 (估计)",
            "voltage_v": 12,
            "power_w": "待确认",
            "motor_type": "Brushed DC with integrated gearbox",
            "gearbox": {
                "ratio": "待确认 (P10可能表示某种减速比)",
                "integrated": True
            },
            "encoder": "待确认 (可能包含编码器)",
            "mounting": "Standard mounting holes",
            "price_range": "Much cheaper (domestic brand)"
        },
        "pros": [
            "Much more affordable",
            "Integrated gearbox",
            "Easy to source in China",
            "Good availability"
        ],
        "cons": [
            "Larger size (likely 2-3x diameter)",
            "Lower precision than Maxon",
            "Brushed motor (maintenance needed)",
            "May need custom mounting adapter"
        ]
    }

    print("\n" + "=" * 80)
    print("CURRENT MOTOR: Maxon RE10")
    print("=" * 80)
    print(f"Type:           {maxon_re10['type']}")
    print(f"Diameter:       {maxon_re10['specifications']['diameter_mm']} mm")
    print(f"Power:          {maxon_re10['specifications']['power_w']} W")
    print(f"Torque:         {maxon_re10['specifications']['max_torque_mNm']} mNm")
    print(f"Gearbox:        {maxon_re10['specifications']['gearbox']['model']}")
    print(f"  - Pitch:      {maxon_re10['specifications']['gearbox']['pitch_joint_ratio']}")
    print(f"  - Jaw:        {maxon_re10['specifications']['gearbox']['jaw_joint_ratio']}")

    print("\n" + "=" * 80)
    print("NEW MOTOR: WHEELTEC MG513P10-12V")
    print("=" * 80)
    print(f"Type:           {wheeltec_mg513['type']}")
    print(f"Diameter:       {wheeltec_mg513['specifications']['diameter_mm']} mm (estimated)")
    print(f"Note:           Dimensions need to be measured from STEP file")
    print()
    print("[!] WARNING: Size Mismatch Expected!")
    print("   The MG513 motor is likely MUCH LARGER than the Maxon RE10 (10mm)")

    print("\n" + "=" * 80)
    print("CRITICAL COMPATIBILITY ISSUES TO CHECK")
    print("=" * 80)
    print()
    print("1. SIZE DIFFERENCE")
    print("   - Maxon RE10: ~10mm diameter")
    print("   - MG513:      ~25mm diameter (estimated)")
    print("   → motor_base.SLDPRT will need MAJOR redesign")
    print()
    print("2. SHAFT DIAMETER")
    print("   - Maxon: ~2-3mm (couples to planetary gearbox)")
    print("   - MG513: ~6mm (estimated)")
    print("   -> coupling_M2_M4.SLDPRT needs complete redesign")
    print()
    print("3. GEARBOX INTEGRATION")
    print("   - Maxon: External GP10A planetary gearbox (1:256 and 1:64)")
    print("   - MG513: Built-in gearbox (ratio unknown)")
    print("   → Need to verify MG513 gear ratio matches performance requirements")
    print()
    print("4. MOUNTING INTERFACE")
    print("   - Maxon: Proprietary gearbox mounting")
    print("   - MG513: Standard mounting holes")
    print("   → attachment_base.SLDPRT may need modification")
    print()
    print("5. CONTROL ELECTRONICS")
    print("   - Maxon: Brushless (needs ESCON 36/2 DC driver)")
    print("   - MG513: Brushed (simpler driver, but current driver may not work)")
    print()
    print("6. ENCODER")
    print("   - Maxon: 16 CPT integrated encoder")
    print("   - MG513: Encoder type unknown")
    print("   → Need to verify encoder compatibility with DAQ boards")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Extract exact dimensions from MG513 STEP file")
    print("2. Read WHEELTEC documentation for specifications")
    print("3. Calculate space requirements in drive_unit assembly")
    print("4. Design adapter/mounting solution")
    print("5. Verify gear ratio meets performance requirements (10N grip force)")
    print("6. Check if existing ESCON drivers can control brushed motor")

    # 保存对比报告
    comparison = {
        "timestamp": datetime.now().isoformat(),
        "current_motor": maxon_re10,
        "new_motor": wheeltec_mg513,
        "compatibility_concerns": [
            "Size difference: ~2.5x diameter increase expected",
            "Shaft coupling needs redesign",
            "Motor mount needs complete redesign",
            "Driver compatibility (brushless vs brushed)",
            "Encoder interface compatibility",
            "Gear ratio verification needed"
        ],
        "required_modifications": [
            "motor_base.SLDPRT - complete redesign",
            "coupling_M2_M4.SLDPRT - new coupling design",
            "attachment_base.SLDPRT - mounting interface changes",
            "drive_unit_base.SLDPRT - clearance check",
            "drive_unit_*_cover - clearance check",
            "Control electronics - driver replacement may be needed"
        ]
    }

    report_path = Path("E:/Robotic-Arm/OpenRST-main/motor_comparison_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)

    print(f"\nReport saved to: {report_path}")
    print("=" * 80)

    return comparison

if __name__ == "__main__":
    compare_motors()
