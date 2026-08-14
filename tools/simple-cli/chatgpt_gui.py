import sys
import argparse
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt5.QtChart import QChart, QChartView, QLineSeries
from PyQt5.QtCore import Qt, QTimer, QDateTime


def list_ports():
    """列出可用串口"""
    ports = serial.tools.list_ports.comports()
    result = []
    for p in ports:
        result.append((p.device, p.description))
    return result

def auto_detect_port():
    """自动检测串口"""
    ports = list_ports()
    if not ports:
        return None
    for device, desc in ports:
        d = desc.lower()
        if "stm" in d or "usb" in d or "serial" in d:
            print(f"[自动检测] 选择端口: {device} ({desc})")
            return device
    print(f"[自动检测] 使用第一个串口: {ports[0][0]} ({ports[0][1]})")
    return ports[0][0]


class MainWindow(QMainWindow):
    def __init__(self, port):
        super().__init__()

        self.setWindowTitle("Dummy MPU6050 实时数据")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # 状态提示
        self.status_label = QLabel("正在连接...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; padding: 8px;")

        self.chart_view = QChartView(self)
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.addWidget(self.status_label)
        self.central_layout.addWidget(self.chart_view)

        self.accel_series_x = QLineSeries()
        self.accel_series_x.setName("Accel X")
        self.accel_series_y = QLineSeries()
        self.accel_series_y.setName("Accel Y")
        self.accel_series_z = QLineSeries()
        self.accel_series_z.setName("Accel Z")

        self.chart = QChart()
        self.chart.addSeries(self.accel_series_x)
        self.chart.addSeries(self.accel_series_y)
        self.chart.addSeries(self.accel_series_z)
        self.chart.createDefaultAxes()
        self.chart.setTitle("MPU6050 Accelerometer")
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignBottom)
        self.chart_view.setChart(self.chart)
        self.chart_view.chart().axisY().setRange(-2, 2)

        try:
            self.serial_port = serial.Serial(port, 115200, timeout=1)
            self.status_label.setText(f"已连接 {port}")
            self.status_label.setStyleSheet(
                "font-size: 14px; padding: 8px; color: green;")
        except Exception as e:
            self.status_label.setText(f"串口连接失败: {e}")
            self.status_label.setStyleSheet(
                "font-size: 14px; padding: 8px; color: red;")
            self.serial_port = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_chart)
        self.timer.start(500)

    def update_chart(self):
        if self.serial_port is None:
            return
        try:
            self.serial_port.write(b"#GETMPU\n")
            line = self.serial_port.readline().decode("utf-8").strip()
            if line.startswith("ok"):
                data_str = line[3:].split(" ")
                if len(data_str) == 3:
                    accel_data = [float(val) for val in data_str]
                    timestamp = QDateTime.currentDateTime().toMSecsSinceEpoch()
                    self.accel_series_x.append(timestamp, accel_data[0])
                    self.accel_series_y.append(timestamp, accel_data[1])
                    self.accel_series_z.append(timestamp, accel_data[2])
                    # 保持最近120个点
                    if self.accel_series_x.count() > 120:
                        self.accel_series_x.removePoints(
                            0, self.accel_series_x.count() - 20)
                        self.accel_series_y.removePoints(
                            0, self.accel_series_y.count() - 20)
                        self.accel_series_z.removePoints(
                            0, self.accel_series_z.count() - 20)
                    self.chart_view.chart().axisX().setRange(
                        timestamp - 120000, timestamp)
        except (ValueError, serial.SerialException, OSError) as e:
            self.status_label.setText(f"读取错误: {e}")
            self.status_label.setStyleSheet(
                "font-size: 14px; padding: 8px; color: orange;")


def main():
    parser = argparse.ArgumentParser(
        description="Dummy MPU6050 加速度实时图表")
    parser.add_argument("-p", "--port", help="指定串口 (如 COM3)")
    parser.add_argument("-l", "--list", action="store_true", help="列出所有可用串口后退出")
    args = parser.parse_args()

    if args.list:
        ports = list_ports()
        if not ports:
            print("未检测到任何串口设备")
        else:
            print("可用串口:")
            for dev, desc in ports:
                print(f"  {dev}  -  {desc}")
        return

    if args.port:
        port = args.port
    else:
        port = auto_detect_port()
        if port is None:
            print("未检测到串口！请用 -p 手动指定端口")
            print("用法: python chatgpt_gui.py -p COM3")
            print("或用 -l 查看可用串口")
            return

    print(f"连接 {port} (波特率 115200)")
    print("注意: 固件中需已实现 #GETMPU 命令才能显示数据！")

    app = QApplication(sys.argv)
    window = MainWindow(port)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
