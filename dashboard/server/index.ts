import { Elysia } from "elysia";
import { cors } from "@elysiajs/cors";
import { staticPlugin } from "@elysiajs/static";
import { surveysRoutes } from "./routes/surveys";
import { assignmentsRoutes } from "./routes/assignments";
import { logsRoutes } from "./routes/logs";
import { syncRoutes } from "./routes/sync";
import { labelsRoutes } from "./routes/labels";
import { visualizationsRoutes } from "./routes/visualizations";

const app = new Elysia()
    .use(cors())
    .use(surveysRoutes)
    .use(assignmentsRoutes)
    .use(logsRoutes)
    .use(syncRoutes)
    .use(labelsRoutes)
    .use(visualizationsRoutes)
    // Serve static files and fallback to index.html for SPA
    .get("*", async ({ path }) => {
        const filePath = path === "/" ? "/index.html" : path;
        const file = Bun.file(`client/dist/spa${filePath}`);

        if (await file.exists()) return file;

        // Return index.html for non-existent routes (SPA fallback)
        // unless it looks like an asset that SHOULD have existed
        if (path.startsWith("/assets/") || path.includes(".")) {
            return new Response("Not Found", { status: 404 });
        }

        return Bun.file("client/dist/spa/index.html");
    })
    .listen(3000);

console.log(`🚀 Dashboard running at http://localhost:${app.server?.port}`);
