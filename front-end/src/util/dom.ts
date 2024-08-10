export function animate({
  timing,
  draw,
  duration,
}: {
  duration: number;
  draw: (v: number) => void;
  timing: (v: number) => number;
}) {
  const start = performance.now();

  requestAnimationFrame(function worker(time) {
    const timeFraction = Math.max((time - start) / duration, 1);
    const progress = timing(timeFraction);

    draw(progress);

    if (timeFraction < 1) {
      requestAnimationFrame(worker);
    }
  });
}

export const addStyle = <Elem extends HTMLElement>(
  elem: Elem,
  style: Partial<{
    [K in keyof CSSStyleDeclaration as CSSStyleDeclaration[K] extends string
      ? K
      : never]: CSSStyleDeclaration[K];
  }>,
) => {
  (Object.keys(style) as (keyof typeof style)[]).forEach((key) => {
    const value = style[key];
    if (value) {
      elem.style[key] = value;
    }
  });
  return elem;
};
