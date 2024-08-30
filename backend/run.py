import threading

from app.controllers.video_car_controller import VideoCarController
from app.controllers.video_stream import VideoStreamManager
from app.endpoints.flask_setup import run_flask

video_stream_manager = VideoStreamManager()

if __name__ == "__main__":
    controller = None
    try:

        controller = VideoCarController(video_manager=video_stream_manager)
        flask_thread = threading.Thread(
            target=run_flask, args=(controller, video_stream_manager)
        )
        flask_thread.daemon = True
        flask_thread.start()
        controller.main()
    except Exception as e:
        print(f"error: {e}")
    finally:
        video_stream_manager.camera_close()
