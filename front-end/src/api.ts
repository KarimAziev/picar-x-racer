import { logToElement } from '@/util/log';
import { messager } from '@/util/message';

export class RealSockets {
  private websocket: WebSocket;
  private url: string;
  private messageQueue: string[] = [];
  private onOpenCallbacks: (() => void)[] = [];
  private connected: boolean = false;

  constructor(url: string) {
    this.url = url;
    this.initializeWebSocket();
  }

  private initializeWebSocket() {
    this.websocket = new WebSocket(this.url);

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

    this.websocket.onerror = (error) => {
      console.error(`WebSocket error: ${error}`);
      this.connected = false;
    };
  }

  private retryConnection() {
    setTimeout(() => {
      console.log('Retrying WebSocket connection...');
      this.initializeWebSocket();
    }, 5000);
  }

  private sendMessage(message: any): void {
    const msgString = JSON.stringify(message);
    if (this.connected) {
      this.websocket.send(msgString);
      logToElement(`Sent message: ${msgString}`);
    } else {
      this.messageQueue.push(msgString);
    }
  }

  forward(speed: number): void {
    this.sendMessage({ action: 'move', direction: 'forward', speed });
  }

  backward(speed: number): void {
    this.sendMessage({ action: 'move', direction: 'backward', speed });
  }

  stop(): void {
    this.sendMessage({ action: 'stop' });
  }

  setDirServoAngle(angle: number): void {
    this.sendMessage({ action: 'setServo', angle });
  }

  setCamTiltAngle(angle: number): void {
    this.sendMessage({ action: 'setCamTiltAngle', angle });
  }

  setCamPanAngle(angle: number): void {
    this.sendMessage({ action: 'setCamPanAngle', angle });
  }

  playMusic(): void {
    this.sendMessage({ music: 'play' });
  }

  stopMusic(): void {
    this.sendMessage({ music: 'stop' });
  }

  playSound(): void {
    this.sendMessage({ sound: 'play' });
  }

  sayText(text: string): void {
    this.sendMessage({ speech: text });
  }

  takePhoto(): void {
    messager.success('Photo taken');
    this.sendMessage({ photo: 'take' });
  }

  onOpen(callback: () => void) {
    if (this.connected) {
      callback();
    } else {
      this.onOpenCallbacks.push(callback);
    }
  }
}
