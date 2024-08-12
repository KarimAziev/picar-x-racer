import { logToElement } from '@/util/log';
import { AbstractWSBridge } from '@/ws/interface';
import { messager } from '@/util/message';

export class WSBridge implements AbstractWSBridge {
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
      console.log(`WebSocket connection established with URL: ${this.url}`);
      this.connected = true;
      while (this.messageQueue.length > 0) {
        this.websocket.send(this.messageQueue.shift()!);
      }
      this.onOpenCallbacks.forEach((callback) => callback());
    };

    this.websocket.onerror = (error) => {
      console.error(`WebSocket error: ${error}`);
      messager.error('WebSocket error');
      this.connected = false;
    };

    this.websocket.onclose = () => {
      console.log('WebSocket connection closed');
      messager.error('WebSocket connection closed');
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
      logToElement(msgString.trim());
    } else {
      this.messageQueue.push(msgString);
    }
  }
}
