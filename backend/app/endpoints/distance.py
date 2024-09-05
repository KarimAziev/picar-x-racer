from typing import TYPE_CHECKING

from flask import Blueprint, current_app, jsonify

distance_bp = Blueprint("distance", __name__)

if TYPE_CHECKING:
    from app.controllers.car_controller import CarController


@distance_bp.route("/api/get-distance", methods=["GET"])
async def get_ultrasonic_distance():
    car_manager: "CarController" = current_app.config["car_manager"]
    value: float = await car_manager.px.get_distance()
    return jsonify({"distance": value})
