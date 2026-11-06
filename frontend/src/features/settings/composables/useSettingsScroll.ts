import { nextTick, onBeforeUnmount, onMounted, watch, type Ref } from "vue";
import { useStore as usePopupStore } from "@/features/settings/stores/popup";
import { isHTMLElement, isNull, isNumber } from "@/util/guards";

/** Remembers each tab's position in the settings dialog's scroll viewport. */
export function useSettingsScroll(content: Readonly<Ref<HTMLElement | null>>) {
  const popupStore = usePopupStore();
  let viewport: HTMLElement | null = null;
  let observer: ResizeObserver | null = null;
  let frame: number | null = null;
  let activeTab = popupStore.tab;
  let restoring = false;
  let target = 0;

  const savePosition = () => {
    if (viewport && popupStore.isOpen && !restoring) {
      popupStore.scrollPositions[activeTab] = viewport.scrollTop;
    }
  };

  const cancelRestore = () => {
    restoring = false;
    if (!isNull(frame)) {
      cancelAnimationFrame(frame);
      frame = null;
    }
  };

  const scheduleRestore = () => {
    if (!restoring || !isNull(frame)) return;
    frame = requestAnimationFrame(() => {
      frame = null;
      if (!viewport || !restoring) return;
      viewport.scrollTop = target;
      // Async panels can grow over several renders before this position exists.
      if (viewport.scrollHeight - viewport.clientHeight >= target) {
        restoring = false;
      }
    });
  };

  const restorePosition = () => {
    cancelRestore();
    if (!viewport || !popupStore.isOpen || popupStore.robotSection) return;
    const saved = popupStore.scrollPositions[activeTab];
    target = isNumber(saved) && Number.isFinite(saved) ? Math.max(0, saved) : 0;
    restoring = true;
    void nextTick(scheduleRestore);
  };

  const onInteraction = () => {
    cancelRestore();
    savePosition();
  };

  const interactionEvents = [
    "wheel",
    "touchstart",
    "pointerdown",
    "keydown",
  ] as const;

  watch(
    () => popupStore.tab,
    (tab) => {
      savePosition();
      activeTab = tab;
      restorePosition();
    },
    { flush: "sync" },
  );

  watch(
    () => popupStore.isOpen,
    (open) => {
      if (open) {
        restorePosition();
      } else {
        // Capture before the dialog's closing transition removes its content.
        if (viewport && !restoring) {
          popupStore.scrollPositions[activeTab] = viewport.scrollTop;
        }
        cancelRestore();
      }
    },
    { flush: "sync" },
  );

  watch(
    () => popupStore.robotSection,
    (section) => {
      if (section) cancelRestore();
    },
    { flush: "sync" },
  );

  onMounted(() => {
    const parent = content.value?.closest(".p-dialog-content") ?? null;
    if (!isHTMLElement(parent) || !content.value) return;
    viewport = parent;
    viewport.addEventListener("scroll", savePosition, { passive: true });
    interactionEvents.forEach((event) => {
      viewport?.addEventListener(event, onInteraction, { passive: true });
    });
    observer = new ResizeObserver(scheduleRestore);
    observer.observe(content.value);
    observer.observe(viewport);
    restorePosition();
  });

  onBeforeUnmount(() => {
    savePosition();
    cancelRestore();
    observer?.disconnect();
    viewport?.removeEventListener("scroll", savePosition);
    interactionEvents.forEach((event) => {
      viewport?.removeEventListener(event, onInteraction);
    });
    viewport = null;
  });
}
