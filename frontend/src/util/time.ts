export function secondsToReadableString(seconds: number): string {
  if (seconds < 0) {
    throw new Error("Input seconds should be a non-negative number.");
  }

  const minutes = Math.floor(seconds / 60);

  const remainingSeconds = seconds % 60;

  const formattedMinutes = minutes.toString().padStart(2, "0");
  const formattedSeconds = remainingSeconds.toFixed().padStart(2, "0");

  return `${formattedMinutes}:${formattedSeconds}`;
}

export function secondsToMiliseconds(seconds: number): number {
  if (seconds < 0) {
    throw new Error("Input seconds should be a non-negative number.");
  }

  return seconds * 1000;
}
