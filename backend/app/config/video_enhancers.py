from app.util.video_enhancers import (
    preprocess_frame,
    preprocess_frame_clahe,
    preprocess_frame_combined,
    preprocess_frame_edge_enhancement,
    preprocess_frame_ycrcb,
    simulate_infrared_vision,
    simulate_predator_vision,
    simulate_robocop_vision,
    simulate_robocop_vision_targeting,
    simulate_ultrasonic_vision,
)

frame_enhancers = {
    "preprocess_frame": preprocess_frame,
    "preprocess_frame_clahe": preprocess_frame_clahe,
    "preprocess_frame_combined": preprocess_frame_combined,
    "preprocess_frame_edge_enhancement": preprocess_frame_edge_enhancement,
    "preprocess_frame_ycrcb": preprocess_frame_ycrcb,
    "robocop_vision": simulate_robocop_vision,
    "simulate_predator_vision": simulate_predator_vision,
    "simulate_infrared_vision": simulate_infrared_vision,
    "simulate_ultrasonic_vision": simulate_ultrasonic_vision,
    "simulate_robocop_vision_targeting": simulate_robocop_vision_targeting,
}
