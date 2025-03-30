<template>
  <div ref="editorContainer" class="w-full h-full"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { EditorState, Compartment, Prec } from "@codemirror/state";
import { EditorView, basicSetup } from "codemirror";
import * as commands from "@codemirror/commands";
import { keymap } from "@codemirror/view";
import type { First } from "@/util/ts-helpers";
import { languages } from "@codemirror/language-data";
import { oneDark, oneDarkHighlightStyle } from "@codemirror/theme-one-dark";
import { emacs } from "@replit/codemirror-emacs";
import { syntaxHighlighting } from "@codemirror/language";

import { joinLine, smartLineStart } from "@/util/codemirror-commands";

interface Props {
  modelValue?: string | null;
  theme?: string;
  language?: First<typeof languages>;
  autofocus?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: "",
  theme: "dark",
  autofocus: true,
});

let searchPanelObserver: MutationObserver | null = null;

const addKeymapCommands = Prec.highest(
  keymap.of([
    {
      key: "Ctrl-Alt-f",
      run: commands.cursorSyntaxRight,
      preventDefault: true,
    },
    { key: "Ctrl-Alt-b", run: commands.cursorSyntaxLeft, preventDefault: true },
    { key: "Alt-;", run: commands.toggleLineComment },
    { key: "Alt->", run: commands.cursorDocEnd },
    { key: "Alt-<", run: commands.cursorDocStart },
    { key: "Alt-j", run: joinLine },
    { key: "Ctrl-a", run: smartLineStart },
    { key: "Ctrl-d", run: commands.deleteCharForward },
  ]),
);

const searchPanelOpen = ref(false);
const emit = defineEmits(["update:modelValue", "search:open", "search:close"]);

const editorContainer = ref<Element | null>(null);
const themeCompartment = new Compartment();
let editorView: EditorView | null = null;

const languageCompartment = new Compartment();

const loadLanguageExtension = async (lang?: typeof props.language) => {
  if (lang) {
    const support = await lang.load();
    return support.extension;
  }
  return [];
};

onMounted(async () => {
  if (editorContainer.value) {
    const langExtension = await loadLanguageExtension(props.language);
    const state = EditorState.create({
      doc: props.modelValue || "",
      extensions: [
        addKeymapCommands,
        Prec.high(emacs()),
        basicSetup,
        languageCompartment.of(langExtension),
        syntaxHighlighting(oneDarkHighlightStyle),
        themeCompartment.of(props.theme === "dark" ? oneDark : []),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            const newVal = update.state.doc.toString();
            if (newVal !== props.modelValue) {
              emit("update:modelValue", newVal);
            }
          }
        }),
      ],
    });

    editorView = new EditorView({
      state,
      parent: editorContainer.value,
    });

    if (props.autofocus) {
      await nextTick();
      setTimeout(() => {
        if (editorView) {
          editorView.focus();
        }
      }, 200);
    }

    searchPanelObserver = new MutationObserver(() => {
      const panel = editorContainer.value?.querySelector(".cm-search");
      if (panel && !searchPanelOpen.value) {
        searchPanelOpen.value = true;
        emit("search:open");
      } else if (!panel && searchPanelOpen.value) {
        searchPanelOpen.value = false;
        setTimeout(() => {
          if (!searchPanelOpen.value) {
            emit("search:close");
          }
        }, 500);
      }
    });

    searchPanelObserver.observe(editorContainer.value, {
      childList: true,
      subtree: true,
    });
  }
});

watch(
  () => props.modelValue,
  (newVal) => {
    if (editorView) {
      const currentValue = editorView.state.doc.toString();
      if (newVal !== null && newVal !== currentValue) {
        editorView.dispatch({
          changes: { from: 0, to: editorView.state.doc.length, insert: newVal },
        });
      }
    }
  },
);

watch(
  () => props.language,
  async (newLang) => {
    if (editorView) {
      const ext = await loadLanguageExtension(newLang);
      editorView.dispatch({
        effects: languageCompartment.reconfigure(ext),
      });
    }
  },
);

onBeforeUnmount(() => {
  if (editorView) {
    editorView.destroy();
    editorView = null;
  }
  if (searchPanelObserver && editorContainer.value) {
    searchPanelObserver.disconnect();
    searchPanelObserver = null;
  }
});
</script>
