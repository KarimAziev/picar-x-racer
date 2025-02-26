import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("@/views/HomeView.vue"),
    },
    {
      path: "/virtual",
      name: "virtual_mode",
      component: () => import("@/views/VirtualView.vue"),
    },
  ],
});

export default router;
