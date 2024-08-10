import { FakeSockets } from '@/stubs';
import { logToElement } from '@/util/log';
import { Speedometer } from '@/speedometer/speedometer';
import { RealSockets } from '@/api';

const ACCELERATION = 10;
const DECELERATION = 10;

export class VideoCarController {
  /** Current speed of the car, from 0 to 100 */
  private speed: number = 0;
  /**
   * Current direction: -1 for backward, 1 for forward, 0 for stopped
   */
  private direction: number = 0;
  private servoAngle: number = -1;
  private activeKeys: Set<string> = new Set();
  private speedometer: Speedometer;

  private maxSpeed: number = 80;

  constructor(
    private api: FakeSockets | RealSockets,
    private rootElement?: HTMLElement,
  ) {
    this.increaseMaxSpeed = this.increaseMaxSpeed.bind(this);
    this.decreaseMaxSpeed = this.decreaseMaxSpeed.bind(this);
    this.start = this.start.bind(this);
    this.handleKeyDown = this.handleKeyDown.bind(this);
    this.handleKeyUp = this.handleKeyUp.bind(this);
    this.slowdown = this.slowdown.bind(this);
  }

  start(rootElement?: HTMLElement) {
    if (rootElement) {
      this.rootElement = rootElement;
    }
    if (this.rootElement) {
      this.rootElement.innerHTML = `<div class="wrapper">
  <div class="side-menu">
    <ul class="logs"></ul>
  </div>
  <div class="content">

  <div class="video-box">
      <div>
        <img src="/mjpg" alt="Video">
      </div>
  </div>
      </div>
  <div class="right">
      <div class="active-keys">
      <div class="row">
        <kbd class="w">w</kbd>
      </div>
      <div class="row">
        <kbd class="a">a</kbd>
        <kbd class="s">s</kbd>
        <kbd class="d">d</kbd>
      </div>
      <div class="row">
        <kbd class="space">Space</kbd>
      </div>
    </div>
    <div class="angle-wrapper"></div>
    <div class="speedometer-wrapper"></div>
  </div>
</div>
`;
    }

    logToElement('STARTING GAME');
    const wrapper = document.querySelector<HTMLDivElement>(
      '.speedometer-wrapper',
    ) as HTMLDivElement;
    this.speedometer = new Speedometer({ rootElement: wrapper });
    this.setupEventListeners();
    this.gameLoop();
  }

  private setupEventListeners() {
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
  }

  private handleKeyDown(event: KeyboardEvent) {
    const key = event.key;
    this.activeKeys.add(key);

    const otherMethods: { [key: string]: Function } = {
      t: this.api.takePhoto,
      m: this.api.playMusic,
      r: this.api.playSound,
      k: this.api.sayText,
      '=': this.increaseMaxSpeed,
      '-': this.decreaseMaxSpeed,
    };

    if (otherMethods[key]) {
      otherMethods[key]();
    }

    this.updateKeyHighlight();
  }

  private handleKeyUp(event: KeyboardEvent) {
    const key = event.key;

    this.activeKeys.delete(key);

    this.updateKeyHighlight();
  }

  private updateKeyHighlight() {
    ['w', 'a', 's', 'd', ' '].forEach((key) => {
      const keyElement = document.querySelector(
        `kbd.${key === ' ' ? 'space' : key}`,
      );
      if (keyElement) {
        if (this.activeKeys.has(key)) {
          keyElement.classList.add('active');
        } else {
          keyElement.classList.remove('active');
        }
      }
    });
  }

  private gameLoop() {
    this.updateCarState();
    setTimeout(() => this.gameLoop(), 50);
  }

  private updateCarState() {
    if (this.activeKeys.has('w')) {
      this.accelerate();
    } else if (this.activeKeys.has('s')) {
      this.decelerate();
    } else {
      this.slowdown();
    }
    const nextDirServoAngle = this.activeKeys.has('a')
      ? -45
      : this.activeKeys.has('d')
        ? 45
        : 0;

    const currValue = this.servoAngle;

    if (currValue !== nextDirServoAngle) {
      this.api.setDirServoAngle(nextDirServoAngle);
      this.servoAngle = nextDirServoAngle;
    }

    if (this.activeKeys.has(' ')) {
      this.stop();
    }

    this.updateSpeedometer();
    this.updateAngleDisplay();
  }

  private accelerate() {
    const nextSpeed = Math.min(this.speed + ACCELERATION, this.maxSpeed);
    if (this.speed !== nextSpeed || this.direction !== 1) {
      this.api.forward(this.speed);
      this.speed = nextSpeed;
      this.direction = 1;
    }
  }

  private decelerate() {
    const nextSpeed = Math.min(this.speed + ACCELERATION, this.maxSpeed);
    if (this.speed !== nextSpeed || this.direction !== -1) {
      this.api.backward(this.speed);
      this.speed = nextSpeed;
      this.direction = -1;
    }
  }

  private slowdown() {
    if (this.speed > 0) {
      this.speed = Math.max(this.speed - DECELERATION, 0);
    }
    if (this.speed === 0 && this.direction !== 0) {
      this.api.stop();
      this.direction = 0;
    } else if (this.direction === 1) {
      this.api.forward(this.speed);
    } else if (this.direction === -1) {
      this.api.backward(this.speed);
    }
  }

  increaseMaxSpeed() {
    this.maxSpeed = Math.min(100, this.maxSpeed + ACCELERATION);
  }

  decreaseMaxSpeed() {
    this.maxSpeed = Math.max(20, this.maxSpeed - ACCELERATION);
  }

  private stop() {
    this.speed = 0;
    this.direction = 0;
    this.api.stop();
  }

  private updateSpeedometer() {
    this.speedometer.updateValue(this.speed);
  }

  private updateAngleDisplay() {
    const angleElement = document.querySelector('.angle-wrapper');
    if (angleElement) {
      angleElement.textContent = `Angle: ${this.servoAngle}°`;
    }
  }
}
