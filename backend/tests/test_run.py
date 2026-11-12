import unittest
from unittest.mock import Mock, patch

import run


class TestServerSupervision(unittest.TestCase):
    def run_launcher(self, main_exitcode, control_exitcode):
        main_process = Mock(name="main process")
        main_process.name = "px_main_server"
        main_process.exitcode = main_exitcode
        control_process = Mock(name="control process")
        control_process.name = "px_control_server"
        control_process.exitcode = control_exitcode
        with patch(
            "multiprocessing.Process", side_effect=[main_process, control_process]
        ), patch(
            "app.util.setup_env.setup_env",
            return_value=(8000, 8001, "INFO", "prod", 5173),
        ), patch(
            "run.os.path.exists", return_value=False
        ), patch(
            "run.time.sleep", side_effect=[None, KeyboardInterrupt]
        ), patch(
            "run.terminate_processes"
        ) as terminate:
            try:
                run.main()
            finally:
                terminate.assert_called_once_with([control_process, main_process])

    def test_native_web_server_crash_exits_launcher_with_failure(self):
        with self.assertRaises(SystemExit) as raised:
            self.run_launcher(-6, None)
        self.assertEqual(raised.exception.code, 1)

    def test_control_server_exit_exits_launcher_with_failure(self):
        with self.assertRaises(SystemExit) as raised:
            self.run_launcher(None, 1)
        self.assertEqual(raised.exception.code, 1)

    def test_unexpected_clean_server_exit_is_a_failure(self):
        with self.assertRaises(SystemExit):
            self.run_launcher(0, None)

    def test_running_servers_remain_alive_until_interrupt(self):
        self.run_launcher(None, None)
