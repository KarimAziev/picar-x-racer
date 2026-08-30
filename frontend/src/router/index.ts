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
      path: "/autonomy",
      name: "autonomy",
      component: () => import("@/views/AutonomyView.vue"),
    },
    {
      path: "/virtual",
      name: "virtual_mode",
      redirect: { name: "autonomy", query: { view: "model" } },
    },
  ],
});

export default router;
