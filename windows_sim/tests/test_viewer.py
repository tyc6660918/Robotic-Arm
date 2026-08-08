from __future__ import annotations

import time
import unittest
from unittest.mock import Mock, call, patch, sentinel

import matplotlib

matplotlib.use("Agg", force=True)

from windows_sim.sim.viewer import InteractiveViewer


class InteractiveViewerTests(unittest.TestCase):
    def test_master_publisher_runs_independently_of_rendering(self) -> None:
        input_callback = Mock()
        viewer = InteractiveViewer(
            snapshot_provider=Mock(return_value={}),
            input_callback=input_callback,
            reset_callback=Mock(),
            script_callback=Mock(),
            master_publish_rate_hz=100.0,
        )
        self.addCleanup(viewer.close)
        viewer._on_control_changed(None)
        input_callback.reset_mock()

        viewer._start_publisher()
        time.sleep(0.045)
        viewer._stop_publisher()

        self.assertGreaterEqual(input_callback.call_count, 3)

    def test_render_does_not_duplicate_the_independent_master_publisher(self) -> None:
        input_callback = Mock()
        viewer = InteractiveViewer(
            snapshot_provider=Mock(return_value={}),
            input_callback=input_callback,
            reset_callback=Mock(),
            script_callback=Mock(),
        )
        self.addCleanup(viewer.close)

        viewer.update()

        input_callback.assert_not_called()

    def test_status_artist_can_participate_in_blitting(self) -> None:
        viewer = InteractiveViewer(
            snapshot_provider=Mock(return_value={}),
            input_callback=Mock(),
            reset_callback=Mock(),
            script_callback=Mock(),
        )
        self.addCleanup(viewer.close)

        self.assertIs(viewer.status_text.axes, viewer.status_axes)

    def test_sliders_use_local_blitting_instead_of_full_figure_draws(self) -> None:
        viewer = InteractiveViewer(
            snapshot_provider=Mock(return_value={}),
            input_callback=Mock(),
            reset_callback=Mock(),
            script_callback=Mock(),
        )
        self.addCleanup(viewer.close)

        for key, slider in viewer._sliders.items():
            with self.subTest(slider=key):
                self.assertFalse(slider.drawon)
                self.assertTrue(slider.poly.get_animated())
                self.assertTrue(slider._handle.get_animated())
                self.assertTrue(slider.valtext.get_animated())

        with patch.object(viewer.figure.canvas, "draw_idle") as draw_idle:
            viewer._sliders["x"].set_val(0.05)
        draw_idle.assert_not_called()

    def test_slider_change_only_blits_its_own_axes(self) -> None:
        viewer = InteractiveViewer(
            snapshot_provider=Mock(return_value={}),
            input_callback=Mock(),
            reset_callback=Mock(),
            script_callback=Mock(),
        )
        self.addCleanup(viewer.close)
        x_slider = viewer._sliders["x"]
        y_slider = viewer._sliders["y"]
        viewer._slider_backgrounds["x"] = sentinel.x_background

        with (
            patch.object(viewer.figure.canvas, "restore_region") as restore_region,
            patch.object(viewer.figure.canvas, "blit") as blit,
            patch.object(x_slider.ax, "draw_artist") as draw_x_artist,
            patch.object(y_slider.ax, "draw_artist") as draw_y_artist,
        ):
            x_slider.set_val(0.05)

        restore_region.assert_called_once_with(sentinel.x_background)
        self.assertEqual(
            draw_x_artist.call_args_list,
            [call(artist) for artist in viewer._slider_artists["x"]],
        )
        draw_y_artist.assert_not_called()
        blit.assert_called_once_with(x_slider.ax.bbox)

    def test_full_draw_rebuilds_all_slider_backgrounds(self) -> None:
        viewer = InteractiveViewer(
            snapshot_provider=Mock(return_value={}),
            input_callback=Mock(),
            reset_callback=Mock(),
            script_callback=Mock(),
        )
        self.addCleanup(viewer.close)

        viewer.figure.canvas.draw()

        self.assertEqual(
            set(viewer._slider_backgrounds), set(viewer._sliders)
        )

    def test_health_failure_closes_the_window_before_propagating(self) -> None:
        snapshot_provider = Mock(return_value={})

        def fail_health_check() -> None:
            raise RuntimeError("control loop stopped")

        viewer = InteractiveViewer(
            snapshot_provider=snapshot_provider,
            input_callback=Mock(),
            reset_callback=Mock(),
            script_callback=Mock(),
            health_check=fail_health_check,
        )
        self.addCleanup(viewer.close)

        with patch.object(viewer, "close") as close:
            with self.assertRaisesRegex(RuntimeError, "control loop stopped"):
                viewer.update()
            close.assert_called_once_with()
        snapshot_provider.assert_not_called()

    def test_master_publisher_failure_is_propagated(self) -> None:
        def fail_publish(_: object) -> None:
            raise RuntimeError("publisher callback stopped")

        viewer = InteractiveViewer(
            snapshot_provider=Mock(return_value={}),
            input_callback=fail_publish,
            reset_callback=Mock(),
            script_callback=Mock(),
            master_publish_rate_hz=100.0,
        )
        self.addCleanup(viewer.close)
        with viewer._input_lock:
            viewer._current_input = Mock()

        viewer._start_publisher()
        viewer._publisher_thread.join(timeout=1.0)

        with self.assertRaisesRegex(RuntimeError, "virtual master publisher failed") as raised:
            viewer.update()
        self.assertIsInstance(raised.exception.__cause__, RuntimeError)
        self.assertEqual(str(raised.exception.__cause__), "publisher callback stopped")


if __name__ == "__main__":
    unittest.main()
