from app.util.video_enhancers import (
    simulate_infrared_vision,
    simulate_predator_vision,
    simulate_robocop_vision,
    simulate_ultrasonic_vision,
)

frame_enhancers = {
    "robocop_vision": simulate_robocop_vision,
    "simulate_predator_vision": simulate_predator_vision,
    "simulate_infrared_vision": simulate_infrared_vision,
    "simulate_ultrasonic_vision": simulate_ultrasonic_vision,
}
