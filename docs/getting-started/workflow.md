# 🔄 开发工作流

完整的 STM32 + CubeMX 开发循环。

---

## 标准开发流程

```
需求分析
   ↓
CubeMX 图形化配置外设
   ↓
生成初始化代码
   ↓
VSCode 编写业务逻辑
   ↓
编译
   ↓
调试（OpenOCD + GDB）
   ↓
验证功能
   ↓
提交代码
```

---

## 1. 配置外设（CubeMX）

### 打开现有项目
```bash
# 找到 .ioc 文件
robots/dummy-arm/firmware/stm32-control/control.ioc

# 用 STM32CubeMX 打开
```

### 配置步骤
1. **Pinout & Configuration** - 选择外设、配置引脚
2. **Clock Configuration** - 配置系统时钟树
3. **Project Manager** - 设置工程名称和路径
4. **Generate Code** - 生成初始化代码

### ⚠️ 重要：保护用户代码
CubeMX 会保留 `USER CODE BEGIN` 和 `USER CODE END` 之间的代码：

```c
/* USER CODE BEGIN 0 */
// 你的代码在这里是安全的
int my_variable = 42;
/* USER CODE END 0 */
```

---

## 2. 编写业务逻辑（VSCode）

### 推荐的代码组织

```c
// main.c
int main(void) {
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM2_Init();
    
    /* USER CODE BEGIN 2 */
    App_Init();  // 你的初始化
    /* USER CODE END 2 */
    
    while (1) {
        /* USER CODE BEGIN 3 */
        App_Loop();  // 你的主循环
        /* USER CODE END 3 */
    }
}
```

### 创建独立的应用文件
```
Core/
├── Inc/
│   └── app_main.h      # 应用头文件
└── Src/
    └── app_main.c      # 应用实现
```

---

## 3. 编译

### VSCode 内编译
```
Ctrl + Shift + B  →  选择 "Build" 任务
```

### 命令行编译
```bash
cd robots/dummy-arm/firmware/stm32-control
make -j8
```

### 查看编译输出
```
Build finished successfully.
   text    data     bss     dec     hex filename
  27468    1472   20684   49624    c1e8 build/control.elf
```

---

## 4. 调试

### VSCode 调试
```
F5  →  自动编译 + 烧录 + 启动调试
```

### 常用调试操作
- `F5` - 继续执行
- `F10` - 单步跳过（Step Over）
- `F11` - 单步进入（Step Into）
- `Shift + F11` - 单步跳出（Step Out）
- `Shift + F5` - 停止调试

### 查看变量
```
左侧"变量"面板 → 自动显示局部变量
右键变量 → "添加到监视" → 持续跟踪
```

### 查看寄存器
```
左侧"外设"面板 → 展开外设 → 查看寄存器值
```

---

## 5. 串口调试

### 连接串口
```
开发板 UART1 → USB转串口 → PC
波特率: 115200
数据位: 8
停止位: 1
校验: None
```

### 查看日志
```bash
# Windows (PowerShell)
mode COM5 BAUD=115200 PARITY=N DATA=8

# Linux/Mac
screen /dev/ttyUSB0 115200
```

---

## 6. 修改外设配置的流程

### 场景：我想添加一个新的定时器

**Step 1:** 打开 CubeMX
```bash
# 打开 .ioc 文件
STM32CubeMX → Open Project → control.ioc
```

**Step 2:** 配置新外设
```
Pinout & Configuration → Timers → TIM3
  - Mode: PWM Generation CH1
  - Prescaler: 71
  - Counter Period: 999
```

**Step 3:** 生成代码
```
Project → Generate Code
```

**Step 4:** 在 VSCode 中添加业务逻辑
```c
/* USER CODE BEGIN 2 */
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
__HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, 500); // 50% 占空比
/* USER CODE END 2 */
```

**Step 5:** 编译、调试、验证

---

## 7. Git 工作流

### 开发新功能
```bash
# 1. 创建功能分支
git checkout -b feature/add-motor-control

# 2. 开发、测试
# ... 编码 ...

# 3. 提交
git add Core/Src/motor_control.c
git commit -m "feat: Add motor PWM control

- Implement motor speed control via TIM3 PWM
- Add safety current limiting
- Tested with 42 stepper motor

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"

# 4. 推送并创建 PR
git push -u origin feature/add-motor-control
gh pr create
```

### ⚠️ 不要提交的文件
```
build/           # 编译产物
*.axf *.hex      # 二进制文件
*.uvguix.*       # Keil 用户配置
__pycache__/     # Python 缓存
```

---

## 8. 故障排查清单

### 编译失败
- [ ] 工具链是否正确安装？
- [ ] Makefile 路径是否正确？
- [ ] 缺少的头文件是否已包含？

### 烧录失败
- [ ] OpenOCD 是否能连接到目标？
- [ ] SWD 线是否连接正确？
- [ ] 开发板是否上电？

### 程序不运行
- [ ] BOOT0 跳线是否正确？
- [ ] 是否有 HardFault？（查看串口输出）
- [ ] 外设时钟是否使能？

### 外设不工作
- [ ] 外设时钟是否使能？（RCC->APBxENR）
- [ ] GPIO 是否配置正确？
- [ ] 中断是否使能？（NVIC）
- [ ] 引脚是否有复用冲突？

---

## 9. 性能优化

### 编译优化级别
```makefile
# Makefile
OPT = -Og      # 调试优化（默认）
OPT = -O2      # 性能优化
OPT = -Os      # 大小优化
```

### 查看代码大小
```bash
arm-none-eabi-size build/control.elf
```

### 分析栈使用
```bash
arm-none-eabi-objdump -h build/control.elf | grep -E "\.stack|\.heap"
```

---

## 10. 常用工具命令

### 查看固件信息
```bash
arm-none-eabi-readelf -h build/control.elf
```

### 反汇编
```bash
arm-none-eabi-objdump -d build/control.elf > disassembly.txt
```

### 查看符号表
```bash
arm-none-eabi-nm build/control.elf | sort
```

---

## 下一步

- 📖 完整调试教程 → [`../guides/debugging-complete.md`](../guides/debugging-complete.md)
- 🏗️ 项目架构说明 → [`../technical/architecture.md`](../technical/architecture.md)
- 🔧 硬件连接详细步骤 → [`../guides/hardware-setup.md`](../guides/hardware-setup.md)

---

**有问题随时问我！** 💬
