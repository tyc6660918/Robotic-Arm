# VSCode 调试配置

## 1. 区域用途

本项目中所有固件目标的集中调试工作区。为三个基于 STM32 的系统提供 VSCode 启动配置、构建任务和 OpenOCD 接口脚本：rst-control-fw（STM32F103ZE）、dummy-ref-core-fw（STM32F405RG）以及 CubeMX 验证测试。支持三种调试器硬件类型（ST-Link、CMSIS-DAP、WCH-Link），具备 SWO/ITM 跟踪能力。将工具链路径和构建编排与各固件源码树隔离。

## 2. 关键文件

| 文件路径 | 用途 | 状态 | 备注 |
|-----------|---------|--------|-------|
| E:\Robotic-Arm\debug\.vscode\launch.json | 使用 Cortex-Debug 扩展为所有固件目标提供的主要调试配置 | 完成 | 7 个配置：3 个用于 rst-control-fw（ST-Link/CMSIS-DAP/WCH-Link），1 个用于 dummy-ref-core-fw（ST-Link），1 个附加模式，2 个用于 CubeMX 验证测试（T01/T02） |
| E:\Robotic-Arm\debug\.vscode\tasks.json | 用于 CubeMX 验证测试的 CMake 构建/清理/配置/烧录任务 | 完成 | 11 个任务，覆盖 T01-base 和 T02-usart-dma：构建、清理、配置、复合工作流、OpenOCD 烧录 |
| E:\Robotic-Arm\debug\.vscode\settings.json | 工具链路径和 IntelliSense 配置 | 完成 | ARM GCC 工具链位于 C:/Program Files (x86)/Arm GNU Toolchain arm-none-eabi/12.2 mpacbti-rel1/bin，OpenOCD 位于 C:/Users/TYC/.embedded-tools/openocd/xpack-openocd-0.12.0-7/bin |
| E:\Robotic-Arm\debug\openocd-configs\stlink-f103.cfg | 使用 ST-Link 调试器调试 STM32F103 的 OpenOCD 配置 | 完成 | SWD 传输，1.8MHz 适配器速度，包含暂停/复位/闪存编程的辅助函数 |
| E:\Robotic-Arm\debug\openocd-configs\cmsis-dap-f103.cfg | 使用 CMSIS-DAP 调试器调试 STM32F103 的 OpenOCD 配置 | 完成 | SWD 传输，1MHz 适配器速度，可配置 VID/PID |
| E:\Robotic-Arm\debug\openocd-configs\wch-link-f103.cfg | 使用 WCH-Link 调试器调试 STM32F103 的 OpenOCD 配置 | 完成 | 使用带 WCH VID/PID（0x0416:0x5021）的 cmsis-dap 驱动，1MHz 适配器速度 |
| E:\Robotic-Arm\debug\openocd-configs\stlink-f405.cfg | 使用 ST-Link 调试器调试 STM32F405 的 OpenOCD 配置 | 完成 | 用于 dummy-ref-core-fw，1.8MHz 适配器速度，支持 SWO/ITM 跟踪（168MHz CPU，2MHz SWO） |
| E:\Robotic-Arm\robots\U-Arm\.vscode\settings.json | U-Arm 机器人工作区的 Python/Conda 环境设置 | 最低限度 | 仅 Python 环境管理器配置，CMake ignoreCMakeListsMissing 标志 |
| E:\Robotic-Arm\robots\Dummy-Arm\firmware\dummy-ref-core-fw\CMakeLists.txt | 基于 STM32F405 的参考固件的 CMake 构建系统 | 完成 | ARM GCC 交叉编译、FreeRTOS、USB CDC、硬件 FPU，生成 .elf/.hex/.bin |

## 3. 当前进度

| 组件 | 状态 | 证据 | 备注 |
|-----------|--------|----------|-------|
| rst-control-fw 的调试配置 | 完成 | E:\Robotic-Arm\debug\.vscode\launch.json 包含 3 种调试器变体 + 1 种附加模式 | 缺少构建产物（control.elf） |
| dummy-ref-core-fw 的调试配置 | 完成 | E:\Robotic-Arm\debug\.vscode\launch.json 包含带 SWO 跟踪的 ST-Link 配置 | 仓库根目录不存在预期路径 firmware/ |
| OpenOCD 接口脚本 | 完成 | E:\Robotic-Arm\debug\openocd-configs\ 中的 4 个配置覆盖 3 种调试器类型和 2 个 MCU 系列 | 全部包含自定义暂停/复位/烧录辅助函数 |
| CubeMX 测试的 CMake 构建任务 | 完成 | E:\Robotic-Arm\debug\.vscode\tasks.json 包含 T01/T02 的 11 个任务 | 目标目录 cubemx-validation-test/ 不存在 |
| 工具链配置 | 完成 | E:\Robotic-Arm\debug\.vscode\settings.json 记录了 ARM GCC 12.2 和 OpenOCD 0.12.0-7 路径 | 已在全局上下文中验证 |
| SWO/ITM 跟踪配置 | 完成 | launch.json 包含 F103（72MHz/2MHz）和 F405（168MHz/2MHz）的 SWO 设置 | 需要硬件验证 |
| U-Arm 调试配置 | 未完成 | E:\Robotic-Arm\robots\U-Arm\.vscode\ 没有 launch.json | Python/ROS 工作区可能不需要固件调试 |

## 4. 已完成功能

- 定位所有 .vscode 目录：debug/ 和 robots/U-Arm/
- 编目了覆盖 3 个固件目标的 7 个调试配置
- 识别了 CubeMX 验证测试的 11 个构建/烧录任务
- 记录了工具链路径：ARM GCC 12.2、OpenOCD 0.12.0-7、MinGW Make
- 验证了针对 3 种调试器类型（ST-Link、CMSIS-DAP、WCH-Link）的 4 个 OpenOCD 配置文件
- 分析了 F103 和 F405 目标的 SWO/ITM 跟踪配置
- 识别了构建系统支持：CMake 用于测试/参考固件，Keil MDK 用于遗留项目

## 5. 未完成工作

| 任务 | 优先级 | 阻碍 | 下一步 |
|------|----------|---------|-----------|
| 构建 rst-control-fw 以生成 control.elf | 高 | rst-control-fw/control/build/control.elf 不存在 | 使用 Keil MDK 编译或验证实际构建输出路径 |
| 解决固件路径不匹配 | 中 | launch.json 引用 ${workspaceFolder}/firmware/，但实际路径为 robots/Dummy-Arm/firmware/ | 更新 dummy-ref-core-fw 配置的 launch.json 中的 svdFile 和可执行文件路径 |
| 定位或重建 CubeMX 验证测试 | 低 | cubemx-validation-test/ 目录不存在，阻碍 T01/T02 调试配置 | 验证测试是否在 f2db105 重组中被删除或需要重新创建 |
| 添加 U-Arm 调试配置 | 低 | robots/U-Arm/.vscode/ 无 launch.json | 确定 U-Arm 舵机控制器是否需要固件调试 |
| 添加 U-Arm 构建任务 | 低 | robots/U-Arm/.vscode/ 无 tasks.json | 如果需要 Python 包构建/测试工作流则创建构建任务 |

## 6. 使用说明

**工具链配置：**
- ARM GCC: C:/Program Files (x86)/Arm GNU Toolchain arm-none-eabi/12.2 mpacbti-rel1/bin
- OpenOCD: C:/Users/TYC/.embedded-tools/openocd/xpack-openocd-0.12.0-7/bin/openocd.exe
- GDB: arm-none-eabi-gdb.exe（来自 ARM GCC 工具链）
- MinGW Make: E:/C/mingw64/bin/mingw32-make.exe

**可用调试配置：**

1. **rst-control-fw（STM32F103ZE）** - 3 种调试器选项 + 1 种附加模式
   - ST-Link：启用 SWO/ITM 跟踪（72MHz CPU，2MHz SWO）
   - CMSIS-DAP：标准 SWD 调试
   - WCH-Link：使用带自定义 VID/PID 的 CMSIS-DAP 协议
   - 全部期望构建产物位于：rst-control-fw/control/build/control.elf
   
2. **dummy-ref-core-fw（STM32F405RG）** - 仅 ST-Link
   - 启用 SWO/ITM 跟踪（168MHz CPU，2MHz SWO）
   - 预期产物：firmware/dummy-ref-core-fw/build/REF-STM32F4-fw.elf
   
3. **CubeMX 验证测试** - T01-base、T02-usart-dma
   - 两者均使用 preLaunchTask 触发 CMake 构建
   - 预期产物：cubemx-validation-test/test-builds/T0X-*/build/T0X-*.elf

**OpenOCD 配置：**
- 所有配置均包含自定义辅助函数：halt_target()、reset_target()、flash_program()
- 已配置 GDB 附加/分离事件处理器
- 统一使用 SWD 传输
- 适配器速度：1.8MHz（ST-Link）、1MHz（CMSIS-DAP、WCH-Link）

**构建系统支持：**
- CMake：用于 dummy-ref-core-fw 和 CubeMX 测试构建
- Keil MDK-ARM：位于 robots/Dummy-Arm/firmware/stm32-control（control.uvprojx）
- 为 CMake 交叉编译指定了 MinGW Makefiles 生成器

**IntelliSense 配置：**
- C 标准：c11
- C++ 标准：c++14
- 编译器模式：gcc-arm
- Build/Drivers 目录已从文件资源管理器和搜索中排除

## 7. 风险与限制

| 风险 | 影响 | 证据 | 缓解措施 |
|------|--------|----------|------------|
| launch.json 与实际目录结构之间的路径不匹配 | 高 | launch.json 引用 ${workspaceFolder}/firmware/，但实际路径为 robots/Dummy-Arm/firmware/ | 更新 launch.json 中所有 dummy-ref-core-fw 路径以反映提交 f2db105/2603308 的重组 |
| 缺少构建产物，在编译项目前无法调试 | 高 | rst-control-fw/control/build/control.elf 不存在 | 在尝试调试会话前使用 Keil MDK-ARM 编译 rst-control-fw |
| CubeMX 测试目录可能已被删除或移动 | 中 | cubemx-validation-test/ 目录不存在 | 验证是否需要 T01/T02 测试；如果过时则移除陈旧配置 |
| 多个 .vscode 目录可能导致配置冲突 | 中 | debug/ 和 robots/U-Arm/ 均包含 .vscode/ 文件夹 | 在 VSCode 中打开特定工作区文件夹（debug/ 用于固件，U-Arm/ 用于 Python）以避免干扰 |
| WCH-Link VID/PID 可能需要根据实际硬件进行调整 | 低 | wch-link-f103.cfg 中硬编码的 VID/PID（0x0416:0x5021） | 使用物理 WCH-Link 调试器进行测试，如果设备使用不同标识符枚举则进行调整 |

## 8. 依赖项

- Cortex-Debug VSCode 扩展（所有固件调试必需）
- ARM GNU Toolchain arm-none-eabi 12.2 mpacbti-rel1
- OpenOCD xpack 0.12.0-7
- MinGW64（mingw32-make.exe）
- ST-Link / CMSIS-DAP / WCH-Link 硬件调试器
- CMake 3.19+ 用于交叉编译构建

## 9. 后续步骤

1. **构建 rst-control-fw 以生成 control.elf 产物** - 启用基于 STM32F103 的 RST 夹爪固件调试（对于全局上下文中记录的 P0 优先级固件初始化修复至关重要）
2. **更新 launch.json 路径以匹配重组后的目录结构** - 将 dummy-ref-core-fw 配置的 firmware/ 引用更改为 robots/Dummy-Arm/firmware/
3. **使用硬件测试每个调试器配置以验证连接性** - 使用物理目标板验证 ST-Link、CMSIS-DAP、WCH-Link 配置
4. **验证或移除 CubeMX 验证测试配置** - 确定是否需要 T01/T02 构建，或者是否应删除陈旧配置
5. **如果需要，为 robots/U-Arm 添加调试配置** - 评估 Python/ROS 工作区是否需要固件调试支持
