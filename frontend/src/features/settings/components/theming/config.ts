export const skeletonKeypointsPreviewSample = [
  {
    y: 64.5,
    x: 79.5,
  },
  {
    y: 57,
    x: 88.5,
  },
  {
    y: 57,
    x: 75,
  },
  {
    y: 63,
    x: 102,
  },
  {
    y: 61.5,
    x: 67.5,
  },
  {
    y: 105,
    x: 111,
  },
  {
    y: 105,
    x: 52.5,
  },
  {
    y: 151.5,
    x: 123,
  },
  {
    y: 153,
    x: 34.5,
  },
  {
    y: 196.5,
    x: 132,
  },
  {
    y: 196.5,
    x: 22.5,
  },
  {
    y: 210,
    x: 90,
  },
  {
    y: 208.5,
    x: 52.5,
  },
  {
    y: 283.5,
    x: 85.5,
  },
  {
    y: 285,
    x: 51,
  },
  {
    y: 349.5,
    x: 79.5,
  },
  {
    y: 349.5,
    x: 52.5,
  },
].map(({ y, ...rest }) => ({ ...rest, y: y + 10 }));

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
