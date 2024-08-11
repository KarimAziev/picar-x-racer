import { messager } from '@/util/message';
import { WSBridge } from '@/ws/bridge';
import { FakeBridge } from '@/ws/fakeBridge';
import { AbstractWSBridge } from '@/ws/interface';
import { debounce } from '@/util/debounce';

class ServoDirAngleController {
  constructor(private ws: AbstractWSBridge) {
    this.setDirServoAngle = this.setDirServoAngle.bind(this);
    this.resetDirServoAngle = debounce(this.resetDirServoAngle.bind(this), 500);
  }

  resetDirServoAngle() {
    this.ws.sendMessage({ action: 'setServo', angle: 0 });
  }

  setDirServoAngle(angle: number) {
    this.ws.sendMessage({ action: 'setServo', angle });
  }
}

export class Controller {
  private speed: number = 0;
  private direction: number = 0;
  private ws: AbstractWSBridge;
  private servoAngleController: ServoDirAngleController;

  constructor(url: string, useFake?: boolean) {
    this.ws = useFake ? new FakeBridge(url) : new WSBridge(url);
    this.servoAngleController = new ServoDirAngleController(this.ws);
    this.setDirServoAngle = this.setDirServoAngle.bind(this);
    this.forward = this.forward.bind(this);
    this.backward = this.backward.bind(this);
    this.stop = this.stop.bind(this);
    this.resetDirServoAngle = this.resetDirServoAngle.bind(this);
    this.setCamTiltAngle = this.setCamTiltAngle.bind(this);
    this.setCamPanAngle = this.setCamPanAngle.bind(this);
    this.playMusic = this.playMusic.bind(this);
    this.playSound = this.playSound.bind(this);
    this.sayText = this.sayText.bind(this);
    this.takePhoto = this.takePhoto.bind(this);
  }

  forward(speed: number) {
    if (this.speed !== speed || this.direction !== 1) {
      this.ws.sendMessage({ action: 'move', direction: 'forward', speed });
    }

    this.direction = 1;
    this.speed = speed;
    return this;
  }

  backward(speed: number) {
    if (this.speed !== speed || this.direction !== -1) {
      this.ws.sendMessage({ action: 'move', direction: 'backward', speed });
    }

    this.direction = -1;
    this.speed = speed;
    return this;
  }

  stop() {
    this.ws.sendMessage({ action: 'stop' });
    this.direction = 0;
    this.speed = 0;
  }

  setDirServoAngle(angle: number) {
    if (angle === 0) {
      this.servoAngleController.resetDirServoAngle();
    } else {
      this.servoAngleController.setDirServoAngle(angle);
    }
  }

  resetDirServoAngle(): void {
    this.ws.sendMessage({ action: 'setServo', angle: 0 });
  }

  setCamTiltAngle(angle: number): void {
    this.ws.sendMessage({ action: 'setCamTiltAngle', angle });
  }

  setCamPanAngle(angle: number): void {
    this.ws.sendMessage({ action: 'setCamPanAngle', angle });
  }

  playMusic(): void {
    this.ws.sendMessage({ action: 'playMusic' });
  }

  playSound(): void {
    this.ws.sendMessage({ action: 'playSound' });
  }

  sayText(): void {
    this.ws.sendMessage({ action: 'sayText' });
  }

  takePhoto(): void {
    this.ws.sendMessage({ action: 'takePhoto' });
    messager.success('Photo taken');
  }
}
