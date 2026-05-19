import axios, { type AxiosInstance } from "axios";
import { Notify } from "quasar";
import { boot } from "quasar/wrappers";

declare module "@vue/runtime-core" {
	interface ComponentCustomProperties {
		$axios: AxiosInstance;
		$api: AxiosInstance;
	}
}

// Be careful when using SSR for client-side API calls
const api = axios.create({
	baseURL: "/api",
	withCredentials: true,
});

export default boot(({ app, router }) => {
	// Add interceptor for 401 Unauthorized
	api.interceptors.response.use(
		(response) => response,
		(error) => {
			if (error.response?.status === 401) {
				// Redirect to login if unauthorized
				if (router.currentRoute.value.path !== "/login") {
					Notify.create({
						type: "negative",
						message: "Session expired. Please login again.",
						position: "top",
					});
					router.push("/login");
				}
			}
			return Promise.reject(error);
		},
	);

	app.config.globalProperties.$axios = axios;
	app.config.globalProperties.$api = api;
});

export { api };
