import { route } from "quasar/wrappers";
import { useAuthStore } from "src/stores/auth";
import {
	createMemoryHistory,
	createRouter,
	createWebHashHistory,
	createWebHistory,
} from "vue-router";
import routes from "./routes";

export default route(({ store }: any) => {
	const createHistory = process.env.SERVER
		? createMemoryHistory
		: process.env.VUE_ROUTER_MODE === "history"
			? createWebHistory
			: createWebHashHistory;

	const Router = createRouter({
		scrollBehavior: () => ({ left: 0, top: 0 }),
		routes,
		history: createHistory(process.env.VUE_ROUTER_BASE),
	});

	Router.beforeEach(async (to) => {
		const auth = useAuthStore(store);
		console.log(
			`[Router] Navigating to: ${to.fullPath}, Authenticated: ${auth.isAuthenticated}, Initialized: ${auth.isInitialized}`,
		);

		if (!auth.isInitialized) {
			console.log("[Router] Auth not initialized, fetching session...");
			await auth.fetchSession();
			console.log(`[Router] Auth initialized. Authenticated: ${auth.isAuthenticated}`);
		}

		const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
		console.log(`[Router] Requires Auth: ${requiresAuth}`);

		if (requiresAuth && !auth.isAuthenticated) {
			console.log("[Router] Protected route & Not Authenticated -> Redirecting to /login");
			return {
				path: "/login",
				query: { redirect: to.fullPath },
			};
		}

		if (to.path === "/login" && auth.isAuthenticated) {
			console.log("[Router] Already Authenticated -> Redirecting to /");
			return { path: "/" };
		}

		console.log("[Router] Allowing navigation");
	});

	return Router;
});
