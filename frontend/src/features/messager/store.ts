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

export type ShowMessageProps = Omit<MessageItemParams, "text">;
export type ShowMessageTypeProps = Omit<ShowMessageProps, "type">;

export interface State {
  messages: MessageItem[];
}

const defaultState: State = {
  messages: [],
};

export const useMessagerStore = defineStore("messager", {
  state: () => ({ ...defaultState }),

  actions: {
    show(text: string, props?: ShowMessageProps) {
      const type = props?.type || "info";
      const id = new Date().getTime();
      const params = { text, delay: 2000, ...props, type, id };
      const self = this;
      self.messages.push(params);
      setTimeout(() => {
        self.messages = self.messages.filter((m) => m.id !== id);
      }, params.delay);
    },
    error(text: string, props?: ShowMessageTypeProps) {
      return this.show(text, { ...props, type: "error" });
    },
    info(text: string, props?: ShowMessageTypeProps) {
      return this.show(text, { ...props, type: "info" });
    },
    success(text: string, props?: ShowMessageTypeProps) {
      return this.show(text, { ...props, type: "success" });
    },
    handleError<Err>(error: Err, title?: string) {
      const data = retrieveError(error);
      this.error(data.text, title ? { title } : data);
    },
  },
});
