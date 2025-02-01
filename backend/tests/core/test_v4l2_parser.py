import unittest

from app.core.v4l2_parser import V4L2FormatParser
from app.schemas.camera import DeviceStepwiseBase, DiscreteDevice


class TestV4L2FormatParser(unittest.TestCase):

    def setUp(self):
        self.device = "/dev/video0"
        self.parser = V4L2FormatParser(self.device)

    def test_parse_discrete_resolution(self):
        """
        Test parsing of `v4l2-ctl --list-formats-ext` output with discrete resolutions.
        """
        v4l2_output = (
            "ioctl: VIDIOC_ENUM_FMT\n"
            "    Type: Video Capture\n\n"
            "    [0]: 'GREY' (8-bit Greyscale)\n"
            "        Size: Discrete 640x360\n"
            "            Interval: Discrete 0.067s (15.000 fps)\n"
            "            Interval: Discrete 0.033s (30.000 fps)\n"
        )

        expected_result = [
            {
                "device": "/dev/video2",
                "width": 640,
                "height": 360,
                "pixel_format": "GREY",
                "fps": 15,
                "name": None,
            },
            {
                "device": "/dev/video2",
                "width": 640,
                "height": 360,
                "pixel_format": "GREY",
                "fps": 30,
                "name": None,
            },
        ]

        result = V4L2FormatParser("/dev/video2").parse(v4l2_output)
        self.assertEqual(result, [DiscreteDevice(**item) for item in expected_result])

    def test_parse_multi_discrete_formats(self):
        output = (
            "ioctl: VIDIOC_ENUM_FMT\n"
            "	Type: Video Capture\n"
            "\n"
            "	[0]: 'MJPG' (Motion-JPEG, compressed)\n"
            "		Size: Discrete 1920x1080\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 320x180\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 320x240\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 352x288\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 424x240\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 640x360\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 640x480\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 848x480\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 960x540\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 1280x720\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "	[1]: 'YUYV' (YUYV 4:2:2)\n"
            "		Size: Discrete 640x480\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 320x180\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 320x240\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 352x288\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 424x240\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 640x360\n"
            "			Interval: Discrete 0.033s (30.000 fps)\n"
            "		Size: Discrete 848x480\n"
            "			Interval: Discrete 0.050s (20.000 fps)\n"
            "		Size: Discrete 960x540\n"
            "			Interval: Discrete 0.067s (15.000 fps)\n"
            "		Size: Discrete 1280x720\n"
            "			Interval: Discrete 0.100s (10.000 fps)\n"
            "		Size: Discrete 1920x1080\n"
            "			Interval: Discrete 0.200s (5.000 fps)\n"
        )
        result = self.parser.parse(output)

        self.assertEqual(
            result,
            [
                DiscreteDevice(**item)
                for item in [
                    {
                        "device": "/dev/video0",
                        "width": 1920,
                        "height": 1080,
                        "pixel_format": "MJPG",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 320,
                        "height": 180,
                        "pixel_format": "MJPG",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 320,
                        "height": 240,
                        "pixel_format": "MJPG",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 352,
                        "height": 288,
                        "pixel_format": "MJPG",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 424,
                        "height": 240,
                        "pixel_format": "MJPG",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 640,
                        "height": 360,
                        "pixel_format": "MJPG",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 640,
                        "height": 480,
                        "pixel_format": "MJPG",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 848,
                        "height": 480,
                        "pixel_format": "MJPG",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 960,
                        "height": 540,
                        "pixel_format": "MJPG",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 1280,
                        "height": 720,
                        "pixel_format": "MJPG",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 640,
                        "height": 480,
                        "pixel_format": "YUYV",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 320,
                        "height": 180,
                        "pixel_format": "YUYV",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 320,
                        "height": 240,
                        "pixel_format": "YUYV",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 352,
                        "height": 288,
                        "pixel_format": "YUYV",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 424,
                        "height": 240,
                        "pixel_format": "YUYV",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 640,
                        "height": 360,
                        "pixel_format": "YUYV",
                        "fps": 30,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 848,
                        "height": 480,
                        "pixel_format": "YUYV",
                        "fps": 20,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 960,
                        "height": 540,
                        "pixel_format": "YUYV",
                        "fps": 15,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 1280,
                        "height": 720,
                        "pixel_format": "YUYV",
                        "fps": 10,
                    },
                    {
                        "device": "/dev/video0",
                        "width": 1920,
                        "height": 1080,
                        "pixel_format": "YUYV",
                        "fps": 5,
                    },
                ]
            ],
        )

    def test_parse_stepwise_formats(self):
        output = (
            "ioctl: VIDIOC_ENUM_FMT\n"
            "	Type: Video Capture\n"
            "\n"
            "	[0]: 'YU12' (Planar YUV 4:2:0)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[1]: 'YUYV' (YUYV 4:2:2)\n"
            "		Size: Stepwise 64x64 - 2492x1844 with step 2/2\n"
            "	[2]: 'RGB3' (24-bit RGB 8-8-8)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[3]: 'JPEG' (JFIF JPEG, compressed)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[4]: 'H264' (H.264, compressed)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[5]: 'MJPG' (Motion-JPEG, compressed)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[6]: 'YVYU' (YVYU 4:2:2)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[7]: 'VYUY' (VYUY 4:2:2)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[8]: 'UYVY' (UYVY 4:2:2)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[9]: 'NV12' (Y/UV 4:2:0)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[10]: 'BGR3' (24-bit BGR 8-8-8)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[11]: 'YV12' (Planar YVU 4:2:0)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[12]: 'NV21' (Y/VU 4:2:0)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "	[13]: 'RX24' (32-bit XBGR 8-8-8-8)\n"
            "		Size: Stepwise 32x32 - 2592x1944 with step 2/2\n"
            "\n"
        )
        result = self.parser.parse(output)

        self.assertEqual(
            result,
            [
                DeviceStepwiseBase(**item)
                for item in [
                    {
                        "device": "/dev/video0",
                        "pixel_format": "YU12",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "YUYV",
                        "min_width": 64,
                        "max_width": 2492,
                        "min_height": 64,
                        "max_height": 1844,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "RGB3",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "JPEG",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "H264",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "MJPG",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "YVYU",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "VYUY",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "UYVY",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "NV12",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "BGR3",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "YV12",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "NV21",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                    {
                        "device": "/dev/video0",
                        "pixel_format": "RX24",
                        "min_width": 32,
                        "max_width": 2592,
                        "min_height": 32,
                        "max_height": 1944,
                        "width_step": 2,
                        "height_step": 2,
                    },
                ]
            ],
        )

    def test_parse_empty_output(self):
        """
        Test that an empty output results in an empty list of formats.
        """
        v4l2_output = ""
        result = self.parser.parse(v4l2_output)
        self.assertEqual(result, [])

    def test_parse_invalid_output(self):
        """
        Test that invalid or unexpected output does not raise an exception but results in an empty list.
        """
        v4l2_output = "Invalid Output"
        result = self.parser.parse(v4l2_output)
        self.assertEqual(result, [])

    def test_parse_frameinterval_continuous(self):
        """
        Test parsing of `ioctl: VIDIOC_ENUM_FRAMEINTERVALS` output for continuous intervals.
        """
        frameinterval_output = (
            "ioctl: VIDIOC_ENUM_FRAMEINTERVALS\n"
            "        Interval: Continuous 0.011s - 1.000s (1.000-90.000 fps)"
        )
        expected_result = (1, 90)
        result = V4L2FormatParser.parse_frameinterval(frameinterval_output)
        self.assertEqual(result, expected_result)

    def test_parse_frameinterval_discrete(self):
        """
        Test parsing of `ioctl: VIDIOC_ENUM_FRAMEINTERVALS` output for discrete intervals.
        """
        frameinterval_output = (
            "ioctl: VIDIOC_ENUM_FRAMEINTERVALS\n"
            "        Interval: Discrete 0.033s (30.000 fps)"
        )
        expected_result = (30, 30)
        result = V4L2FormatParser.parse_frameinterval(frameinterval_output)
        self.assertEqual(result, expected_result)

    def test_parse_frameinterval_invalid(self):
        """
        Test parsing of invalid or unexpected `ioctl: VIDIOC_ENUM_FRAMEINTERVALS` output.
        """
        frameinterval_output = "Invalid Output"
        result = V4L2FormatParser.parse_frameinterval(frameinterval_output)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
