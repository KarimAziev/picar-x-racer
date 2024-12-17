export function takePhotoEffect() {
  const flash = document.createElement("div");
  flash.style.position = "fixed";
  flash.style.top = "0";
  flash.style.left = "0";
  flash.style.width = "100%";
  flash.style.height = "100%";
  flash.style.backgroundColor = "white";
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

export function showDirectionalIndicator(deltaX: number, deltaY: number) {
  const arrow = document.createElement("div");
  const styles = getComputedStyle(document.documentElement);
  const color = styles.getPropertyValue("--color-text").trim();
  arrow.style.position = "fixed";
  arrow.style.width = "60px";
  arrow.style.height = "60px";
  arrow.style.zIndex = "9999";
  arrow.style.pointerEvents = "none";
  arrow.style.color = color;
  arrow.style.fontSize = "35px";
  arrow.style.fontWeight = "bold";
  arrow.style.display = "flex";
  arrow.style.justifyContent = "center";
  arrow.style.alignItems = "center";
  arrow.style.transition = "opacity 0.3s ease, transform 0.3s ease";

  arrow.style.backgroundColor = "rgba(0, 0, 0, 0.7)";
  arrow.style.borderRadius = "50%";
  arrow.style.opacity = "1";

  arrow.textContent = "↑";

  arrow.style.top = "50%";
  arrow.style.left = "50%";
  arrow.style.transformOrigin = "50% 50%";
  arrow.style.transform = "translate(-50%, -50%)";

  document.body.appendChild(arrow);

  // atan2 gives the angle in radians
  const angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI);

  arrow.style.transform = `translate(-50%, -50%) rotate(${angle + 90}deg)`;
  // +90 is needed because the base arrow ↑ points upwards in the 0° direction

  setTimeout(() => {
    arrow.style.opacity = "0";
    arrow.style.transform = `translate(-50%, -50%) rotate(${angle + 90}deg) scale(0.8)`;
    setTimeout(() => {
      arrow.remove();
    }, 300);
  }, 300);
}
