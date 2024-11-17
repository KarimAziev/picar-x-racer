import { DetectionResult } from "@/features/controller/detectionStore";

export const drawOverlay = (
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  detectionData?: DetectionResult[],
) => {
  if (!canvas || !img) return;

  const ctx = canvas!.getContext("2d");

  if (!ctx) {
    return;
  }

  const originalWidth = img.naturalWidth;
  const originalHeight = img.naturalHeight;

  const displayedWidth = img.clientWidth;
  const displayedHeight = img.clientHeight;

  const scaleX = displayedWidth / originalWidth;
  const scaleY = displayedHeight / originalHeight;

  canvas.width = displayedWidth;
  canvas.height = displayedHeight;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const styles = getComputedStyle(document.documentElement);
  const color = styles.getPropertyValue("--color-text").trim();
  const font = styles.getPropertyValue("--canvas-font").trim();

  ctx.lineWidth = 4;
  ctx.font = font;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;

  detectionData?.forEach((detection) => {
    const { label, confidence, bbox } = detection;
    let [x1, y1, x2, y2] = bbox;

    x1 = x1 * scaleX;
    y1 = y1 * scaleY;
    x2 = x2 * scaleX;
    y2 = y2 * scaleY;

    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    ctx.fillText(
      `${label.toUpperCase()}: ${(confidence * 100).toFixed(1)}%`,
      x1 + 5,
      y1 + 25,
    );
  });
};

export const drawAimOverlay = (
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  detectionData?: DetectionResult[],
) => {
  if (!canvas || !img) return;

  const ctx = canvas.getContext("2d");

  if (!ctx) {
    return;
  }

  const originalWidth = img.naturalWidth;
  const originalHeight = img.naturalHeight;

  const displayedWidth = img.clientWidth;
  const displayedHeight = img.clientHeight;

  const scaleX = displayedWidth / originalWidth;
  const scaleY = displayedHeight / originalHeight;

  canvas.width = displayedWidth;
  canvas.height = displayedHeight;

  // Clear the canvas before drawing new frame
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const styles = getComputedStyle(document.documentElement);
  const color = styles.getPropertyValue("--color-text").trim();
  const font = styles.getPropertyValue("--canvas-font").trim();

  ctx.lineWidth = 4;
  ctx.font = font;
  ctx.strokeStyle = color; // Set the crosshair color
  ctx.fillStyle = color; // Set the text color

  detectionData?.forEach((detection) => {
    const { label, confidence, bbox } = detection;
    let [x1, y1, x2, y2] = bbox;

    // Adjust bounding box coordinates to the canvas scale
    x1 = x1 * scaleX;
    y1 = y1 * scaleY;
    x2 = x2 * scaleX;
    y2 = y2 * scaleY;

    const midX = (x1 + x2) / 2; // Mid-point of the bounding box (horizontal)
    const midY = (y1 + y2) / 2; // Mid-point of the bounding box (vertical)

    // Full-width horizontal line across the bounding box
    ctx.beginPath();
    ctx.moveTo(x1, midY); // Start at the left edge of the bbox
    ctx.lineTo(x2, midY); // Draw to the right edge of the bbox
    ctx.stroke();

    // Full-height vertical line through the bounding box
    ctx.beginPath();
    ctx.moveTo(midX, y1); // Start at the top edge of the bbox
    ctx.lineTo(midX, y2); // Draw to the bottom edge of the bbox
    ctx.stroke();

    // Draw the label with detection confidence slightly above the bbox
    ctx.fillText(
      `${label.toUpperCase()}: ${(confidence * 100).toFixed(1)}%`,
      x1, // Start slightly to the left of the bbox
      y1 - 10, // Position it slightly above the top of the bbox
    );
  });
};
