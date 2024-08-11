import { logToElement } from '@/util/log';
import { messager } from '@/util/message';

export class FakeBridge {
  private websocket: WebSocket;
  private url: string;
  private messageQueue: string[] = [];
  private onOpenCallbacks: (() => void)[] = [];
  private connected: boolean = false;
  private useFake: boolean = false;

  constructor(url: string) {
    this.url = url;
    this.initializeWebSocket();
  }

  private initializeWebSocket() {
    this.websocket = new WebSocket(this.url);

    this.websocket.onerror = () => {
      this.useFake = true;
      this.connected = false;
      while (this.messageQueue.length > 0) {
        this.websocket.send(this.messageQueue.shift()!);
      }
      this.onOpenCallbacks.forEach((callback) => callback());
    };

    this.websocket.onopen = () => {
      console.log('WebSocket connection established');
      this.connected = true;
      while (this.messageQueue.length > 0) {
        this.websocket.send(this.messageQueue.shift()!);
      }
      this.onOpenCallbacks.forEach((callback) => callback());
    };

    this.websocket.onclose = () => {
      console.log('WebSocket connection closed');
      this.connected = false;
      this.retryConnection();
    };
  }

  private retryConnection() {
    setTimeout(() => {
      console.log('Retrying WebSocket connection...');
      this.initializeWebSocket();
    }, 5000);
  }

  public sendMessage(message: any): void {
    const msgString = JSON.stringify(message);
    if (this.connected) {
      this.websocket.send(msgString);
      logToElement(`Sent message: ${msgString}`);
    } else if (!this.connected && this.useFake) {
      logToElement(`Fake message: ${msgString}`);
    } else {
      this.messageQueue.push(msgString);
    }
  }
}

export class FakeSockets {
  // speed: 0-100
  forward(speed: number): void {
    logToElement(
      `Sent message: ${JSON.stringify({
        action: 'move',
        direction: 'forward',
        speed,
      })}`,
    );
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
