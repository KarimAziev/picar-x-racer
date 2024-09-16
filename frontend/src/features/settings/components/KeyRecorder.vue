<template>
  <Dialog
    v-model:visible="visible"
    header="Recording"
    :closable="false"
    :closeOnEscape="false"
    :modal="false"
  >
    <div class="title-caption">
      Press desired key sequence and then<br />
      <b>Enter</b> to confirm or <b>Escape</b> to reset
    </div>
    <div class="field">
      <InputText v-model="keyInput" :readonly="!recording" />
    </div>
    <div class="error" v-if="errorMsg">{{ errorMsg }}</div>
    <ButtonGroup class="button-group">
      <Button
        label="Reset"
        outlined
        :disabled="keyEvents.length === 0"
        @click="resetRecording"
      />
      <Button label="Submit" :disabled="submitDisabled" @click="submit" />
      <Button severity="danger" label="Cancel" @click="cancel" />
    </ButtonGroup>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import ButtonGroup from "primevue/buttongroup";
import { KeyboardMapper } from "@/util/keyboard-mapper";
import { formatKeyboardEvents, validateKeyString } from "@/util/keyboard-util";
import { isString } from "@/util/guards";

const props = defineProps({
  onSubmit: Function,
  onCancel: Function,
  validate: Function,
});

const visible = ref(true);
const keyInput = ref<string>("");
const keyEvents = ref<KeyboardEvent[]>([]);
const errorMsg = ref<string | undefined>("");
const recording = ref(false);

const submitDisabled = computed(() => {
  return keyEvents.value.length === 0 || errorMsg.value !== "";
});

const toggleRecording = () => {
  recording.value = !recording.value;
  if (recording.value) {
    attachKeyDownListener();
  } else {
    removeKeyDownListener();
  }
};

const attachKeyDownListener = () => {
  document.addEventListener("keydown", handleKeyDown);
};

const removeKeyDownListener = () => {
  document.removeEventListener("keydown", handleKeyDown);
};

const handleKeyDown = (ev: KeyboardEvent) => {
  const key = ev.key;
  ev.preventDefault();

  if (KeyboardMapper.isModifier(key)) {
    return;
  }

  if (["Enter"].includes(key) && keyEvents.value.length > 0) {
    toggleRecording();
    submit();
    return;
  }

  if (["Escape"].includes(key)) {
    if (keyEvents.value.length > 0) {
      resetRecording();
    } else {
      resetRecording();
      cancel();
    }
    return;
  }

  if (["Backspace"].includes(key)) {
    if (keyEvents.value.length > 0) {
      keyEvents.value.pop();
      keyInput.value = formatKeyboardEvents(keyEvents.value);
      return;
    }
  }

  keyEvents.value = [ev];
  keyInput.value = formatKeyboardEvents(keyEvents.value);
  submit();
};

const validateInput = () => {
  if (!validateKeyString(keyInput.value)) {
    errorMsg.value = "Invalid key";
    resetRecording();
    return false;
  }
  const error = props.validate?.(keyInput.value);
  errorMsg.value = isString(error) ? error : error ? "Invalid" : "";

  return !error;
};

const resetRecording = () => {
  keyEvents.value = [];
  keyInput.value = "";
  errorMsg.value = "";
};

const submit = () => {
  if (validateInput()) {
    props.onSubmit?.(keyInput.value);
    removeKeyDownListener();
  }
};

const cancel = () => {
  if (props.onCancel) {
    props.onCancel();
    removeKeyDownListener();
  }
};

onMounted(() => {
  toggleRecording();
});

onBeforeUnmount(() => {
  removeKeyDownListener();
});
</script>

<style scoped>
.dialog {
  max-width: 500px;
}

.title-caption {
  margin-bottom: 1em;
}

.error {
  color: red;
  margin-top: 0.5em;
}
.field {
  margin: 20px 0;
}
</style>
