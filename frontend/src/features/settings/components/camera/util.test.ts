import { describe, test, expect } from "vitest";
import type { DiscreteDevice } from "@/features/settings/interface";
import {
  groupDevices,
  findAlternative,
} from "@/features/settings/components/camera/util";

const sampleDevices = [
  {
    key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
    label: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a imx708_wide",
    children: [
      {
        key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:NV21",
        label: "NV21",
        children: [
          {
            key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:NV21 640x480 video/x-raw",
            label: "NV21 640x480 video/x-raw",
            device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
            name: "imx708_wide",
            pixel_format: "NV21",
            media_type: "video/x-raw",
            api: "libcamera",
            path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
            width: 640,
            height: 480,
            fps: null,
          },
          {
            key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:NV21 160x120 video/x-raw",
            label: "NV21 160x120 video/x-raw",
            device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
            name: "imx708_wide",
            pixel_format: "NV21",
            media_type: "video/x-raw",
            api: "libcamera",
            path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
            width: 160,
            height: 120,
            fps: null,
          },
          {
            key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:NV21 240x160 video/x-raw",
            label: "NV21 240x160 video/x-raw",
            device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
            name: "imx708_wide",
            pixel_format: "NV21",
            media_type: "video/x-raw",
            api: "libcamera",
            path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
            width: 240,
            height: 160,
            fps: null,
          },
          {
            key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:NV21 320x240 video/x-raw",
            label: "NV21 320x240 video/x-raw",
            device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
            name: "imx708_wide",
            pixel_format: "NV21",
            media_type: "video/x-raw",
            api: "libcamera",
            path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
            width: 320,
            height: 240,
            fps: null,
          },
        ],
      },
      {
        key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:I420",
        label: "I420",
        children: [
          {
            key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:I420 3200x2400 video/x-raw",
            label: "I420 3200x2400 video/x-raw",
            device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
            name: "imx708_wide",
            pixel_format: "I420",
            media_type: "video/x-raw",
            api: "libcamera",
            path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
            width: 3200,
            height: 2400,
            fps: null,
          },
          {
            key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:I420 3840x2160 video/x-raw",
            label: "I420 3840x2160 video/x-raw",
            device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
            name: "imx708_wide",
            pixel_format: "I420",
            media_type: "video/x-raw",
            api: "libcamera",
            path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
            width: 3840,
            height: 2160,
            fps: null,
          },
          {
            key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:I420 4096x2160 video/x-raw",
            label: "I420 4096x2160 video/x-raw",
            device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
            name: "imx708_wide",
            pixel_format: "I420",
            media_type: "video/x-raw",
            api: "libcamera",
            path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
            width: 4096,
            height: 2160,
            fps: null,
          },
          {
            key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:I420 3840x2400 video/x-raw",
            label: "I420 3840x2400 video/x-raw",
            device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
            name: "imx708_wide",
            pixel_format: "I420",
            media_type: "video/x-raw",
            api: "libcamera",
            path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
            width: 3840,
            height: 2400,
            fps: null,
          },
        ],
      },
    ],
  },
  {
    key: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
    label: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a imx708_wide",
    children: [
      {
        key: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a:YV12 320x240 - 4608x2592 15-120FPS",
        label: "YV12 320x240 - 4608x2592 15-120FPS",
        device: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
        name: "imx708_wide",
        pixel_format: "YV12",
        media_type: null,
        api: "picamera2",
        path: null,
        min_width: 320,
        max_width: 4608,
        min_height: 240,
        max_height: 2592,
        height_step: 2,
        width_step: 2,
        min_fps: 15,
        max_fps: 120,
        fps_step: 1,
      },
      {
        key: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a:I420 320x240 - 4608x2592 15-120FPS",
        label: "I420 320x240 - 4608x2592 15-120FPS",
        device: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
        name: "imx708_wide",
        pixel_format: "I420",
        media_type: null,
        api: "picamera2",
        path: null,
        min_width: 320,
        max_width: 4608,
        min_height: 240,
        max_height: 2592,
        height_step: 2,
        width_step: 2,
        min_fps: 15,
        max_fps: 120,
        fps_step: 1,
      },
    ],
  },
];

describe("findAlternative", () => {
  test("should return best alternative from same API", () => {
    const baseDevicePath = "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a";

    const cameraSettings = {
      pixel_format: "NV21",
      width: 320,
      height: 240,
      fps: null,
    };

    const alternative = findAlternative(
      baseDevicePath,
      cameraSettings,
      sampleDevices,
      true,
    ) as DiscreteDevice & { score: number };

    expect(alternative).toBeDefined();
    expect(alternative?.device).toContain("libcamera");
    expect(alternative?.pixel_format).toEqual("NV21");
    expect(alternative?.width).toEqual(320);
    expect(alternative?.height).toEqual(240);
    expect(alternative?.score).toEqual(21);
  });

  test("should return best alternative from a different API", () => {
    const baseDevicePath = "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a";

    const cameraSettings = {
      pixel_format: "NV21",
      width: 320,
      height: 240,
      fps: null,
    };

    const alternative = findAlternative(
      baseDevicePath,
      cameraSettings,
      sampleDevices,
      false,
    );

    expect(alternative).toBeDefined();
    expect(alternative?.api).toBe("picamera2");

    expect(typeof alternative?.score).toBe("number");
  });

  test("should return best alternative with pixel format match from a different API", () => {
    const baseDevicePath = "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a";

    const cameraSettings = {
      pixel_format: "I420",
      width: 320,
      height: 240,
      fps: null,
    };

    const alternative = findAlternative(
      baseDevicePath,
      cameraSettings,
      sampleDevices,
      false,
    );

    expect(alternative).toBeDefined();
    expect(alternative?.api).toBe("picamera2");
    expect(alternative?.pixel_format).toEqual("I420");

    expect(typeof alternative?.score).toBe("number");
  });

  test("should return nil if no alternative found", () => {
    const baseDevicePath = "nonexistent:/fake/path";
    const cameraSettings = {
      pixel_format: "NV21",
      width: 320,
      height: 240,
      fps: null,
    };

    const alternative = findAlternative(
      baseDevicePath,
      cameraSettings,
      sampleDevices,
      true,
    );
    expect(alternative).toBeNull();
  });
});

describe("groupDevices", () => {
  test("should devices", () => {
    expect(
      groupDevices([
        {
          device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
          name: "imx708_wide",
          pixel_format: "NV21",
          media_type: "video/x-raw",
          api: "libcamera",
          path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
          width: 640,
          height: 480,
          fps: null,
        },
        {
          device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
          name: "imx708_wide",
          pixel_format: "NV21",
          media_type: "video/x-raw",
          api: "libcamera",
          path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
          width: 160,
          height: 120,
          fps: null,
        },
        {
          device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
          name: "imx708_wide",
          pixel_format: "NV21",
          media_type: "video/x-raw",
          api: "libcamera",
          path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
          width: 240,
          height: 160,
          fps: null,
        },
        {
          device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
          name: "imx708_wide",
          pixel_format: "NV21",
          media_type: "video/x-raw",
          api: "libcamera",
          path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
          width: 320,
          height: 240,
          fps: null,
        },
        {
          device: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
          name: "imx708_wide",
          pixel_format: "I420",
          media_type: null,
          api: "picamera2",
          path: null,
          min_width: 320,
          max_width: 4608,
          min_height: 240,
          max_height: 2592,
          height_step: 2,
          width_step: 2,
          min_fps: 15,
          max_fps: 120,
          fps_step: 1,
        },
        {
          device: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
          name: "imx708_wide",
          pixel_format: "YV12",
          media_type: null,
          api: "picamera2",
          path: null,
          min_width: 320,
          max_width: 4608,
          min_height: 240,
          max_height: 2592,
          height_step: 2,
          width_step: 2,
          min_fps: 15,
          max_fps: 120,
          fps_step: 1,
        },
      ]),
    ).toEqual([
      {
        key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
        label: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a imx708_wide",
        children: [
          {
            key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:NV21",
            label: "NV21",
            children: [
              {
                key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:NV21 640x480 video/x-raw",
                label: "NV21 640x480 video/x-raw",
                device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
                name: "imx708_wide",
                pixel_format: "NV21",
                media_type: "video/x-raw",
                api: "libcamera",
                path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
                width: 640,
                height: 480,
                fps: null,
              },
              {
                key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:NV21 160x120 video/x-raw",
                label: "NV21 160x120 video/x-raw",
                device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
                name: "imx708_wide",
                pixel_format: "NV21",
                media_type: "video/x-raw",
                api: "libcamera",
                path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
                width: 160,
                height: 120,
                fps: null,
              },
              {
                key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:NV21 240x160 video/x-raw",
                label: "NV21 240x160 video/x-raw",
                device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
                name: "imx708_wide",
                pixel_format: "NV21",
                media_type: "video/x-raw",
                api: "libcamera",
                path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
                width: 240,
                height: 160,
                fps: null,
              },
              {
                key: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a:NV21 320x240 video/x-raw",
                label: "NV21 320x240 video/x-raw",
                device: "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
                name: "imx708_wide",
                pixel_format: "NV21",
                media_type: "video/x-raw",
                api: "libcamera",
                path: "/base/soc/i2c0mux/i2c@1/imx708@1a",
                width: 320,
                height: 240,
                fps: null,
              },
            ],
          },
        ],
      },
      {
        key: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
        label: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a imx708_wide",
        children: [
          {
            key: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a:I420 320x240 - 4608x2592 15-120FPS",
            label: "I420 320x240 - 4608x2592 15-120FPS",
            device: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
            name: "imx708_wide",
            pixel_format: "I420",
            media_type: null,
            api: "picamera2",
            path: null,
            min_width: 320,
            max_width: 4608,
            min_height: 240,
            max_height: 2592,
            height_step: 2,
            width_step: 2,
            min_fps: 15,
            max_fps: 120,
            fps_step: 1,
          },
          {
            key: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a:YV12 320x240 - 4608x2592 15-120FPS",
            label: "YV12 320x240 - 4608x2592 15-120FPS",
            device: "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
            name: "imx708_wide",
            pixel_format: "YV12",
            media_type: null,
            api: "picamera2",
            path: null,
            min_width: 320,
            max_width: 4608,
            min_height: 240,
            max_height: 2592,
            height_step: 2,
            width_step: 2,
            min_fps: 15,
            max_fps: 120,
            fps_step: 1,
          },
        ],
      },
    ]);
  });
});
