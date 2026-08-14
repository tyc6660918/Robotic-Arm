from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.spatial.transform import Rotation


WINDOWS_SIM = Path(__file__).resolve().parents[1]
if str(WINDOWS_SIM) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SIM))

from sim.mock_plant import FaultConfig, MockJointPlant, PlantConfig
from sim.openrst_model import IdealOpenRSTModel
from sim.teleop_mapper import SafetyFault, TeleopSafetyStateMachine
from sim.types import Pose, TeleopState


def one_joint_config() -> PlantConfig:
    return PlantConfig(
        lower_limits=np.array([-0.5]),
        upper_limits=np.array([0.5]),
        velocity_limits=1.0,
        acceleration_limits=4.0,
        jerk_limits=40.0,
        response_time=0.1,
    )


class SafetyStateMachineTests(unittest.TestCase):
    def test_timeout_holds_and_requires_explicit_rearm(self) -> None:
        safety = TeleopSafetyStateMachine(input_timeout=0.05)
        self.assertEqual(safety.enable().state, TeleopState.READY)
        self.assertEqual(
            safety.update(0.0, 0.0, deadman=True, clutch=False).state,
            TeleopState.TELEOP,
        )

        timed_out = safety.update(0.051, 0.0, deadman=True, clutch=False)
        self.assertEqual(timed_out.state, TeleopState.HOLD)
        self.assertTrue(timed_out.fault_bits & int(SafetyFault.INPUT_TIMEOUT))

        still_held = safety.update(0.06, 0.06, deadman=True, clutch=False)
        self.assertEqual(still_held.state, TeleopState.HOLD)
        safety.update(0.07, 0.07, deadman=False, clutch=False)
        rearmed = safety.update(0.08, 0.08, deadman=True, clutch=False)
        self.assertEqual(rearmed.state, TeleopState.TELEOP)

    def test_out_of_order_input_enters_hold(self) -> None:
        safety = TeleopSafetyStateMachine()
        safety.enable()
        safety.update(1.0, 1.0, deadman=True, clutch=False)
        result = safety.update(1.01, 0.99, deadman=True, clutch=False)
        self.assertEqual(result.state, TeleopState.HOLD)
        self.assertTrue(result.fault_bits & int(SafetyFault.TIMESTAMP_ORDER))

    def test_future_timestamp_enters_hold(self) -> None:
        safety = TeleopSafetyStateMachine()
        safety.enable()
        result = safety.update(0.0, 1000.0, deadman=True, clutch=False)
        self.assertEqual(result.state, TeleopState.HOLD)
        self.assertTrue(result.fault_bits & int(SafetyFault.TIMESTAMP_ORDER))
        self.assertEqual(result.reason, "input timestamp is in the future")

    def test_invalid_or_out_of_order_controls_cannot_rearm(self) -> None:
        for invalid_kind in ("invalid", "out_of_order"):
            with self.subTest(invalid_kind=invalid_kind):
                safety = TeleopSafetyStateMachine()
                safety.enable()
                safety.update(1.0, 1.0, deadman=True, clutch=False)
                if invalid_kind == "invalid":
                    held = safety.update(
                        1.01,
                        1.01,
                        deadman=False,
                        clutch=False,
                        validity_flags=0,
                    )
                else:
                    held = safety.update(
                        1.01,
                        0.99,
                        deadman=False,
                        clutch=False,
                    )
                self.assertEqual(held.state, TeleopState.HOLD)
                still_held = safety.update(
                    1.02, 1.02, deadman=True, clutch=False
                )
                self.assertEqual(still_held.state, TeleopState.HOLD)
                self.assertEqual(still_held.reason, "rearm required")
                safety.update(1.03, 1.03, deadman=False, clutch=False)
                self.assertEqual(
                    safety.update(1.04, 1.04, deadman=True, clutch=False).state,
                    TeleopState.TELEOP,
                )

    def test_clutch_can_supply_rearm_cycle(self) -> None:
        safety = TeleopSafetyStateMachine()
        safety.enable()
        safety.update(0.0, 0.0, deadman=True, clutch=False)
        self.assertEqual(
            safety.update(0.01, 0.01, deadman=True, clutch=True).state,
            TeleopState.HOLD,
        )
        self.assertEqual(
            safety.update(0.02, 0.02, deadman=True, clutch=False).state,
            TeleopState.TELEOP,
        )

    def test_feedback_and_tracking_faults_require_rearm(self) -> None:
        safety = TeleopSafetyStateMachine()
        safety.enable()
        safety.update(0.0, 0.0, deadman=True, clutch=False)
        feedback_hold = safety.update(
            0.01,
            0.01,
            deadman=True,
            clutch=False,
            feedback_fresh=False,
        )
        self.assertEqual(feedback_hold.state, TeleopState.HOLD)
        self.assertTrue(
            feedback_hold.fault_bits & int(SafetyFault.FEEDBACK_TIMEOUT)
        )
        safety.update(0.02, 0.02, deadman=False, clutch=False)
        self.assertEqual(
            safety.update(0.03, 0.03, deadman=True, clutch=False).state,
            TeleopState.TELEOP,
        )
        tracking_hold = safety.update(
            0.04,
            0.04,
            deadman=True,
            clutch=False,
            tracking_ok=False,
        )
        self.assertTrue(
            tracking_hold.fault_bits & int(SafetyFault.TRACKING_ERROR)
        )

    def test_rearm_during_active_fault_is_not_queued(self) -> None:
        safety = TeleopSafetyStateMachine()
        safety.enable()
        safety.update(0.0, 0.0, deadman=True, clutch=False)
        safety.update(
            0.01,
            0.01,
            deadman=True,
            clutch=False,
            feedback_fresh=False,
        )
        safety.update(
            0.02,
            0.02,
            deadman=False,
            clutch=False,
            feedback_fresh=False,
        )
        safety.update(
            0.03,
            0.03,
            deadman=True,
            clutch=False,
            feedback_fresh=False,
        )

        recovered = safety.update(
            0.04,
            0.04,
            deadman=True,
            clutch=False,
            feedback_fresh=True,
        )
        self.assertEqual(recovered.state, TeleopState.HOLD)
        self.assertEqual(recovered.reason, "rearm required")
        safety.update(0.05, 0.05, deadman=False, clutch=False)
        self.assertEqual(
            safety.update(0.06, 0.06, deadman=True, clutch=False).state,
            TeleopState.TELEOP,
        )

    def test_fault_is_latched_until_clear_and_fresh_rearm(self) -> None:
        safety = TeleopSafetyStateMachine()
        safety.enable()
        faulted = safety.fault("internal test fault")
        self.assertEqual(faulted.state, TeleopState.FAULT)
        self.assertEqual(
            safety.update(0.0, 0.0, deadman=False, clutch=False).state,
            TeleopState.FAULT,
        )
        safety.clear_fault()
        self.assertEqual(
            safety.update(0.01, 0.01, deadman=True, clutch=False).state,
            TeleopState.HOLD,
        )
        safety.update(0.02, 0.02, deadman=False, clutch=False)
        self.assertEqual(
            safety.update(0.03, 0.03, deadman=True, clutch=False).state,
            TeleopState.TELEOP,
        )


class MockPlantFaultTests(unittest.TestCase):
    def test_targets_are_clipped_and_positions_remain_bounded(self) -> None:
        plant = MockJointPlant(config=one_joint_config())
        self.assertTrue(plant.set_target(np.array([2.0])))
        self.assertTrue(plant.last_command_was_clipped)
        for _ in range(500):
            state = plant.step(0.01)
        self.assertLessEqual(state.positions[0], 0.5)
        self.assertAlmostEqual(state.target_positions[0], 0.5)

    def test_stuck_joint_does_not_move(self) -> None:
        config = PlantConfig(
            lower_limits=np.array([-1.0, -1.0]),
            upper_limits=np.array([1.0, 1.0]),
            velocity_limits=1.0,
            acceleration_limits=4.0,
            jerk_limits=40.0,
        )
        plant = MockJointPlant(
            config=config,
            faults=FaultConfig(stuck_joints=(0,)),
        )
        plant.set_target(np.array([0.5, 0.5]))
        for _ in range(100):
            state = plant.step(0.01)
        self.assertAlmostEqual(state.positions[0], 0.0)
        self.assertGreater(state.positions[1], 0.1)

    def test_normal_motion_respects_velocity_acceleration_and_jerk(self) -> None:
        plant = MockJointPlant(config=one_joint_config())
        plant.set_target(np.array([0.4]))
        previous_acceleration = plant.accelerations.copy()
        for _ in range(300):
            state = plant.step(0.01)
            self.assertLessEqual(abs(state.velocities[0]), 1.0 + 1e-12)
            self.assertLessEqual(abs(state.accelerations[0]), 4.0 + 1e-12)
            jerk = abs(state.accelerations[0] - previous_acceleration[0]) / 0.01
            self.assertLessEqual(jerk, 40.0 + 1e-9)
            previous_acceleration = state.accelerations.copy()

    def test_timestamp_jump_does_not_expand_the_dynamics_step(self) -> None:
        plant = MockJointPlant(config=one_joint_config())
        plant.set_target(np.array([0.4]))

        state = plant.step(0.01, timestamp=0.2)

        self.assertAlmostEqual(state.timestamp, 0.2)
        self.assertAlmostEqual(state.accelerations[0], 0.4, places=12)
        self.assertAlmostEqual(state.velocities[0], 0.004, places=12)
        self.assertAlmostEqual(state.positions[0], 0.00004, places=12)

    def test_delayed_command_slot_keeps_only_latest_value(self) -> None:
        plant = MockJointPlant(
            config=one_joint_config(),
            faults=FaultConfig(command_delay=0.08),
        )
        plant.set_target(np.array([0.2]), timestamp=0.0)
        plant.set_target(np.array([0.4]), timestamp=0.02)
        state = plant.step(0.071)
        self.assertAlmostEqual(state.target_positions[0], 0.0)
        state = plant.step(0.01)
        self.assertAlmostEqual(state.target_positions[0], 0.4)
        self.assertFalse(plant.has_pending_command)

    def test_full_command_dropout_preserves_target(self) -> None:
        plant = MockJointPlant(
            config=one_joint_config(),
            faults=FaultConfig(command_drop_probability=1.0),
        )
        self.assertFalse(plant.set_target(np.array([0.4])))
        self.assertAlmostEqual(plant.target_positions[0], 0.0)
        self.assertEqual(plant.dropped_command_count, 1)

    def test_feedback_freeze_returns_same_sample_while_plant_moves(self) -> None:
        plant = MockJointPlant(
            config=one_joint_config(),
            faults=FaultConfig(feedback_frozen=True),
        )
        first = plant.feedback()
        plant.set_target(np.array([0.4]))
        for _ in range(20):
            plant.step(0.01)
        second = plant.feedback()
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        np.testing.assert_array_equal(first.positions, second.positions)
        self.assertEqual(first.timestamp, second.timestamp)


class OpenRSTFaultBoundaryTests(unittest.TestCase):
    def test_pitch_yaw_axes_and_signs_match_the_declared_tool_frames(self) -> None:
        model = IdealOpenRSTModel()
        pitch = np.deg2rad(30.0)
        yaw = np.deg2rad(-40.0)
        model.set_command(pitch, yaw, 0.5)
        state = model.forward(Pose.identity())

        expected_rotation = (
            Rotation.from_rotvec([0.0, pitch, 0.0]).as_matrix()
            @ Rotation.from_rotvec([0.0, 0.0, yaw]).as_matrix()
        )
        np.testing.assert_allclose(
            state.tcp_pose.as_matrix()[:3, :3], expected_rotation, atol=1e-12
        )
        np.testing.assert_allclose(
            state.tcp_pose.position,
            expected_rotation @ np.array([0.0, 0.0, model.geometry.shaft_length]),
            atol=1e-12,
        )

        model.set_command(pitch, 0.0, 0.0)
        positive_pitch = model.forward(Pose.identity()).tcp_pose.position[0]
        model.set_command(-pitch, 0.0, 0.0)
        negative_pitch = model.forward(Pose.identity()).tcp_pose.position[0]
        self.assertGreater(positive_pitch, 0.0)
        self.assertLess(negative_pitch, 0.0)

    def test_pitch_yaw_grasp_validation_grid(self) -> None:
        model = IdealOpenRSTModel()
        flange = Pose.identity()
        angles = np.deg2rad([0.0, -30.0, 30.0, -60.0, 60.0])
        for pitch in angles:
            for yaw in angles:
                with self.subTest(pitch=pitch, yaw=yaw):
                    tcp_transforms = []
                    jaw_distances = []
                    for grasp in (0.0, 0.5, 1.0):
                        model.set_command(float(pitch), float(yaw), grasp)
                        state = model.forward(flange)
                        tcp_transforms.append(state.tcp_pose.as_matrix())
                        jaw_distances.append(
                            float(
                                np.linalg.norm(
                                    state.left_jaw_tip - state.right_jaw_tip
                                )
                            )
                        )
                    np.testing.assert_allclose(
                        tcp_transforms[0], tcp_transforms[1], atol=1e-12
                    )
                    np.testing.assert_allclose(
                        tcp_transforms[1], tcp_transforms[2], atol=1e-12
                    )
                    self.assertLess(jaw_distances[0], jaw_distances[1])
                    self.assertLess(jaw_distances[1], jaw_distances[2])

    def test_grasp_does_not_move_stable_tcp(self) -> None:
        model = IdealOpenRSTModel()
        flange = Pose.identity()
        model.set_command(np.deg2rad(30.0), np.deg2rad(-20.0), 0.0)
        closed = model.forward(flange)
        model.set_command(np.deg2rad(30.0), np.deg2rad(-20.0), 1.0)
        opened = model.forward(flange)
        np.testing.assert_allclose(
            closed.tcp_pose.as_matrix(),
            opened.tcp_pose.as_matrix(),
            atol=1e-12,
        )
        self.assertGreater(
            np.linalg.norm(opened.left_jaw_tip - opened.right_jaw_tip),
            np.linalg.norm(closed.left_jaw_tip - closed.right_jaw_tip),
        )

    def test_tool_commands_are_clamped_to_ideal_limits(self) -> None:
        model = IdealOpenRSTModel()
        model.set_command(10.0, -10.0, 2.0)
        self.assertTrue(model.last_command_was_clipped)
        self.assertAlmostEqual(model.pitch, np.pi / 2.0)
        self.assertAlmostEqual(model.yaw, -np.pi / 2.0)
        self.assertAlmostEqual(model.grasp, 1.0)


if __name__ == "__main__":
    unittest.main()
