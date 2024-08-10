import { logToElement } from '@/util/log';

export class RealSockets {
  private websocket: WebSocket;

  constructor(url: string) {
    this.websocket = new WebSocket(url);

    this.websocket.onopen = () => {
      console.log('WebSocket connection established');
    };

    this.websocket.onclose = () => {
      console.log('WebSocket connection closed');
    };

    this.websocket.onerror = (error) => {
      console.error(`WebSocket error: ${error}`);
    };
  }

  private sendMessage(message: any): void {
    const msgString = JSON.stringify(message);
    this.websocket.send(msgString);
    logToElement(`Sent message: ${msgString}`);
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
    this.sendMessage({ photo: 'take' });
  }
}
