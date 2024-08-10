import './speedometer.css';

export interface SpeedometerParams {
  /**
   * Current value in range between minValue and maxValue
   * @defaultValue 0
   */
  value: number;
  /**
   * Minimal allowed value
   * @defaultValue 0
   */
  minValue: number;
  /**
   * Maximum allowed value
   * @defaultValue 100
   */
  maxValue: number;
  /**
   * Number of segments in the speedometer.
   * @defaultValue 10
   */
  segments: number;
  extraValue?: number;
  rootElement: HTMLElement;
}

export class Speedometer {
  private rootElement: HTMLElement | null = null;
  private needleElement: HTMLElement | null = null;
  private centerLabelElement: HTMLElement | null = null;
  private value: number = 0;
  private minValue: number = 0;
  private maxValue: number = 100;
  private segments: number = 10;

  constructor(params?: Partial<SpeedometerParams>) {
    if (params) {
      this.value = params.value ?? this.value;
      this.minValue = params.minValue ?? this.minValue;
      this.maxValue = params.maxValue ?? this.maxValue;
      this.segments = params.segments ?? this.segments;
      if (params.rootElement) {
        this.rootElement = params.rootElement;
        this.render();
        this.updateNeedle(this.value);
      }
    }
  }

  static make(params?: Partial<SpeedometerParams>) {
    return new Speedometer(params);
  }

  mount<Element extends HTMLElement>(parentElement: Element) {
    this.rootElement = parentElement;
    this.render();
    this.updateNeedle(this.value);
  }

  updateValue(value: number) {
    this.value = Math.max(this.minValue, Math.min(value, this.maxValue));
    this.updateNeedle(this.value);
  }

  private render() {
    if (!this.rootElement) return;

    // Apply styles
    const style = document.createElement('style');
    style.textContent = `
      .outer-labels div:nth-child(1) {
        transform: rotate(180deg) translateY(-120px) rotate(-180deg);
      }
      .outer-labels div:nth-child(2) {
        transform: rotate(198deg) translateY(-120px) rotate(-198deg);
      }
      .outer-labels div:nth-child(3) {
        transform: rotate(216deg) translateY(-120px) rotate(-216deg);
      }
      .outer-labels div:nth-child(4) {
        transform: rotate(234deg) translateY(-120px) rotate(-234deg);
      }
      .outer-labels div:nth-child(5) {
        transform: rotate(252deg) translateY(-120px) rotate(-252deg);
      }
      .outer-labels div:nth-child(6) {
        transform: rotate(270deg) translateY(-120px) rotate(-270deg);
      }
      .outer-labels div:nth-child(7) {
        transform: rotate(288deg) translateY(-120px) rotate(-288deg);
      }
      .outer-labels div:nth-child(8) {
        transform: rotate(306deg) translateY(-120px) rotate(-306deg);
      }
      .outer-labels div:nth-child(9) {
        transform: rotate(324deg) translateY(-120px) rotate(-324deg);
      }
      .outer-labels div:nth-child(10) {
        transform: rotate(342deg) translateY(-120px) rotate(-342deg);
      }
      .outer-labels div:nth-child(11) {
        transform: rotate(360deg) translateY(-120px) rotate(-360deg);
      }
    `;
    document.head.appendChild(style);

    // Set HTML content
    this.rootElement.innerHTML = `
      <div class="speedometer">
        <div class="gauge">
          <div class="progress"></div>
          <div class="gauge-center"></div>
          <div class="needle" id="needle"></div>
        </div>
        <div class="labels">
          <div class="center-label" id="center-label">${this.value}</div>
        </div>
        <div class="outer-labels" id="outer-labels">
          ${this.renderOuterLabels()}
        </div>
      </div>
    `;

    this.needleElement = this.rootElement.querySelector('#needle');
    this.centerLabelElement = this.rootElement.querySelector('#center-label');
  }

  private renderOuterLabels(): string {
    const labels = [];
    for (let i = 0; i <= this.segments; i++) {
      const step = (this.maxValue - this.minValue) / this.segments;
      const value = step * i;
      labels.push(`<div>${value}</div>`);
    }
    return labels.join('');
  }

  private updateNeedle(value: number) {
    if (this.needleElement && this.centerLabelElement) {
      const rotation =
        ((value - this.minValue) / (this.maxValue - this.minValue)) * 180 - 90;
      this.needleElement.style.transform = `translateY(-100%) rotate(${
        rotation + 180
      }deg)`;
      this.centerLabelElement.textContent = `${value}`;
    }
  }
}
