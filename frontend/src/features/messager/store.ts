import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";

export interface MessageItemParams {
  title?: string;
  text: string;
  delay?: number;
  type: "success" | "info" | "error";
}

export interface MessageItem {
  title?: string;
  text: string;
  delay: number;
  type: "success" | "info" | "error";
  id: number;
}

export interface State {
  messages: MessageItem[];
}

const defaultState: State = {
  messages: [],
};

export const useMessagerStore = defineStore("messager", {
  state: () => ({ ...defaultState }),

  actions: {
    error(text: string, props?: Omit<MessageItemParams, "text" | "type">) {
      const id = new Date().getTime();
      const msg = { text, delay: 2000, ...props, type: "error" as "error", id };
      this.messages.push(msg);
      setTimeout(() => {
        this.messages = this.messages.filter((m) => m.id !== id);
      }, msg.delay);
    },
    info(text: string, props?: Omit<MessageItemParams, "text" | "type">) {
      const id = new Date().getTime();
      const msg = { text, delay: 2000, ...props, type: "info" as "info", id };
      this.messages.push(msg);
      setTimeout(() => {
        this.messages = this.messages.filter((m) => m.id !== id);
      }, msg.delay);
    },
    success(text: string, props?: Omit<MessageItemParams, "text" | "type">) {
      const id = new Date().getTime();
      const msg = {
        text,
        delay: 2000,
        ...props,
        type: "success" as "success",
        id,
      };

      this.messages.push(msg);
      setTimeout(() => {
        this.messages = this.messages.filter((m) => m.id !== id);
      }, msg.delay);
    },
    handleError<Err>(error: Err, title?: string) {
      const data = retrieveError(error);
      this.error(data.text, title ? { title } : data);
    },
  },
});
