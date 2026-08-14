"""
Forward kinematics for Dummy 6-DOF robot arm.

Parameters extracted from URDF (dummy.urdf).
FK chain handled by Ursina's scene-graph hierarchy.

Each link entity is a child of the previous link.
  - local position = joint origin (from URDF)
  - local rotation = axis * angle (degrees)
  - mesh child at visual offset
"""

JOINT_DEFS = [
    # (name, parent_idx, origin_x, origin_y, origin_z, axis_x, axis_y, axis_z, vis_x, vis_y, vis_z)
    ("Joint1", -1,  -0.015, -0.079017, 0.0825,   0, 0, 1,    0.0, 0.0, 0.0),
    ("Joint2",  0,  -0.017, -0.035,    0.0375,   1, 0, 0,    0.0, -0.017517, 0.005),
    ("Joint3",  1,   0.032,  0.0,       0.146,    1, 0, 0,   -0.0,  0.114017, -0.266),
    ("Joint4",  2,  -0.017, -0.0175,   0.052,    0,-1, 0,    0.017, 0.131517, -0.318),
    ("Joint5",  3,  -0.0176,-0.1025,   0.0,     -1, 0, 0,    0.0346,0.234017, -0.318),
    ("Joint6",  4,   0.0186,-0.0565,   0.0,      0, 1, 0,    0.016, 0.290517, -0.318),
]

MESH_FILES = [
    "meshes/link1_1_1.glb",
    "meshes/link2_1_1.glb",
    "meshes/link3_1_1.glb",
    "meshes/link4_1_1.glb",
    "meshes/link5_1_1.glb",
    "meshes/link6_1_1.glb",
]


def get_link_transforms(joint_angles_deg):
    """Compute per-link local position/rotation for Ursina entities.

    Returns list of (local_pos, local_euler_deg, visual_offset).
    """
    result = []
    for i, (name, parent, ox, oy, oz, ax, ay, az, vx, vy, vz) in enumerate(JOINT_DEFS):
        angle = joint_angles_deg[i]
        pos = (ox, oy, oz)
        rot = (ax * angle, ay * angle, az * angle)
        vis = (vx, vy, vz)
        result.append((pos, rot, vis))
    return result
