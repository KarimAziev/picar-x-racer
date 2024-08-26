import threading
from app.controllers.video_car_controller import VideoCarController
from app.endpoints.flask_setup import run_flask
from app.util.platform_adapters import Vilib

if __name__ == "__main__":
    controller = None
    try:
        controller = VideoCarController()
        flask_thread = threading.Thread(target=run_flask, args=(controller,))
        flask_thread.daemon = True
        flask_thread.start()
        controller.main()
    except Exception as e:
        print(f"error: {e}")
    finally:
        if controller is not None:
            controller.px.stop()
            Vilib.camera_close()
