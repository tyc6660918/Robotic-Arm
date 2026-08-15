# Dummy机械臂MoveIt 2 HTTP接口开发文档

本接口提供基于RESTful架构的访问方式，用于通过MoveIt 2控制Dummy机械臂。外部系统（Web控制面板、移动应用或其他服务端）无需配置本地ROS 2环境即可向机械臂下发控制指令。

**基础访问地址**：`http://<ROBOT_IP>:8000`

---

## 1. 接口总览

| 方法 | 端点 | 功能说明 |
| :--- | :--- | :--- |
| **GET** | `/api/status` | 获取机器人当前执行状态及关节位置。 |
| **GET** | `/api/pose` | 获取末端执行器当前笛卡儿位姿（X、Y、Z、四元数）。 |
| **POST** | `/api/move_to_pose` | 基于标准MoveIt规划，移动至笛卡儿（X、Y、Z）目标位姿。 |
| **POST** | `/api/move_optimal` | 基于优化规划，以当前关节或自定义关节为逆运动学初始种子，求解最近似的IK解并执行运动。 |

---

## 2. 接口说明

### GET `/api/status`
返回MoveIt接口当前状态及实时关节位置（单位为弧度）。

**响应示例**：
```json
{
  "status": "ok",
  "robot_state": "IDLE", 
  "current_joints": [0.0, -1.30, 1.57, 0.0, 0.0, 0.0]
}
```
注意：`robot_state`的可能取值为`IDLE`（空闲）、`REQUESTING`（请求中）或`EXECUTING`（执行中）。

---

### GET `/api/pose`
执行正运动学计算，返回末端执行器当前笛卡儿位姿。

**响应示例**：
```json
{
  "status": "ok",
  "frame_id": "dummy_base_link",
  "position": {
    "x": 0.25,
    "y": 0.0,
    "z": 0.20
  },
  "orientation": {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "w": 1.0
  }
}
```

---

### POST `/api/move_to_pose`
标准笛卡儿空间规划。MoveIt将搜索通往目标位姿的运动路径。

**请求体**：
```json
{
  "x": 0.25,
  "y": 0.0,
  "z": 0.3,
  "qx": 0.0,
  "qy": 0.0,
  "qz": 0.0,
  "qw": 1.0,
  "cartesian": false
}
```

---

### POST `/api/move_optimal`
搜索与`start_joints`（或当前真实关节位置）最接近且满足目标位姿约束的关节构型，随后执行关节空间轨迹。**推荐用于最小化冗余运动。**

**请求体**：
```json
{
  "x": 0.20,
  "y": -0.1,
  "z": 0.25,
  "qx": 0.0,
  "qy": 0.0,
  "qz": 0.0,
  "qw": 1.0,
  "start_joints": [0.0, -1.0, 1.2, 0.0, 0.5, 0.0] 
}
```
`start_joints`为可选参数。若省略，服务端将使用机器人当前实际关节位置作为初始值。

---

## 3. 使用示例

### 使用`curl`（命令行方式）
**采用优化规划移动至指定点位：**
```bash
curl -X POST "http://localhost:8000/api/move_optimal" \
     -H "Content-Type: application/json" \
     -d '{
           "x": 0.22,
           "y": 0.05,
           "z": 0.3,
           "qw": 1.0
         }'
```

---

### 使用Python（`requests`库）
```python
import requests
import time

BASE_URL = "http://192.168.1.100:8000" # 替换为实际机器人IP地址

def move_robot(x, y, z):
    payload = {
        "x": x, "y": y, "z": z,
        "qw": 1.0
    }
    response = requests.post(f"{BASE_URL}/api/move_optimal", json=payload)
    return response.json()

def wait_for_idle():
    while True:
        status = requests.get(f"{BASE_URL}/api/status").json()
        if status["robot_state"] == "IDLE":
            print("机器人已就绪。")
            break
        print("机器人运动中...")
        time.sleep(0.5)

# 示例工作流程
if __name__ == "__main__":
    print(move_robot(0.2, 0.0, 0.25))
    wait_for_idle()
    print("任务完成！")
```

---

## 4. 开发注意事项
- **坐标系规范**：位置值单位为米（m），关节值单位为弧度（rad）。
- **姿态约定**：默认姿态`[0,0,0,1]`（qx,qy,qz,qw）在Dummy机械臂构型下通常对应末端执行器朝下。
- **安全机制**：若机器人当前处于`EXECUTING`状态，接口将以`400`错误拒绝新的目标请求。
