import os
import sys
import unittest
from unittest.mock import patch

from app.util import setup_env


class TestSetupEnvVars(unittest.TestCase):
    def setUp(self):
        keys = [
            "GPIOZERO_PIN_FACTORY",
            "PYGAME_HIDE_SUPPORT_PROMPT",
            "ROBOT_HAT_MOCK_SMBUS",
            "ROBOT_HAT_DISCHARGE_RATE",
        ]
        for key in keys:
            os.environ.pop(key, None)

    @patch("app.util.setup_env.get_gpio_factory_name", return_value="mock")
    def test_setup_env_vars_without_gpio_set_returns_false_mock(self, _):
        """
        When GPIOZERO_PIN_FACTORY is not defined, and get_gpio_factory_name returns "mock",
        it should consider that it's not a real Raspberry Pi.
        """
        is_real = setup_env.setup_env_vars()
        self.assertEqual(os.environ.get("GPIOZERO_PIN_FACTORY"), "mock")
        self.assertEqual(os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT"), "1")
        self.assertEqual(os.environ.get("ROBOT_HAT_MOCK_SMBUS"), "1")
        self.assertEqual(os.environ.get("ROBOT_HAT_DISCHARGE_RATE"), "10")
        self.assertFalse(is_real)

    @patch("app.util.setup_env.get_gpio_factory_name", return_value="real")
    def test_setup_env_vars_without_gpio_set_returns_true_real(self, _):
        """
        When get_gpio_factory_name returns a value other than "mock", the result should be True.
        """
        is_real = setup_env.setup_env_vars()
        self.assertEqual(os.environ.get("GPIOZERO_PIN_FACTORY"), "real")
        self.assertEqual(os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT"), "1")

        self.assertIsNone(os.environ.get("ROBOT_HAT_MOCK_SMBUS"))
        self.assertIsNone(os.environ.get("ROBOT_HAT_DISCHARGE_RATE"))
        self.assertTrue(is_real)

    @patch("app.util.setup_env.is_raspberry_pi", return_value=True)
    def test_setup_env_vars_when_gpio_already_set(self, _):
        """
        If GPIOZERO_PIN_FACTORY is already set, then is_raspberry_pi() is used.
        """
        os.environ["GPIOZERO_PIN_FACTORY"] = "anything"
        is_real = setup_env.setup_env_vars()
        self.assertTrue(is_real)
        self.assertEqual(os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT"), "1")
        self.assertIsNone(os.environ.get("ROBOT_HAT_MOCK_SMBUS"))
        self.assertIsNone(os.environ.get("ROBOT_HAT_DISCHARGE_RATE"))

    @patch("app.util.setup_env.is_raspberry_pi", return_value=False)
    def test_setup_env_vars_when_gpio_already_set_and_not_rpi(self, _):
        os.environ["GPIOZERO_PIN_FACTORY"] = "anything"
        is_real = setup_env.setup_env_vars()
        self.assertFalse(is_real)
        self.assertEqual(os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT"), "1")
        self.assertEqual(os.environ.get("ROBOT_HAT_MOCK_SMBUS"), "1")
        self.assertEqual(os.environ.get("ROBOT_HAT_DISCHARGE_RATE"), "10")


class TestParseCliArgs(unittest.TestCase):
    def setUp(self):
        self.orig_environ = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_environ)

    def test_parse_cli_args_defaults(self):
        """
        Set environment variables that affect defaults.
        """
        with patch.object(sys, "argv", ["prog"]):
            os.environ["PX_LOG_LEVEL"] = "WARNING"
            os.environ["PX_MAIN_APP_PORT"] = "8080"
            os.environ["PX_CONTROL_APP_PORT"] = "8081"
            args = setup_env.parse_cli_args()
        self.assertFalse(args.debug)
        self.assertEqual(args.log_level, "WARNING")
        self.assertFalse(args.dev)
        self.assertEqual(args.port, 8080)
        self.assertEqual(args.px_port, 8081)
        self.assertEqual(args.frontend_port, 4000)

    def test_parse_cli_args_with_arguments(self):
        test_argv = [
            "prog",
            "--debug",
            "--dev",
            "--port",
            "9000",
            "--px-port",
            "9001",
            "--frontend-port",
            "5000",
        ]
        with patch.object(sys, "argv", test_argv):
            for var in ["PX_LOG_LEVEL", "PX_MAIN_APP_PORT", "PX_CONTROL_APP_PORT"]:
                os.environ.pop(var, None)
            args = setup_env.parse_cli_args()
        self.assertTrue(args.debug)
        self.assertEqual(args.log_level, "INFO")
        self.assertTrue(args.dev)
        self.assertEqual(args.port, 9000)
        self.assertEqual(args.px_port, 9001)
        self.assertEqual(args.frontend_port, 5000)

    def test_mutually_exclusive_log_options(self):
        """
        Test that providing both --debug and --log-level arguments should cause the parser to exit.
        """
        test_argv = [
            "prog",
            "--debug",
            "--log-level",
            "ERROR",
        ]
        with patch.object(sys, "argv", test_argv):
            with self.assertRaises(SystemExit):
                setup_env.parse_cli_args()


class TestSetupEnv(unittest.TestCase):
    def setUp(self):
        for key in [
            "PX_LOG_LEVEL",
            "PX_CONTROL_APP_PORT",
            "PX_MAIN_APP_PORT",
            "PX_APP_MODE",
        ]:
            os.environ.pop(key, None)

    def tearDown(self):
        for key in [
            "PX_LOG_LEVEL",
            "PX_CONTROL_APP_PORT",
            "PX_MAIN_APP_PORT",
            "PX_APP_MODE",
        ]:
            os.environ.pop(key, None)

    def test_setup_env_defaults(self):
        """
        Test setup_env with no overriding CLI flags should use environment defaults.
        """
        os.environ["PX_LOG_LEVEL"] = "CRITICAL"
        os.environ["PX_MAIN_APP_PORT"] = "7000"
        os.environ["PX_CONTROL_APP_PORT"] = "7001"
        test_argv = ["prog"]
        with patch.object(sys, "argv", test_argv):
            app_env = setup_env.setup_env()
        self.assertEqual(app_env.main_app_port, "7000")
        self.assertEqual(app_env.control_app_port, "7001")
        self.assertEqual(app_env.log_level, "CRITICAL")
        self.assertEqual(app_env.mode, "prod")
        self.assertEqual(app_env.frontend_port, "4000")
        self.assertEqual(os.environ.get("PX_LOG_LEVEL"), "CRITICAL")
        self.assertEqual(os.environ.get("PX_MAIN_APP_PORT"), "7000")
        self.assertEqual(os.environ.get("PX_CONTROL_APP_PORT"), "7001")
        self.assertEqual(os.environ.get("PX_APP_MODE"), "prod")

    def test_setup_env_with_debug_and_dev(self):
        """
        Test debug level should override the log-level value, when the --debug and --dev flags are used.
        """
        test_argv = [
            "prog",
            "--debug",
            "--dev",
            "--port",
            "9100",
            "--px-port",
            "9101",
            "--frontend-port",
            "4200",
        ]
        for var in ["PX_LOG_LEVEL", "PX_MAIN_APP_PORT", "PX_CONTROL_APP_PORT"]:
            os.environ.pop(var, None)
        with patch.object(sys, "argv", test_argv):
            app_env = setup_env.setup_env()
        self.assertEqual(app_env.main_app_port, "9100")
        self.assertEqual(app_env.control_app_port, "9101")
        self.assertEqual(app_env.log_level, "DEBUG")
        self.assertEqual(app_env.mode, "dev")
        self.assertEqual(app_env.frontend_port, "4200")
        self.assertEqual(os.environ.get("PX_LOG_LEVEL"), "DEBUG")
        self.assertEqual(os.environ.get("PX_MAIN_APP_PORT"), "9100")
        self.assertEqual(os.environ.get("PX_CONTROL_APP_PORT"), "9101")
        self.assertEqual(os.environ.get("PX_APP_MODE"), "dev")

    def test_setup_env_with_log_level_specified(self):
        """
        Test setup_env with a specified log level argument overrides the default log level.
        """

        test_argv = [
            "prog",
            "--log-level",
            "ERROR",
            "--port",
            "9200",
            "--px-port",
            "9201",
            "--frontend-port",
            "4300",
        ]
        with patch.object(sys, "argv", test_argv):
            app_env = setup_env.setup_env()
        self.assertEqual(app_env.log_level, "ERROR")
        self.assertEqual(app_env.mode, "prod")
        self.assertEqual(app_env.main_app_port, "9200")
        self.assertEqual(app_env.control_app_port, "9201")
        self.assertEqual(app_env.frontend_port, "4300")
        self.assertEqual(os.environ.get("PX_LOG_LEVEL"), "ERROR")
        self.assertEqual(os.environ.get("PX_MAIN_APP_PORT"), "9200")
        self.assertEqual(os.environ.get("PX_CONTROL_APP_PORT"), "9201")
        self.assertEqual(os.environ.get("PX_APP_MODE"), "prod")


if __name__ == "__main__":
    unittest.main(buffer=True)
