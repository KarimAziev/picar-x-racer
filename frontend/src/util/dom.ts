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

export function takePhotoEffect() {
  const flash = document.createElement("div");
  const styles = getComputedStyle(document.documentElement);
  const color = styles.getPropertyValue("--color-text").trim();
  flash.style.position = "fixed";
  flash.style.top = "0";
  flash.style.left = "0";
  flash.style.width = "100%";
  flash.style.height = "100%";
  flash.style.backgroundColor = color;
  flash.style.opacity = "0.8";
  flash.style.zIndex = "9999";
  flash.style.transition = "opacity 0.3s ease";

  document.body.appendChild(flash);

  setTimeout(() => {
    flash.style.opacity = "0";
    setTimeout(() => {
      flash.remove();
    }, 300);
  }, 100);
}
