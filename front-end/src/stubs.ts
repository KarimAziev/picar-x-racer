import { logToElement } from '@/util/log';
import { messager } from '@/util/message';

export class FakeSockets {
  // speed: 0-100
  forward(speed: number): void {
    logToElement(`Moving forward with speed ${speed}`);
  }

  // speed: 0-100
  backward(speed: number): void {
    logToElement(`Moving backward with speed ${speed}`);
  }

  stop(): void {
    logToElement('Stopping');
  }

  setDirServoAngle(angle: number): void {
    logToElement(`Setting servo angle to ${angle} degrees`);
  }

  setCamTiltAngle(angle: number): void {
    logToElement(`Setting camera tilt angle to ${angle} degrees`);
  }

  setCamPanAngle(angle: number): void {
    logToElement(`Setting camera pan angle to ${angle} degrees`);
  }
  // key: m
  playMusic() {
    messager.success(`Playing music`);
  }
  // key: r
  playSound() {
    messager.success(`Playing sound`);
  }
  // key: k
  sayText() {
    messager.success(`Saying text`);
  }
  // photo: t
  takePhoto() {
    messager.success(`Taking photo`);
  }
}
