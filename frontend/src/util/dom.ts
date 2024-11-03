export function requestFullScreen() {
  if (document.documentElement.requestFullscreen) {
    document.documentElement.requestFullscreen({ navigationUI: "hide" });
  } else if (
    (document.documentElement as unknown as any).mozRequestFullScreen
  ) {
    (document.documentElement as unknown as any).mozRequestFullScreen({
      navigationUI: "hide",
    });
  } else if (
    (document.documentElement as unknown as any).webkitRequestFullscreen
  ) {
    (document.documentElement as unknown as any).webkitRequestFullscreen({
      navigationUI: "hide",
    });
  } else if ((document.documentElement as unknown as any).msRequestFullscreen) {
    (document.documentElement as unknown as any).msRequestFullscreen({
      navigationUI: "hide",
    });
  }
}

export function exitFullScreen() {
  if (document.exitFullscreen) {
    document.exitFullscreen();
  } else if ((document as any).mozCancelFullScreen) {
    (document as any).mozCancelFullScreen();
  } else if ((document as any).webkitExitFullscreen) {
    (document as any).webkitExitFullscreen();
  } else if ((document as any).msExitFullscreen) {
    (document as any).msExitFullscreen();
  }
}
