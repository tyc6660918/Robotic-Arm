"""Matplotlib interface for the Windows-native offline simulator."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Callable, Mapping, Sequence

import matplotlib.animation as animation
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, CheckButtons, Slider
import numpy as np


@dataclass(frozen=True)
class MasterInput:
    position_m: np.ndarray
    rpy_deg: np.ndarray
    grasp: float
    deadman: bool
    clutch: bool


class InteractiveViewer:
    """Fixed-layout 3D viewer with a virtual 6-DOF master console."""

    FRAME_COLORS = ("#d1495b", "#2a9d8f", "#277da1")

    def __init__(
        self,
        snapshot_provider: Callable[[], Mapping[str, object]],
        input_callback: Callable[[MasterInput], None],
        reset_callback: Callable[[], None],
        script_callback: Callable[[], None],
        health_check: Callable[[], None] | None = None,
        master_publish_rate_hz: float = 100.0,
        render_rate_hz: float = 30.0,
    ) -> None:
        self.snapshot_provider = snapshot_provider
        self.input_callback = input_callback
        self.reset_callback = reset_callback
        self.script_callback = script_callback
        self.health_check = health_check
        self.master_publish_rate_hz = max(1.0, float(master_publish_rate_hz))
        self.render_rate_hz = max(1.0, float(render_rate_hz))
        self._input_lock = threading.Lock()
        self._current_input: MasterInput | None = None
        self._publisher_running = threading.Event()
        self._publisher_thread: threading.Thread | None = None
        self._publisher_error: BaseException | None = None

        self.figure = plt.figure(figsize=(13.5, 8.2))
        self.figure.patch.set_facecolor("#f4f6f8")
        self.axes = self.figure.add_axes([0.04, 0.08, 0.61, 0.86], projection="3d")
        self.axes.set_facecolor("#ffffff")
        self._configure_axes()

        (self.actual_line,) = self.axes.plot(
            [], [], [], color="#212529", linewidth=5, marker="o", markersize=6,
            label="Actual Dummy",
        )
        (self.target_line,) = self.axes.plot(
            [], [], [], color="#40916c", linewidth=2, linestyle="--", alpha=0.75,
            label="Target",
        )
        (self.openrst_line,) = self.axes.plot(
            [], [], [], color="#6f42c1", linewidth=4, marker="o", markersize=4,
            label="Virtual OpenRST",
        )
        (self.trajectory_line,) = self.axes.plot(
            [], [], [], color="#f4a261", linewidth=1.5, alpha=0.85,
            label="Actual flange trail",
        )
        self.axes.legend(loc="upper left", fontsize=8)

        self.actual_frame = self._create_frame(alpha=1.0)
        self.target_frame = self._create_frame(alpha=0.5)
        self.master_frame = self._create_frame(alpha=0.8, linestyle=":")

        self.status_axes = self.figure.add_axes(
            [0.69, 0.79, 0.28, 0.10],
            frameon=False,
        )
        self.status_axes.set_axis_off()
        self.status_text = self.status_axes.text(
            0.0, 1.0, "State: DISABLED", fontsize=10, family="monospace",
            va="top", color="#202124",
        )
        self._sliders: dict[str, Slider] = {}
        self._slider_artists: dict[str, tuple[object, ...]] = {}
        self._slider_backgrounds: dict[str, object] = {}
        self._caching_slider_backgrounds = False
        self._checks: CheckButtons | None = None
        self._buttons: list[Button] = []
        self._build_controls()
        self._draw_event_id = self.figure.canvas.mpl_connect(
            "draw_event", self._on_figure_draw
        )
        self._animation: animation.FuncAnimation | None = None

    def _configure_axes(self) -> None:
        self.axes.set_xlim(-0.35, 0.35)
        self.axes.set_ylim(-0.45, 0.25)
        self.axes.set_zlim(-0.15, 0.7)
        self.axes.set_xticks(np.linspace(-0.3, 0.3, 5))
        self.axes.set_yticks(np.linspace(-0.4, 0.2, 5))
        self.axes.set_zticks(np.linspace(-0.1, 0.7, 5))
        self.axes.set_box_aspect((0.7, 0.7, 0.85))
        self.axes.set_xlabel("X (m)")
        self.axes.set_ylabel("Y (m)")
        self.axes.set_zlabel("Z (m)")
        self.axes.set_title("Dummy + Virtual OpenRST Offline Teleoperation")
        self.axes.grid(True, alpha=0.25)

    def _build_controls(self) -> None:
        slider_specs = (
            ("x", "X (m)", -0.15, 0.15, 0.0),
            ("y", "Y (m)", -0.15, 0.15, 0.0),
            ("z", "Z (m)", -0.15, 0.15, 0.0),
            ("roll", "Roll (deg)", -90.0, 90.0, 0.0),
            ("pitch", "Pitch (deg)", -90.0, 90.0, 0.0),
            ("yaw", "Yaw (deg)", -90.0, 90.0, 0.0),
            ("grasp", "Grasp", 0.0, 1.0, 0.0),
        )
        y = 0.78
        for key, label, minimum, maximum, initial in slider_specs:
            slider_axes = self.figure.add_axes([0.73, y, 0.22, 0.025])
            slider = Slider(
                slider_axes,
                label,
                minimum,
                maximum,
                valinit=initial,
                valstep=None,
            )
            slider.drawon = False
            dynamic_artists = (slider.poly, slider._handle, slider.valtext)
            for artist in dynamic_artists:
                artist.set_animated(True)
            self._slider_artists[key] = dynamic_artists
            slider.on_changed(
                lambda value, slider_key=key: self._on_slider_changed(
                    slider_key, value
                )
            )
            self._sliders[key] = slider
            y -= 0.065

        check_axes = self.figure.add_axes([0.73, 0.25, 0.19, 0.09])
        check_axes.set_facecolor("#f4f6f8")
        self._checks = CheckButtons(check_axes, ("Deadman", "Clutch"), (False, False))
        self._checks.on_clicked(self._on_control_changed)

        reset_axes = self.figure.add_axes([0.73, 0.17, 0.1, 0.045])
        reset_button = Button(reset_axes, "Reset", color="#e9ecef", hovercolor="#dee2e6")
        reset_button.on_clicked(self._on_reset)
        self._buttons.append(reset_button)

        script_axes = self.figure.add_axes([0.85, 0.17, 0.1, 0.045])
        script_button = Button(script_axes, "Run script", color="#d8f3dc", hovercolor="#b7e4c7")
        script_button.on_clicked(lambda _: self.script_callback())
        self._buttons.append(script_button)

    def _on_slider_changed(self, slider_key: str, value: object) -> None:
        self._on_control_changed(value)
        self._blit_slider(slider_key)

    def _blit_slider(self, slider_key: str) -> None:
        background = self._slider_backgrounds.get(slider_key)
        if background is None:
            return
        slider = self._sliders[slider_key]
        canvas = self.figure.canvas
        canvas.restore_region(background)
        for artist in self._slider_artists[slider_key]:
            slider.ax.draw_artist(artist)
        canvas.blit(slider.ax.bbox)

    def _on_figure_draw(self, event: object) -> None:
        if self._caching_slider_backgrounds:
            return
        if getattr(event, "canvas", self.figure.canvas) is not self.figure.canvas:
            return
        self._caching_slider_backgrounds = True
        try:
            canvas = self.figure.canvas
            for key, slider in self._sliders.items():
                self._slider_backgrounds[key] = canvas.copy_from_bbox(
                    slider.ax.bbox
                )
                for artist in self._slider_artists[key]:
                    slider.ax.draw_artist(artist)
                canvas.blit(slider.ax.bbox)
        finally:
            self._caching_slider_backgrounds = False

    def _on_control_changed(self, _: object) -> None:
        if self._checks is None:
            return
        deadman, clutch = self._checks.get_status()
        command = MasterInput(
            position_m=np.array(
                [self._sliders[axis].val for axis in ("x", "y", "z")],
                dtype=float,
            ),
            rpy_deg=np.array(
                [self._sliders[axis].val for axis in ("roll", "pitch", "yaw")],
                dtype=float,
            ),
            grasp=float(self._sliders["grasp"].val),
            deadman=bool(deadman),
            clutch=bool(clutch),
        )
        with self._input_lock:
            self._current_input = command
        self.input_callback(command)

    def _publish_current_input(self) -> None:
        with self._input_lock:
            command = self._current_input
        if command is not None:
            self.input_callback(command)

    def _publisher_loop(self) -> None:
        period_s = 1.0 / self.master_publish_rate_hz
        next_tick = time.perf_counter()
        try:
            while self._publisher_running.is_set():
                self._publish_current_input()
                next_tick += period_s
                remaining = next_tick - time.perf_counter()
                if remaining <= 0.0:
                    next_tick = time.perf_counter()
                    continue
                time.sleep(remaining)
        except BaseException as exc:
            with self._input_lock:
                self._publisher_error = exc
            self._publisher_running.clear()

    def _raise_if_publisher_failed(self) -> None:
        with self._input_lock:
            error = self._publisher_error
        if error is not None:
            raise RuntimeError("virtual master publisher failed") from error

    def _start_publisher(self) -> None:
        if self._publisher_thread is not None and self._publisher_thread.is_alive():
            return
        self._raise_if_publisher_failed()
        self._publisher_running.set()
        self._publisher_thread = threading.Thread(
            target=self._publisher_loop,
            name="virtual-master-publisher",
            daemon=True,
        )
        self._publisher_thread.start()

    def _stop_publisher(self) -> None:
        self._publisher_running.clear()
        if (
            self._publisher_thread is not None
            and self._publisher_thread.is_alive()
            and self._publisher_thread is not threading.current_thread()
        ):
            self._publisher_thread.join(timeout=1.0)

    def _on_reset(self, _: object) -> None:
        for slider in self._sliders.values():
            slider.reset()
        if self._checks is not None:
            states = self._checks.get_status()
            for index, state in enumerate(states):
                if state:
                    self._checks.set_active(index)
        self.reset_callback()
        self._on_control_changed(None)

    def _create_frame(
        self,
        alpha: float,
        linestyle: str = "-",
    ) -> tuple[object, object, object]:
        lines = []
        for color in self.FRAME_COLORS:
            (line,) = self.axes.plot(
                [], [], [], color=color, linewidth=2, alpha=alpha,
                linestyle=linestyle,
            )
            lines.append(line)
        return tuple(lines)  # type: ignore[return-value]

    @staticmethod
    def _set_polyline(line: object, points: object) -> None:
        array = np.asarray(points, dtype=float)
        if array.ndim != 2 or array.shape[0] == 0 or array.shape[1] != 3:
            line.set_data_3d([], [], [])
            return
        line.set_data_3d(array[:, 0], array[:, 1], array[:, 2])

    @staticmethod
    def _set_frame(
        lines: Sequence[object],
        transform: object,
        scale: float = 0.04,
    ) -> None:
        matrix = np.asarray(transform, dtype=float)
        if matrix.shape != (4, 4):
            for line in lines:
                line.set_data_3d([], [], [])
            return
        origin = matrix[:3, 3]
        for index, line in enumerate(lines):
            endpoint = origin + scale * matrix[:3, index]
            line.set_data_3d(
                [origin[0], endpoint[0]],
                [origin[1], endpoint[1]],
                [origin[2], endpoint[2]],
            )

    def update(self, _: int = 0) -> tuple[object, ...]:
        try:
            self._raise_if_publisher_failed()
            if self.health_check is not None:
                self.health_check()
        except BaseException:
            self.close()
            raise
        snapshot = self.snapshot_provider()
        self._set_polyline(self.actual_line, snapshot.get("actual_points", []))
        self._set_polyline(self.target_line, snapshot.get("target_points", []))
        self._set_polyline(self.openrst_line, snapshot.get("openrst_points", []))
        self._set_polyline(self.trajectory_line, snapshot.get("trajectory", []))
        self._set_frame(self.actual_frame, snapshot.get("actual_flange", np.eye(4)))
        self._set_frame(self.target_frame, snapshot.get("target_flange", np.eye(4)))
        self._set_frame(self.master_frame, snapshot.get("master_transform", np.eye(4)))

        position_error = float(snapshot.get("position_error_m", 0.0)) * 1000.0
        orientation_error = np.degrees(float(snapshot.get("orientation_error_rad", 0.0)))
        status = str(snapshot.get("status_text", "State: DISABLED"))
        self.status_text.set_text(
            f"{status}\nPosition error: {position_error:8.3f} mm\n"
            f"Orientation error: {orientation_error:7.3f} deg"
        )
        return (
            self.actual_line,
            self.target_line,
            self.openrst_line,
            self.trajectory_line,
            self.status_text,
            *self.actual_frame,
            *self.target_frame,
            *self.master_frame,
        )

    def show(self) -> None:
        interval_ms = max(1, int(round(1000.0 / self.render_rate_hz)))
        self._on_control_changed(None)
        self.update()
        # mplot3d must build its projection matrix before animated artists can blit.
        self.figure.canvas.draw()
        self._animation = animation.FuncAnimation(
            self.figure,
            self.update,
            interval=interval_ms,
            blit=True,
            cache_frame_data=False,
        )
        self._start_publisher()
        try:
            plt.show()
            self._raise_if_publisher_failed()
        finally:
            self._stop_publisher()

    def close(self) -> None:
        self._stop_publisher()
        plt.close(self.figure)
