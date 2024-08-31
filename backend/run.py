import threading
from app.controllers.video_car_controller import VideoCarController
from app.controllers.video_stream import VideoStreamManager
from app.endpoints.flask_setup import run_flask

from os import path, makedirs
import shutil
from app.config.paths import PICARX_CONFIG_FILE, PICARX_OLD_CONFIG_FILE


if path.exists(PICARX_OLD_CONFIG_FILE) and not path.exists(PICARX_CONFIG_FILE):
    dir = path.dirname(PICARX_CONFIG_FILE)
    if not path.exists(dir):
        makedirs(dir)
    print(f"copying {PICARX_OLD_CONFIG_FILE} to {PICARX_CONFIG_FILE}")
    shutil.copyfile(PICARX_OLD_CONFIG_FILE, PICARX_CONFIG_FILE)


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
