<template>
  <Drawer v-model:visible="visible">
    <Menu :model="items">
      <template #item="{ item, props }">
        <router-link
          v-if="item.route"
          v-slot="{ href, navigate }"
          :to="item.route"
          custom
        >
          <a :href="href" v-bind="props.action" @click="navigate">
            <span :class="item.icon" />
            <span class="ml-2">{{ item.label }}</span>
          </a>
        </router-link>
        <a v-else :href="item.url" :target="item.target" v-bind="props.action">
          <span :class="item.icon" />
          <span class="ml-2">{{ item.label }}</span>
        </a>
      </template>
    </Menu>
  </Drawer>

  <Button
    severity="secondary"
    icon="pi pi-bars"
    @click="visible = true"
    class="drawer-button"
  />
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import Drawer from "primevue/drawer";
import Button from "primevue/button";
import { ref } from "vue";

import { useRouter } from "vue-router";

const router = useRouter();

const items = ref([
  {
    label: "Home",
    icon: "pi pi-home",
    command: () => {
      router.push("/");
      visible.value = false;
    },
  },
  {
    label: "Settings",
    icon: "pi pi-cog",

    command: () => {
      router.push("/settings");
      visible.value = false;
    },
  },
]);

const visible = ref();
</script>
<style scoped lang="scss">
.drawer-button {
  position: fixed;
  top: 5px;
  left: 5px;
}
</style>
