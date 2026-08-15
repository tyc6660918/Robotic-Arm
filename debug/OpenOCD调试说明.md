# OpenOCD 与烧录基础设施

## 1. 区域用途

本区域使用 OpenOCD 为 STM32 目标（F103ZE 和 F405RG）提供全面的调试和烧录支持。支持多种硬件调试器（ST-Link、CMSIS-DAP、WCH-Link），包含自动化连接测试，并与 VSCode 集成以实现带 SWO/ITM 跟踪功能的交互式调试。

## 2. 关键文件

| 文件路径 | 用途 | 状态 | 备注 |
|-----------|---------|--------|-------|
| /e/Robotic-Arm/debug/openocd-configs/配置文件使用说明.md | 全面的 OpenOCD 文档，涵盖所有调试器类型、使用示例、故障排除和配置自定义 | 完成 | 8KB 文件，包含 ST-Link、CMSIS-DAP、WCH-Link 调试器的详细说明；包括快速入门、烧录方法、GDB 调试、SWO 跟踪设置和详尽的故障排除部分 |
| /e/Robotic-Arm/debug/openocd-configs/stlink-f103.cfg | 适用于 STM32F103ZE（rst-control-fw）的 ST-Link 调试器配置 | 完成 | 使用 HLA 接口，1.8MHz SWD，包含辅助函数（halt_target、reset_target、flash_program），已配置 GDB 事件处理器 |
| /e/Robotic-Arm/debug/openocd-configs/cmsis-dap-f103.cfg | 适用于 STM32F103ZE 的 CMSIS-DAP/DAPLink 调试器配置 | 完成 | 标准 CMSIS-DAP 协议，1MHz SWD，支持 VID/PID 和序列号指定，包含与 ST-Link 配置相同的辅助函数 |
| /e/Robotic-Arm/debug/openocd-configs/dap-f103.cfg | 特定硬件的已验证配置：野火 DAP 小智款 + STM32F103ZET6 | 完成 | 关键：为 CMSIS-DAP v1 HID 传输指定 'cmsis-dap backend hid'；已使用序列号 6D656D6F7279 测试；防止 'hid_write failed' 错误 |
| /e/Robotic-Arm/debug/openocd-configs/wch-link-f103.cfg | 适用于 STM32F103ZE 的 WCH-Link/WCH-LinkE 调试器配置 | 完成 | 使用带 VID/PID 0x0416:0x5021 的 CMSIS-DAP 协议，包含关于驱动程序要求和固件版本兼容性的故障排除说明 |
| /e/Robotic-Arm/debug/openocd-configs/stlink-f405.cfg | 适用于 STM32F405RG（dummy-ref-core-fw）的 ST-Link 调试器配置 | 完成 | 与 stlink-f103.cfg 类似，但目标为 STM32F4x，包含 168MHz CPU 的 SWO 配置 |
| /e/Robotic-Arm/debug/openocd-configs/test-connection.sh | 适用于所有调试器配置的自动化硬件连接测试脚本 | 完成 | 按顺序测试所有 4 个配置，超时时间 3 秒，提供详细的成功/失败输出，将工作配置保存到 /tmp/openocd_working_config.txt，包含故障排除建议 |
| /e/Robotic-Arm/debug/.vscode/launch.json | 用于 Cortex-Debug 扩展的 VSCode 调试配置 | 完成 | 7 个配置：3 个用于 rst-control-fw（ST-Link/CMSIS-DAP/WCH-Link），1 个用于 dummy-ref-core-fw，1 个附加配置，2 个用于测试构建；包含 SWO/ITM 跟踪设置 |
| /e/Robotic-Arm/debug/.vscode/tasks.json | 用于测试构建的 VSCode 构建和烧录任务 | 完成 | T01-base 和 T02-usart-dma 测试构建的任务；包含配置/构建/清理/烧录序列；烧录任务使用带 'program' 命令的 OpenOCD |
| /e/Robotic-Arm/docs/getting-started/调试快速上手.md | STM32 调试快速入门指南（5 分钟设置） | 完成 | 硬件连接说明、test-connection.sh 使用、VSCode F5 调试、命令行 GDB 说明、故障排除 FAQ |

## 3. 当前进度

| 组件 | 状态 | 证据 | 备注 |
|-----------|--------|----------|-------|
| 适用于 ST-Link、CMSIS-DAP、WCH-Link 调试器的 OpenOCD 配置 | 完成 | debug/openocd-configs/ 中的 5 个 .cfg 文件支持 F103ZE 和 F405RG 目标 | 所有配置遵循一致的结构，带有辅助 TCL 过程和 GDB 事件处理器 |
| 自动化连接测试脚本 | 完成 | test-connection.sh（138 行），带顺序测试和详细输出 | 按顺序测试所有 4 个配置，每个配置超时 3 秒 |
| VSCode 调试集成 | 完成 | launch.json 中的 7 个调试配置，支持 Cortex-Debug 扩展 | 包含 F103（72MHz）和 F405（168MHz）的 SWO/ITM 跟踪设置 |
| 构建和烧录自动化 | 完成 | tasks.json 带 CMake 配置/构建/清理/烧录序列 | 烧录任务使用带 'program' 命令的 OpenOCD |
| 全面文档 | 完成 | 配置文件使用说明.md（342 行），带快速入门、故障排除和自定义指南 | 包含 5 个常见问题的解决方案和使用技巧 |
| 硬件验证的 CMSIS-DAP v1 配置 | 完成 | dap-f103.cfg 指定 'cmsis-dap backend hid' 以修复 HID 传输问题 | 已使用野火 DAP 小智款序列号 6D656D6F7279 测试 |
| 专用烧录脚本 | 未完成 | 仓库中未找到独立的 Python/shell 烧录工具 | 通过 OpenOCD 命令行或 VSCode 任务完成烧录 |
| VSCode 配置中的路径一致性 | 未完成 | launch.json 引用 ${workspaceFolder}/openocd-configs/，但实际路径为 debug/openocd-configs/ | 路径不匹配可能导致调试失败 |
| 固件路径引用 | 未完成 | launch.json 引用不存在的 rst-control-fw/ 目录；实际固件位于 robots/Dummy-Arm/firmware/ | 这些路径问题表明配置可能需要更新 |

## 4. 已完成功能

1. **多调试器支持**：四种调试器类型已完全配置（ST-Link V2/V2.1/V3、CMSIS-DAP/DAPLink、野火 DAP 小智款 CMSIS-DAP v1、WCH-Link/WCH-LinkE），所有配置之间具有一致的 TCL 辅助过程。

2. **双目标架构**：针对 STM32F103ZE @ 72MHz（霸道开发板）和 STM32F405RG @ 168MHz 的独立配置，带有适当的 SWO 时序参数。

3. **自动化硬件检测**：test-connection.sh 脚本提供所有 4 个配置的顺序测试，带电压检测、硬件断点信息解析，并将工作配置持久化到 /tmp/openocd_working_config.txt。

4. **VSCode IDE 集成**：7 个调试配置覆盖所有调试器类型，带 preLaunchTask 集成以在调试前自动构建。Cortex-Debug 扩展配置的 OpenOCD 路径为 C:/Users/TYC/.embedded-tools/openocd/xpack-openocd-0.12.0-7/bin/openocd.exe。

5. **SWO/ITM 跟踪**：在 launch.json 中为 F103（72MHz）和 F405（168MHz）目标配置，带有用于跟踪时序的适当 CPU 时钟设置。

6. **CMSIS-DAP v1 HID 传输修复**：dap-f103.cfg 指定 'cmsis-dap backend hid' 以解决野火 DAP 小智款硬件上的 'hid_write failed' 错误。

7. **全面文档**：配置文件使用说明.md（342 行）涵盖快速入门示例、带自定义选项的详细配置说明、详尽的故障排除部分（5 个常见问题）、使用技巧（别名、芯片信息、闪存操作）、SWO 跟踪设置以及官方资源链接。

## 5. 未完成工作

| 任务 | 优先级 | 阻碍 | 下一步 |
|------|----------|---------|-----------|
| 修复 launch.json 中的路径引用 | P1 | launch.json 引用 ${workspaceFolder}/openocd-configs/，但实际路径为 debug/openocd-configs/ | 将 openocd-configs 移动到仓库根目录或将引用更新为 debug/openocd-configs/ |
| 更新固件路径引用 | P1 | launch.json 引用不存在的 rst-control-fw/；实际固件位于 robots/Dummy-Arm/firmware/stm32-control | 将 launch.json 中所有固件路径引用从 rst-control-fw 更新为 robots/Dummy-Arm/firmware/stm32-control |
| 创建专用烧录脚本 | P2 | 未找到独立的 Python/shell 烧录工具；通过 OpenOCD CLI 或 VSCode 任务完成烧录 | 考虑创建专用烧录脚本（例如 flash.sh），封装常见 OpenOCD 命令以便于 CLI 使用 |
| 为其他调试器硬件添加配置 | P3 | 仅支持 ST-Link、CMSIS-DAP、WCH-Link | 如果团队使用其他探针类型，添加相应的 .cfg 文件 |
| 测试所有 launch.json 配置 | P1 | 路径不匹配可能导致调试无法正常工作 | 测试所有 launch.json 配置以验证路径并确保它们适用于当前目录结构 |
| 记录工作区文件夹要求 | P2 | 不清楚用户应打开 debug/ 文件夹还是仓库根目录 | 在 README 或调试指南中记录工作区文件夹要求 |
| 使 OpenOCD 路径可移植 | P2 | 硬编码的绝对路径（C:/Users/TYC/...）使配置在团队成员间不可移植 | 对 OpenOCD 安装路径使用相对路径或环境变量 |
| 修复 test-connection.sh Windows 兼容性 | P3 | 脚本使用 /tmp/，在 Windows 上可能无法可靠工作 | 更新脚本以使用 Windows 兼容的临时目录路径 |

## 6. 使用说明

### 支持的调试器

1. **ST-Link V2/V2.1/V3**：stlink-f103.cfg、stlink-f405.cfg
2. **CMSIS-DAP/DAPLink**：cmsis-dap-f103.cfg
3. **野火 DAP 小智款 CMSIS-DAP v1**：dap-f103.cfg（带 HID 后端的硬件验证）
4. **WCH-Link/WCH-LinkE**：wch-link-f103.cfg

### 目标芯片

- **STM32F103ZE @ 72MHz**（霸道开发板）：stlink-f103.cfg、cmsis-dap-f103.cfg、dap-f103.cfg、wch-link-f103.cfg
- **STM32F405RG @ 168MHz**：stlink-f405.cfg

### 配置架构

所有配置遵循一致的结构：

1. 接口配置（适配器驱动、传输选择 SWD）
2. 适配器速度（500-1800 kHz）
3. 目标芯片配置（source [find target/stm32f1x.cfg]）
4. 复位配置（srst_only srst_nogate）
5. 辅助 TCL 过程：halt_target()、reset_target()、flash_program()
6. 用于附加/分离的 GDB 事件处理器

**关键技术特性：**
- dap-f103.cfg 指定 'cmsis-dap backend hid' 以修复 CMSIS-DAP v1 HID 传输问题
- 为 F103（72MHz）和 F405（168MHz）配置了 SWO/ITM 跟踪
- 所有 STM32 目标的闪存基地址：0x08000000
- GDB 服务器端口：3333（默认）
- 工作区大小：具有显式 WORKAREASIZE 的 F103 配置为 0x5000

### 烧录方法

1. **OpenOCD 命令行**：
   ```bash
   openocd -f <config> -c "program firmware.elf verify reset exit"
   ```

2. **带自定义过程的 OpenOCD**：
   ```bash
   openocd -f <config> -c init -c "flash_program firmware.elf" -c exit
   ```

3. **VSCode 任务**：tasks.json 中的构建 → 烧录序列

4. **VSCode F5 调试**：通过 launch.json preLaunchTask 自动构建 → 烧录 → 调试

5. **直接 flash_write_image**：手动暂停 → 擦除 → 写入 → 验证 → 运行

### 硬件验证

运行 test-connection.sh 进行自动化测试：
- 按顺序测试所有 4 个配置
- 每个配置超时 3 秒
- 解析 OpenOCD 输出以获取电压检测和硬件断点信息
- 将工作配置保存到 /tmp/openocd_working_config.txt
- 返回详细的错误消息和故障排除建议

### VSCode 集成

- launch.json 中的 7 个调试配置覆盖所有调试器类型
- 需要 Cortex-Debug 扩展
- OpenOCD 路径：C:/Users/TYC/.embedded-tools/openocd/xpack-openocd-0.12.0-7/bin/openocd.exe
- 配置引用 ${workspaceFolder}/openocd-configs/（需要将路径修正为 debug/openocd-configs/）
- preLaunchTask 集成用于在调试前自动构建

## 7. 风险与限制

| 风险 | 影响 | 证据 | 缓解措施 |
|------|--------|----------|------------|
| launch.json 中的路径不匹配可能导致调试失败 | 高 | launch.json 引用 ${workspaceFolder}/openocd-configs/，但实际路径为 debug/openocd-configs/ | 将所有路径引用更新为 debug/openocd-configs/ 或将配置移动到仓库根目录 |
| 硬编码的绝对路径使配置在团队成员间不可移植 | 中 | launch.json 中的 OpenOCD 路径 C:/Users/TYC/.embedded-tools/... | 对工具路径使用相对路径或环境变量 |
| test-connection.sh 在 Windows 上可能无法可靠工作 | 中 | 脚本使用非标准 Windows 路径 /tmp/ | 更新脚本以使用 Windows 兼容的临时目录（$TEMP 或 %TEMP%） |
| 如果 OpenOCD 配置被意外修改，没有版本控制或备份机制 | 低 | 未记录 .cfg 备份或恢复机制 | 考虑添加 git 挂钩以警告 .cfg 修改或维护参考副本 |
| 没有文档说明哪些固件项目实际存在与配置中引用的内容 | 中 | launch.json 引用不存在的 rst-control-fw/；实际固件位于 robots/Dummy-Arm/firmware/ | 在 f2db105/2603308 重组后更新文档和配置以反映实际目录结构 |
| 缺少专用烧录脚本增加了 CLI 用户的使用门槛 | 低 | 未找到独立烧录工具；需要键入完整的 OpenOCD 命令 | 为常见烧录操作创建包装脚本（flash.sh、flash.py） |

## 8. 依赖项

- **OpenOCD 0.12.0-7**（xpack 发行版，位于 C:/Users/TYC/.embedded-tools/openocd/xpack-openocd-0.12.0-7/）
- **Cortex-Debug VSCode 扩展**，用于交互式调试
- **arm-none-eabi-gdb**，用于 GDB 调试会话
- **硬件调试器**：ST-Link V2/V2.1/V3、CMSIS-DAP/DAPLink、WCH-Link/WCH-LinkE 或兼容探针
- **CMake 和 MinGW**，用于构建任务集成
- **目标硬件**：带 SWD 接口的 STM32F103ZE 或 STM32F405RG 开发板

## 9. 后续步骤

1. **[P1] 修复 launch.json 中的路径引用**：将 ${workspaceFolder}/openocd-configs/ 更新为 debug/openocd-configs/ 或将配置移动到仓库根目录。这是阻止 VSCode 调试开箱即用的关键阻碍。

2. **[P1] 更新固件路径引用**：将 launch.json 中所有 rst-control-fw 引用更改为 robots/Dummy-Arm/firmware/stm32-control，以反映 f2db105/2603308 仓库重组。

3. **[P1] 测试所有 launch.json 配置**：验证所有 7 个调试配置在修正路径和当前目录结构下均可正常工作，以确保新开发人员可以立即进行调试。

4. **[P2] 使 OpenOCD 路径可移植**：用环境变量或相对路径替换硬编码的 C:/Users/TYC/...，使配置无需修改即可在团队成员间工作。

5. **[P2] 记录工作区文件夹要求**：在 README 或调试指南中说明用户应打开 debug/ 文件夹还是仓库根目录作为工作区文件夹。

6. **[P2] 创建专用烧录脚本**：将常见 OpenOCD 命令封装在 flash.sh 或 flash.py 中以便于 CLI 使用（例如 `./flash.sh firmware.elf stlink-f103`）。

7. **[P3] 修复 test-connection.sh Windows 兼容性**：更新脚本以使用 $TEMP 或 %TEMP% 而非 /tmp/，以便在 Windows 上可靠运行。

8. **[P3] 为其他调试器硬件添加配置**：如果团队使用其他探针类型（J-Link、Black Magic Probe），按照已建立的模式添加相应的 .cfg 文件。

9. **[P3] 为配置添加版本控制保护**：考虑 git 挂钩或备份机制，以防止意外修改工作中的 .cfg 文件。
