"""Windows-native offline teleoperation simulation primitives."""

from .hardware_mapping import (
    DUMMY_JOINT_NAMES,
    SAFE_JOINT_LIMITS_DEG,
    SAFE_JOINT_LIMITS_RAD,
    clamp_to_safe_limits,
    hardware_degrees_to_ros,
    require_safe_joints,
    ros_to_hardware_degrees,
    within_safe_limits,
)
from .ik_solver import BoundedIKSolver, IKResult
from .kinematics import (
    SerialKinematics,
    create_dummy_kinematics,
    matrix_to_pose,
    pose_to_matrix,
    rotation_error_vector,
)
from .types import MasterState, Pose, RobotState, TeleopState, TeleopStatus
from .mock_plant import FaultConfig, MockJointPlant, PlantConfig, PlantState
from .motion_filter import OneEuroFilter, OneEuroPoseFilter, PoseRateLimiter
from .openrst_model import (
    IdealOpenRSTModel,
    OpenRSTGeometry,
    OpenRSTKinematicState,
    OpenRSTModel,
)
from .teleop_mapper import (
    SafetyFault,
    SafetySnapshot,
    TeleopMapper,
    TeleopSafetyStateMachine,
)
from .signal_analysis import MultiToneAnalyzer, wrapped_phase_difference
from .urdf_model import (
    Joint,
    JointLimit,
    URDFModel,
    default_dummy_urdf_path,
    default_openrst_urdf_path,
    load_dummy_urdf,
    load_openrst_urdf,
    parse_urdf,
)

__all__ = [
    "BoundedIKSolver",
    "DUMMY_JOINT_NAMES",
    "IKResult",
    "IdealOpenRSTModel",
    "Joint",
    "JointLimit",
    "MasterState",
    "MockJointPlant",
    "MultiToneAnalyzer",
    "OneEuroFilter",
    "OneEuroPoseFilter",
    "OpenRSTGeometry",
    "OpenRSTKinematicState",
    "OpenRSTModel",
    "PlantConfig",
    "PlantState",
    "Pose",
    "RobotState",
    "SAFE_JOINT_LIMITS_DEG",
    "SAFE_JOINT_LIMITS_RAD",
    "SerialKinematics",
    "SafetyFault",
    "SafetySnapshot",
    "TeleopMapper",
    "TeleopSafetyStateMachine",
    "TeleopState",
    "TeleopStatus",
    "URDFModel",
    "clamp_to_safe_limits",
    "create_dummy_kinematics",
    "default_dummy_urdf_path",
    "default_openrst_urdf_path",
    "hardware_degrees_to_ros",
    "load_dummy_urdf",
    "load_openrst_urdf",
    "matrix_to_pose",
    "parse_urdf",
    "pose_to_matrix",
    "PoseRateLimiter",
    "require_safe_joints",
    "ros_to_hardware_degrees",
    "rotation_error_vector",
    "within_safe_limits",
    "wrapped_phase_difference",
    "FaultConfig",
]
