import { Elysia } from "elysia";
import { auth } from "../auth";
import { db } from "../db";
import * as schema from "../db/schema";
import { eq } from "drizzle-orm";

export const authMiddleware = new Elysia({ name: "authMiddleware" })
    .derive(async ({ request, set }) => {
        const session = await auth.api.getSession({ headers: request.headers });
        
        if (!session) {
            return { user: null, roles: [] };
        }

        // Fetch roles from DB
        const userRoles = await db.query.usersToRoles.findMany({
            where: eq(schema.usersToRoles.userId, session.user.id),
            with: {
                role: true
            }
        });

        const roles = userRoles.map(ur => ur.role.name);

        return {
            user: session.user,
            roles: roles
        };
    })
export const requireAuth = (app: Elysia) => app
    .use(authMiddleware)
    .onBeforeHandle(({ user, set }: any) => {
        if (!user) {
            set.status = 401;
            return { error: "Unauthorized" };
        }
    });

export const requireAdmin = (app: Elysia) => app
    .use(authMiddleware)
    .onBeforeHandle(({ user, roles, set }: any) => {
        if (!user) {
            set.status = 401;
            return { error: "Unauthorized" };
        }
        if (!roles.includes("admin")) {
            set.status = 403;
            return { error: "Forbidden: Admin access required" };
        }
    });
