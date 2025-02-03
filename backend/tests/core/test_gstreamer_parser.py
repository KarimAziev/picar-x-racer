import unittest

from app.core.gstreamer_parser import GStreamerParser


class TestGStreamerParser(unittest.TestCase):
    def test_parse_device_path_with_api_prefix(self):
        """Test input with API prefix"""
        input_string = "v4l2:/dev/video0"
        result = GStreamerParser.parse_device_path(input_string)
        self.assertEqual(result, ("v4l2", "/dev/video0"))

    def test_parse_device_path_without_api_prefix(self):
        """Test input without API prefix."""
        input_string = "/dev/video0"
        result = GStreamerParser.parse_device_path(input_string)
        self.assertEqual(result, (None, "/dev/video0"))

    def test_parse_device_path_with_complex_path(self):
        """Test edge case with complex input path."""
        input_string = "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a"
        result = GStreamerParser.parse_device_path(input_string)
        self.assertEqual(result, ("libcamera", "/base/soc/i2c0mux/i2c@1/imx708@1a"))

    def test_parse_device_path_with_colon_path(self):
        """Test edge case with complex input path."""
        input_string = "libcamera:/base:/check"
        result = GStreamerParser.parse_device_path(input_string)
        self.assertEqual(result, ("libcamera", "/base:/check"))

    def test_parse_device_path_invalid_format(self):
        """Test input with invalid format."""
        input_string = "invalid_pattern:/"
        result = GStreamerParser.parse_device_path(input_string)
        self.assertEqual(result, ("invalid_pattern", "/"))

    def test_strip_api_prefix_with_api_prefix(self):
        """Test stripping API prefix."""
        input_string = "v4l2:/dev/video0"
        result = GStreamerParser.strip_api_prefix(input_string)
        self.assertEqual(result, "/dev/video0")

    def test_strip_api_prefix_without_api_prefix(self):
        """Test case where no API prefix is present."""
        input_string = "/dev/video0"
        result = GStreamerParser.strip_api_prefix(input_string)
        self.assertEqual(result, "/dev/video0")

    def test_strip_api_prefix_complex_path(self):
        """Test stripping API prefix for complex input."""
        input_string = "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a"
        result = GStreamerParser.strip_api_prefix(input_string)
        self.assertEqual(result, "/base/soc/i2c0mux/i2c@1/imx708@1a")

    def test_parse_framerate_single_fraction(self):
        """Test parsing single framerate."""
        struct_str = "framerate=(fraction)30/1"
        result = GStreamerParser.parse_framerate(struct_str)
        self.assertEqual(result, [30.0])

    def test_parse_framerate_two_fractions(self):
        """Test parsing two framerates enclosed in braces."""
        struct_str = "framerate=(fraction){ 15/1, 30/1 }"
        result = GStreamerParser.parse_framerate(struct_str)
        self.assertEqual(result, [30.0, 15.0])

    def test_parse_framerate_multiple_fractions(self):
        """Test parsing multiple framerates enclosed in braces."""
        struct_str = "framerate=(fraction){ 5/1, 15/1, 30/1 }"
        result = GStreamerParser.parse_framerate(struct_str)
        self.assertEqual(result, [30.0, 15.0, 5.0])

    def test_parse_framerate_curly_braces_format(self):
        """Test parsing framerate with another valid syntax format."""
        struct_str = "framerate={ (fraction)15/1, (fraction)30/1 }"
        result = GStreamerParser.parse_framerate(struct_str)
        self.assertEqual(result, [30.0, 15.0])

    def test_parse_multiple_framerate_curly_braces_format(self):
        """Test parsing framerate with multiple values in curly braces."""
        struct_str = "framerate={ (fraction)5/1, (fraction)15/1, (fraction)25/1, (fraction)30/1 }"
        result = GStreamerParser.parse_framerate(struct_str)
        self.assertEqual(result, [30.0, 25.0, 15.0, 5.0])

    def test_parse_framerate_empty_input(self):
        """Test case where there is no framerate information."""
        from unittest.mock import patch

        struct_str = "framerate=(fraction)"
        with patch("app.core.logger.Logger.warning") as mock_logger_warning:
            result = GStreamerParser.parse_framerate(struct_str)
            self.assertEqual(result, [])
            mock_logger_warning.assert_called_once()

    def test_parse_framerate_invalid_format(self):
        """Test case with an invalid format."""
        struct_str = "framerate=invalid_format"
        result = GStreamerParser.parse_framerate(struct_str)
        self.assertEqual(result, [])

    def test_parse_framerate_partial_content(self):
        """Test partially malformed input."""
        struct_str = "framerate=(fraction)30/1, invalid_content"
        result = GStreamerParser.parse_framerate(struct_str)
        self.assertEqual(result, [30.0])

    def test_parse_framerate_fraction_with_zero_denominator(self):
        """Test case where fraction has 0 denominator."""

        from unittest.mock import patch

        struct_str = "framerate=(fraction){ 30/0, 15/1 }"
        with patch("app.core.logger.Logger.error") as mock_logger_error:
            result = GStreamerParser.parse_framerate(struct_str)
            self.assertEqual(result, [15.0])
            mock_logger_error.assert_called_once()

    def test_parse_framerate_duplicates(self):
        """Test framerate input with duplicate values."""
        struct_str = "framerate={ (fraction)30/1, (fraction)30/1 }"
        result = GStreamerParser.parse_framerate(struct_str)
        self.assertEqual(result, [30.0])

    def test_parse_framerate_extra_whitespace(self):
        """Test parsing when there is extra whitespace."""
        struct_str = "framerate={   (fraction)15/1 ,   (fraction)30/1   }"
        result = GStreamerParser.parse_framerate(struct_str)
        self.assertEqual(result, [30.0, 15.0])

    def test_parse_framerate_large_fraction(self):
        """Test case where framerate fraction has very large numerator/denominator."""
        struct_str = "framerate=(fraction){ 120000/1000, 30/1 }"
        result = GStreamerParser.parse_framerate(struct_str)
        self.assertEqual(result, [120.0, 30.0])


if __name__ == "__main__":
    unittest.main()
