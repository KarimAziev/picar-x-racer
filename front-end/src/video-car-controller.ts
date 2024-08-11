import { logToElement } from '@/util/log';
import { Speedometer } from '@/speedometer/speedometer';
import { Controller } from '@/api';
import { messager } from '@/util/message';
import { Drawer } from '@/drawer/drawer';

const ACCELERATION = 10;

const CAM_PAN_MIN = -90;
const CAM_PAN_MAX = 90;
const CAM_TILT_MIN = -35;
const CAM_TILT_MAX = 65;

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
  private camPan: number = 0;
  private camTilt: number = 0;

  constructor(
    private api: Controller,
    private rootElement?: HTMLElement,
  ) {
    this.increaseMaxSpeed = this.increaseMaxSpeed.bind(this);
    this.decreaseMaxSpeed = this.decreaseMaxSpeed.bind(this);
    this.start = this.start.bind(this);
    this.handleKeyDown = this.handleKeyDown.bind(this);
    this.handleKeyUp = this.handleKeyUp.bind(this);

    this.slowdown = this.slowdown.bind(this);
    this.updateAngleDisplay = this.updateAngleDisplay.bind(this);
    this.updateSpeedometer = this.updateSpeedometer.bind(this);
    this.accelerate = this.accelerate.bind(this);
    this.decelerate = this.decelerate.bind(this);
    this.increaseCamPan = this.increaseCamPan.bind(this);
    this.decreaseCamPan = this.decreaseCamPan.bind(this);
    this.increaseCamTilt = this.increaseCamTilt.bind(this);
    this.decreaseCamTilt = this.decreaseCamTilt.bind(this);
  }

  start(rootElement?: HTMLElement) {
    if (rootElement) {
      this.rootElement = rootElement;
    }
    if (this.rootElement) {
      this.rootElement.innerHTML = `<div class="wrapper">
  <div class="side-menu">
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
    new Drawer({
      rootElement: document.querySelector('.side-menu') as HTMLElement,
    });
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
      ArrowRight: this.increaseCamPan,
      ArrowLeft: this.decreaseCamPan,
      ArrowUp: this.increaseCamTilt,
      ArrowDown: this.decreaseCamTilt,
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
    this.api.forward(this.speed);
    this.speed = nextSpeed;
    this.direction = 1;
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
      this.speed = Math.max(this.speed - 5, 0);
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
    const curr = Math.min(100, this.maxSpeed + ACCELERATION);
    if (this.maxSpeed !== curr) {
      this.maxSpeed = curr;
      messager.success(`Increased max speed to ${this.maxSpeed}`);
    }
  }

  decreaseMaxSpeed() {
    const curr = Math.max(20, this.maxSpeed - ACCELERATION);
    if (this.maxSpeed !== curr) {
      this.maxSpeed = curr;

      if (this.speed >= this.maxSpeed) {
        this.speed = Math.max(20, this.maxSpeed - 10);
      }
    }
  }

  increaseCamTilt() {
    this.camTilt = Math.min(this.camTilt + 5, CAM_TILT_MAX);
    this.api.setCamTiltAngle(this.camTilt);
  }

  decreaseCamTilt() {
    this.camTilt = Math.max(this.camTilt - 5, CAM_TILT_MIN);
    this.api.setCamTiltAngle(this.camTilt);
  }

  increaseCamPan() {
    this.camPan = Math.min(this.camPan + 5, CAM_PAN_MAX);
    this.api.setCamPanAngle(this.camPan);
  }

  decreaseCamPan() {
    this.camPan = Math.max(this.camPan - 5, CAM_PAN_MIN);
    this.api.setCamPanAngle(this.camPan);
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
