import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";
import { isString } from "@/util/guards";

export interface MessageItemParams {
  title?: string;
  text: string;
  delay?: number;
  type: "success" | "info" | "error";
  immediately?: boolean;
}

export interface MessageItem {
  title?: string;
  text: string;
  delay: number;
  type: "success" | "info" | "error";
  id: number;
  immediately?: boolean;
}

export type ShowMessageProps = Omit<MessageItemParams, "text">;
export type ShowMessageTypeProps = Omit<ShowMessageProps, "type">;

export interface State {
  messages: MessageItem[];
  queue: MessageItem[];
  processing: boolean;
}

const defaultState: State = {
  messages: [],
  queue: [],
  processing: false,
};

export const useMessagerStore = defineStore("messager", {
  state: () => ({ ...defaultState }),

  actions: {
    add(params: MessageItem) {
      this.messages.push(params);
      setTimeout(() => {
        this.messages = this.messages.filter((m) => m.id !== params.id);
      }, params.delay);
    },

    async processQueue() {
      if (this.processing || this.queue.length === 0) return;
      this.processing = true;

      while (this.queue.length > 0) {
        const message = this.queue.shift()!;
        this.add(message);
        await new Promise((resolve) => setTimeout(resolve, 500));
      }

      this.processing = false;
    },

    show(text: any, props?: ShowMessageProps) {
      const type = props?.type || "info";
      const id = new Date().getTime();
      const params = { text: `${text}`, delay: 10000, ...props, type, id };
      if (params.immediately) {
        this.add(params);
      } else {
        this.queue.push(params);
        this.processQueue();
      }
    },

    error(text: any, props?: ShowMessageTypeProps | string) {
      const type = "error";
      if (isString(props)) {
        return this.show(text, { title: props, type });
      }
      return this.show(text, { ...props, type });
    },

    info(text: any, props?: ShowMessageTypeProps | string) {
      const type = "info";
      if (isString(props)) {
        return this.show(text, { title: props, type });
      }
      return this.show(text, { ...props, type });
    },

    success(text: any, props?: ShowMessageTypeProps | string) {
      const type = "success";
      if (isString(props)) {
        return this.show(text, { title: props, type });
      }
      return this.show(text, { ...props, type });
    },

    handleError<Err>(error: Err, title?: string) {
      const data = retrieveError(error);
      this.error(data.text, title ? { title } : data);
    },
  },
});
