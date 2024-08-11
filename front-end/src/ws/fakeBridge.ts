import { logToElement } from '@/util/log';
import { AbstractWSBridge } from '@/ws/interface';

export class FakeBridge implements AbstractWSBridge {
  private url: string;
  private messageQueue: string[] = [];
  private onOpenCallbacks: (() => void)[] = [];
  private connected: boolean = false;

  constructor(url: string) {
    this.url = url;
    console.log(`WebSocket opened with URL: ${this.url}`);
    this.initializeWebSocket();
  }

  private initializeWebSocket() {
    setTimeout(() => {
      this.connected = true;
      while (this.messageQueue.length > 0) {
        this.sendMessage(this.messageQueue.shift()!);
      }
      this.onOpenCallbacks.forEach((callback) => callback());
    }, 500);
  }

  public sendMessage(message: any): void {
    const msgString = JSON.stringify(message);
    if (this.connected) {
      console.log('sent message', msgString);
      logToElement(msgString.trim());
    } else {
      this.messageQueue.push(msgString);
    }
  }
}
