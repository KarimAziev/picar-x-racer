from flask import Blueprint, jsonify
from util.platform_adapters import get_battery_voltage as read_battery_voltage


battery_bp = Blueprint("battery_voltage", __name__)


@battery_bp.route("/api/battery-status", methods=["GET"])
def get_battery_voltage():
    value: float = read_battery_voltage()
    return jsonify({"voltage": value})
