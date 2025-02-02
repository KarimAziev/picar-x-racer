from app.util.video_enhancers import (
    preprocess_frame,
    preprocess_frame_clahe,
    preprocess_frame_combined,
    preprocess_frame_edge_enhancement,
    preprocess_frame_fisheye,
    preprocess_frame_soft_colors,
    preprocess_frame_ycrcb,
    simulate_infrared_vision,
    simulate_predator_vision,
    simulate_robocop_vision,
    simulate_ultrasonic_vision,
)

frame_enhancers = {
    "robocop_vision": simulate_robocop_vision,
    "soft_colors": preprocess_frame_soft_colors,
    "brightness": preprocess_frame,
    "fisheye": preprocess_frame_fisheye,
    "clahe": preprocess_frame_clahe,
    "combined": preprocess_frame_combined,
    "edge_enhancement": preprocess_frame_edge_enhancement,
    "ycrcb": preprocess_frame_ycrcb,
    "simulate_predator_vision": simulate_predator_vision,
    "simulate_infrared_vision": simulate_infrared_vision,
    "simulate_ultrasonic_vision": simulate_ultrasonic_vision,
}
