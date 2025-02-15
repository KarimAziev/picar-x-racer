import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";
import { isString } from "@/util/guards";

export interface MessageItemParams {
  title?: string;
  text: string;
  delay?: number;
  type: "success" | "info" | "error" | "warning";
  immediately?: boolean;
  meta?: any;
}

export interface MessageItem {
  title?: string;
  text: string;
  delay: number;
  type: MessageItemParams["type"];
  id: number;
  immediately?: boolean;
  meta?: any;
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

export const useStore = defineStore("messager", {
  state: () => ({ ...defaultState }),

  actions: {
    add(params: MessageItem) {
      this.messages.push(params);
      setTimeout(() => {
        this.messages = this.messages.filter((m) => m.id !== params.id);
      }, params.delay);
    },

    remove(pred: (m: MessageItem) => boolean) {
      this.messages = this.messages.filter((v) => !pred(v));
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

    show(text: string, props?: ShowMessageProps) {
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
    _show_type(
      type: MessageItemParams["type"],
      text: any,
      props?: ShowMessageTypeProps | string,
    ) {
      if (isString(props)) {
        return this.show(text, { title: props, type });
      }
      return this.show(text, { ...props, type });
    },
    error(text: any, props?: ShowMessageTypeProps | string) {
      return this._show_type("error", text, props);
    },

    makeProgress(title: string) {
      let lastProgress = 0;
      const sym = Symbol("progress");
      return (progress: number) => {
        if (lastProgress !== progress) {
          lastProgress = progress;
          let found = false;
          this.messages.forEach((v, i) => {
            if (v.meta === sym) {
              v.text = `${progress}%`;
              this.messages[i] = v;
              found = true;
            }
          });

          if (!found) {
            this.info(`${progress}%`, {
              immediately: true,
              title,
              delay: 5000,
              meta: sym,
            });
          }
        }
      };
    },

    info(text: any, props?: ShowMessageTypeProps | string) {
      return this._show_type("info", text, props);
    },

    success(text: any, props?: ShowMessageTypeProps | string) {
      return this._show_type("success", text, props);
    },

    warning(text: any, props?: ShowMessageTypeProps | string) {
      return this._show_type("warning", text, props);
    },

    handleError<Err>(error: Err, title?: string) {
      const data = retrieveError(error);
      this.error(data.text, title ? { title } : data);
    },
  },
});
