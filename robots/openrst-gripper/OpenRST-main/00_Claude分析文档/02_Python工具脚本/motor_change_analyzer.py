#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOLIDWORKS 电机更换影响分析工具
用于分析电机选型变更对装配体的影响
"""

import win32com.client
import pythoncom
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class SolidWorksAnalyzer:
    """SOLIDWORKS 装配体分析器"""

    def __init__(self, assembly_path: str):
        self.assembly_path = os.path.abspath(assembly_path)
        self.sw_app = None
        self.model_doc = None
        self.analysis_result = {
            'timestamp': datetime.now().isoformat(),
            'assembly_path': self.assembly_path,
            'components': [],
            'constraints': [],
            'affected_parts': [],
        }

    def connect_solidworks(self) -> bool:
        """连接到 SOLIDWORKS 实例"""
        try:
            pythoncom.CoInitialize()
            self.sw_app = win32com.client.Dispatch("SldWorks.Application")
            self.sw_app.Visible = True
            print(f"[OK] Connected to SOLIDWORKS {self.sw_app.RevisionNumber}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to connect to SOLIDWORKS: {e}")
            return False

    def open_assembly(self) -> bool:
        """打开装配体文件"""
        try:
            if not os.path.exists(self.assembly_path):
                print(f"[ERROR] File not found: {self.assembly_path}")
                return False

            # 打开文档参数: 类型=2(装配体), 选项=1(静默)
            errors = 0
            warnings = 0
            self.model_doc = self.sw_app.OpenDoc6(
                self.assembly_path,
                2,  # swDocASSEMBLY
                1,  # swOpenDocOptions_Silent
                "",
                errors,
                warnings
            )

            if self.model_doc is None:
                print(f"[ERROR] Failed to open assembly (errors: {errors}, warnings: {warnings})")
                return False

            print(f"[OK] Opened assembly: {os.path.basename(self.assembly_path)}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to open assembly: {e}")
            # Try alternative method
            try:
                print("[INFO] Trying alternative opening method...")
                self.model_doc = self.sw_app.OpenDoc(self.assembly_path, 2)
                if self.model_doc:
                    print(f"[OK] Opened assembly: {os.path.basename(self.assembly_path)}")
                    return True
            except Exception as e2:
                print(f"[ERROR] Alternative method also failed: {e2}")
            return False

    def analyze_components(self) -> List[Dict]:
        """分析装配体中的所有零部件"""
        components = []

        try:
            config = self.model_doc.GetActiveConfiguration()
            root_comp = config.GetRootComponent3(True)

            # 获取所有子零部件
            children = root_comp.GetChildren()

            for comp in children:
                comp_name = comp.Name2
                comp_path = comp.GetPathName()
                comp_type = "Assembly" if comp.GetComponentType() == 0 else "Part"

                # 检查是否与电机相关
                is_motor_related = self._is_motor_related(comp_name, comp_path)

                comp_info = {
                    'name': comp_name,
                    'path': comp_path,
                    'type': comp_type,
                    'is_motor_related': is_motor_related,
                    'is_suppressed': comp.IsSuppressed(),
                }

                components.append(comp_info)

                if is_motor_related:
                    print(f"  [MOTOR] Found motor-related part: {comp_name}")

            self.analysis_result['components'] = components
            print(f"[OK] Analyzed {len(components)} components")
            return components

        except Exception as e:
            print(f"[ERROR] Failed to analyze components: {e}")
            return []

    def _is_motor_related(self, comp_name: str, comp_path: str) -> bool:
        """判断零件是否与电机相关"""
        keywords = [
            'motor', 'Motor', 'MOTOR', '电机',
            'coupling', 'Coupling',  # 联轴器
            'shaft', 'Shaft',  # 轴
            'actuation', 'drive',  # 驱动
            'motor_base',  # 电机座
        ]

        name_lower = comp_name.lower()
        path_lower = comp_path.lower() if comp_path else ""

        return any(keyword.lower() in name_lower or keyword.lower() in path_lower
                  for keyword in keywords)

    def analyze_mates(self) -> List[Dict]:
        """分析装配体中的约束关系"""
        mates = []

        try:
            feat = self.model_doc.FirstFeature()

            while feat is not None:
                feat_type = feat.GetTypeName2()

                if feat_type == "MateGroup":
                    # 这是一个配合组
                    mate_data = feat.GetSpecificFeature2()
                    mate_count = mate_data.GetMateCount()

                    for i in range(mate_count):
                        mate = mate_data.GetMate(i)
                        mate_type = mate.GetMateType()

                        mate_info = {
                            'name': feat.Name,
                            'type': self._get_mate_type_name(mate_type),
                        }
                        mates.append(mate_info)

                feat = feat.GetNextFeature()

            self.analysis_result['constraints'] = mates
            print(f"[OK] Analyzed {len(mates)} constraints")
            return mates

        except Exception as e:
            print(f"[ERROR] Failed to analyze constraints: {e}")
            return []

    def _get_mate_type_name(self, mate_type: int) -> str:
        """获取约束类型名称"""
        mate_types = {
            0: "Coincident",
            1: "Parallel",
            2: "Perpendicular",
            3: "Tangent",
            4: "Concentric",
            5: "Distance",
            6: "Angle",
        }
        return mate_types.get(mate_type, f"Unknown({mate_type})")

    def generate_report(self, output_path: str = None) -> str:
        """生成分析报告"""
        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(self.assembly_path),
                f"motor_change_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_result, f, ensure_ascii=False, indent=2)

            print(f"[OK] Report saved to: {output_path}")
            return output_path

        except Exception as e:
            print(f"[ERROR] Failed to save report: {e}")
            return ""

    def close(self):
        """关闭连接"""
        try:
            if self.model_doc:
                self.sw_app.CloseDoc(self.model_doc.GetTitle())
            pythoncom.CoUninitialize()
            print("[OK] Connection closed")
        except Exception as e:
            print(f"[WARNING] Error while closing: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("SOLIDWORKS Motor Change Analysis Tool")
    print("=" * 60)

    # 装配体路径
    assembly_path = r"E:\Robotic-Arm\OpenRST-main\CAD Files\drive_unit\SolidWorks\Assemblies\drive_unit.SLDASM"

    analyzer = SolidWorksAnalyzer(assembly_path)

    # 连接 SOLIDWORKS
    if not analyzer.connect_solidworks():
        return

    # 打开装配体
    if not analyzer.open_assembly():
        analyzer.close()
        return

    # 分析零部件
    print("\n[1/2] Analyzing components...")
    analyzer.analyze_components()

    # 分析约束
    print("\n[2/2] Analyzing constraints...")
    analyzer.analyze_mates()

    # 生成报告
    print("\nGenerating report...")
    report_path = analyzer.generate_report()

    # 关闭
    analyzer.close()

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
