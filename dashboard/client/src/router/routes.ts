import type { RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
	{
		path: "/",
		component: () => import("layouts/MainLayout.vue"),
		meta: { requiresAuth: true },
		children: [
			{ path: "", component: () => import("pages/IndexPage.vue") },
			{ path: "surveys", component: () => import("pages/SurveyList.vue") },
			{ path: "surveys/new", component: () => import("pages/SurveyForm.vue") },
			{
				path: "surveys/:id",
				component: () => import("pages/SurveyDetail.vue"),
				alias: "/survey/:id",
			},
			{
				path: "surveys/:id/edit",
				component: () => import("pages/SurveyForm.vue"),
				alias: "/survey/:id/edit",
			},
			{
				path: "surveys/:id/visualizations",
				component: () => import("pages/SurveyVisualizations.vue"),
				alias: "/survey/:id/visualizations",
			},
			{
				path: "surveys/:id/logs",
				component: () => import("pages/SyncLogs.vue"),
				alias: "/survey/:id/logs",
			},
			{ path: "logs", component: () => import("pages/SyncLogs.vue") },
		],
	},
	{
		path: "/login",
		component: () => import("pages/LoginPage.vue"),
	},
	{
		path: "/:catchAll(.*)*",
		component: () => import("pages/ErrorNotFound.vue"),
	},
];

export default routes;
