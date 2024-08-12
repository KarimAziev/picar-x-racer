#!/usr/bin/env python3

import threading

from video_car_controller import VideoCarController, run_flask

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
            controller.Vilib.camera_close()
