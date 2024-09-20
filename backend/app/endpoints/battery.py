from app.util.platform_adapters import get_battery_voltage as read_battery_voltage
from quart import Blueprint, jsonify

battery_bp = Blueprint("battery_voltage", __name__)


@battery_bp.route("/api/battery-status", methods=["GET"])
async def get_battery_voltage():
    value: float = read_battery_voltage()
    return jsonify({"voltage": value})
