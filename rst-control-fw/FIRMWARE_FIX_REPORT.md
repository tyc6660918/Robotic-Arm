## RST Motor Controller - 固件修复说明

### 修复完成 ✅

已清理 DeepSeek 留下的问题代码，重构为完整的实时控制系统。

---

## 修复内容

### 1. 删除的死代码
- ❌ `app_main.c` - 与 `main.c` 完全重复的文件

### 2. 新增文件
- ✅ `Core/Src/control_loop.c` - 完整的 20kHz 控制循环实现
- ✅ `Core/Src/tim6.c` - TIM6 定时器配置 (20kHz 中断)

### 3. 修改的文件
- ✅ `stm32f1xx_it.c` - 添加 TIM6 中断处理和 UART 回调
- ✅ `main.c` - 添加控制系统初始化和安全启动
- ✅ `rst_config.h` - 添加 `RST_ControlInit()` 函数声明
- ✅ `tim.h` - 添加 TIM6 声明

---

## 实现的功能

### 控制循环 (`control_loop.c`)
1. **编码器读取** - 16位溢出处理 + 角度/速度计算
2. **电流采样** - ADC DMA 三通道连续采样
3. **PID 控制器** - 带积分限幅和微分滤波
4. **归零状态机** - 堵转检测自动寻找机械零点
5. **三种控制模式**:
   - `MODE_POSITION` - 位置环 (PID)
   - `MODE_VELOCITY` - 速度环 (P控制)
   - `MODE_CURRENT` - 力矩环 (开环电流)
6. **堵转保护** - 电流+速度双重判断

### 安全机制
- ✅ 启动前所有电机刹车
- ✅ 编码器计数器初始化到中间值 (避免溢出)
- ✅ PWM 启动顺序正确
- ✅ 控制循环在初始化完成后才启动

---

## 下一步操作 (在 CubeMX 中)

### ⚠️ 必须在 CubeMX 中配置

你需要打开 `.ioc` 文件，配置以下内容：

#### 1. TIM6 配置
- **Pinout & Configuration** → **Timers** → **TIM6**
  - Mode: `Internal Clock`
  - Prescaler: `35` (72MHz / 36 = 2MHz)
  - Counter Period: `99` (2MHz / 100 = 20kHz)
  - **NVIC Settings**: 勾选 `TIM6 global interrupt`

#### 2. ADC1 DMA 配置
- **ADC1** → **DMA Settings**
  - DMA Request: `ADC1`
  - Mode: `Circular`
  - Data Width: `Half Word` (16bit)

#### 3. GPIO 配置检查
确认以下引脚已配置：
- **方向引脚** (PB0/1/5/12/13/14): `GPIO_Output`
- **编码器引脚**: TIM2/3/4 Encoder Mode
- **PWM 引脚**: TIM1_CH1, TIM8_CH1/CH2

#### 4. 生成代码
- **Project Manager** → **Code Generator**
  - 勾选 `Generate peripheral initialization as a pair of '.c/.h' files per peripheral`
- 点击 **GENERATE CODE**

---

## 编译前注意

### Keil 项目配置
1. 确保添加了新文件到项目：
   - `Core/Src/control_loop.c`
   - `Core/Src/tim6.c`

2. 删除 `app_main.c` (如果项目中还在)

3. 编译选项建议：
   - Optimization: `-O2`
   - 勾选 `Use MicroLIB` (减小代码体积)

---

## 测试步骤

### 1. 基础测试 (不转电机)
```
help          # 查看命令列表
info          # 检查系统状态
led 1 blink   # LED 测试
enc 0         # 读编码器 (手动转电机看计数变化)
```

### 2. PWM 测试 (空载)
```
pwm 0 100     # Pitch 电机 10% PWM
pwm 0 0       # 停止
```

### 3. 控制模式测试 (需要实现命令)
你可能需要在 `debug_console.c` 中添加控制命令，例如：
```c
// 位置控制命令
static void Cmd_Move(int argc, char **argv) {
    int ch = atoi(argv[1]);
    float angle = atof(argv[2]);
    g_rst.motor[ch].mode = MODE_POSITION;
    g_rst.motor[ch].goal_angle = angle;
    g_rst.motor[ch].enabled = true;
}
```

---

## 关键改进点

### 原代码问题 → 修复方案
1. **控制循环是空的** → 实现完整的传感器读取 + PID + 输出
2. **没有定时器中断** → 添加 TIM6 20kHz 中断
3. **文件重复** → 删除 `app_main.c`
4. **启动不安全** → 添加刹车初始化
5. **编码器会溢出** → 初始化到 32768

---

## 性能指标

- **控制频率**: 20kHz (50μs 周期)
- **中断优先级**: 最高 (0)
- **编码器分辨率**: 2400 线/圈 (12线×4倍频×50减速比)
- **电流采样精度**: ~4mA/bit (INA180A1 + 0.1Ω)
- **PID 默认参数**: Kp=3.0, Ki=0.05, Kd=0.5

---

## 如果还有问题

1. **编译错误** - 检查是否在 Keil 中添加了新文件
2. **链接错误** - 确保 `tim6.c` 被编译
3. **电机不响应** - 检查 TIM6 中断是否使能
4. **堵转误报** - 调整 `STALL_CURRENT_MA` 和 `STALL_VELOCITY_LIMIT`

需要我帮你添加更多调试命令或者调整 PID 参数吗？
