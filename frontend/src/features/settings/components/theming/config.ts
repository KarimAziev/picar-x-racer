export const skeletonKeypointsPreviewSample = [
  {
    x: 79.5,
    y: 74.5,
  },
  {
    x: 88.5,
    y: 67,
  },
  {
    x: 75,
    y: 67,
  },
  {
    x: 102,
    y: 73,
  },
  {
    x: 67.5,
    y: 71.5,
  },
  {
    x: 111,
    y: 115,
  },
  {
    x: 52.5,
    y: 115,
  },
  {
    x: 123,
    y: 161.5,
  },
  {
    x: 34.5,
    y: 163,
  },
  {
    x: 132,
    y: 206.5,
  },
  {
    x: 22.5,
    y: 206.5,
  },
  {
    x: 90,
    y: 220,
  },
  {
    x: 52.5,
    y: 218.5,
  },
  {
    x: 85.5,
    y: 293.5,
  },
  {
    x: 51,
    y: 295,
  },
  {
    x: 79.5,
    y: 359.5,
  },
  {
    x: 52.5,
    y: 359.5,
  },
];

export function getBoundingBox(
  keypoints: { x: number; y: number }[],
): [number, number, number, number] {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  keypoints.forEach((point) => {
    if (point.x < minX) {
      minX = point.x;
    }
    if (point.y < minY) {
      minY = point.y;
    }
    if (point.x > maxX) {
      maxX = point.x;
    }
    if (point.y > maxY) {
      maxY = point.y;
    }
  });

  return [minX - 20, 5, maxX + 20, maxY + 20];
}

export const detectionSample = {
  bbox: getBoundingBox(skeletonKeypointsPreviewSample),
  label: "person",
  confidence: 0.9,
  keypoints: skeletonKeypointsPreviewSample,
};
