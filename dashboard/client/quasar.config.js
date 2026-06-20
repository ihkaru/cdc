import { configure } from "quasar/wrappers";

export default configure((/* ctx */) => ({
	productName: "FasihNexus",
	productDescription: "Unified Survey Automation & BI Dashboard for FASIH-SM",
	eslint: {
		warnings: true,
		errors: true,
	},
	boot: ["pinia", "axios"],
	css: ["app.scss"],
	extras: ["roboto-font", "material-icons"],
	build: {
		target: {
			browser: ["es2019", "edge88", "firefox78", "chrome87", "safari13.1"],
			node: "node20",
		},
		vueRouterMode: "history",
		vitePlugins: [],
		extendViteConf(viteConf) {
			// Externalize maplibre-gl so its Web Worker code is NOT bundled by Vite.
			// When bundled, Vite renames internal identifiers and breaks the Worker scope,
			// causing the infamous "Rt is not defined" error in the MapLibre Web Worker.
			viteConf.build = viteConf.build || {};
			viteConf.build.rollupOptions = viteConf.build.rollupOptions || {};
			viteConf.build.rollupOptions.external = ["maplibre-gl"];
			viteConf.build.rollupOptions.output = viteConf.build.rollupOptions.output || {};
			viteConf.build.rollupOptions.output.globals = {
				"maplibre-gl": "maplibregl",
			};
		},
		htmlVariables: {},
	},
	devServer: {
		port: process.env.FRONTEND_PORT || 9000,
		open: false,
		proxy: {
			"/api": {
				target: `http://127.0.0.1:${process.env.PORT || 3000}`,
				changeOrigin: true,
			},
			"/storage": {
				target: `http://127.0.0.1:${process.env.PORT || 3000}`,
				changeOrigin: true,
			},
		},
	},
	framework: {
		config: {
			dark: true, // We requested dark mode/premium
		},
		plugins: ["Notify", "Dialog", "Loading"],
	},
	animations: [],
	ssr: {
		pwa: false,
		prodPort: 3000,
		middlewares: ["render"],
	},
	pwa: {
		workboxMode: "generateSW",
		injectPwaMetaTags: true,
		swFilename: "sw.js",
		manifestFilename: "manifest.json",
		useCredentialsForManifestTag: false,
	},
	cordova: {},
	capacitor: {
		hideSplashscreen: true,
	},
	electron: {
		inspectPort: 5858,
		bundler: "packager",
		packager: {},
		builder: {
			appId: "fasih-dashboard-client",
		},
	},
	bex: {
		contentScripts: ["my-content-script"],
	},
}));
