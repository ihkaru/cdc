import argon2 from "argon2";
import crypto from "crypto";
import { eq } from "drizzle-orm";
import fs from "fs";
import path from "path";
import { auth } from "../auth";
import { db } from "./index";
import * as schema from "./schema";

async function seed() {
	console.log("🌱 Starting Seeding Pegawai...");

	// 1. Create Roles & Permissions
	const [adminRole] = await db
		.insert(schema.roles)
		.values({
			id: crypto.randomUUID(),
			name: "admin",
			description: "Full access to system",
		})
		.onConflictDoUpdate({ target: schema.roles.name, set: { description: "Full access" } })
		.returning();

	const [userRole] = await db
		.insert(schema.roles)
		.values({
			id: crypto.randomUUID(),
			name: "user",
			description: "Standard access",
		})
		.onConflictDoUpdate({ target: schema.roles.name, set: { description: "Standard access" } })
		.returning();

	console.log("✅ Roles created.");

	// 2. Read and Parse data-pegawai.php
	// We relocated the file to dashboard/server/db/seed_data/ to ensure it's available in Docker build
	const possiblePaths = [
		path.join(__dirname, "seed_data", "data-pegawai.php"),
		path.join(process.cwd(), "server", "db", "seed_data", "data-pegawai.php"),
		path.join(process.cwd(), "docs", "references", "data-pegawai.php"), // fallback
	];

	let phpPath = "";
	for (const p of possiblePaths) {
		if (fs.existsSync(p)) {
			phpPath = p;
			break;
		}
	}

	if (!phpPath) {
		throw new Error(`Critical: data-pegawai.php not found in any of: ${possiblePaths.join(", ")}`);
	}

	const phpContent = fs.readFileSync(phpPath, "utf-8");

	// Regex for: "nama" => "...", "email" => "..."
	const pegawaiRegex = /"nama"\s*=>\s*"([^"]+)",[\s\S]*?"email"\s*=>\s*"([^"]+)"/g;
	let match;
	const pegawais = [];

	while ((match = pegawaiRegex.exec(phpContent)) !== null) {
		pegawais.push({
			name: match[1],
			email: match[2],
		});
	}

	console.log(`🔍 Found ${pegawais.length} employees.`);

	for (const p of pegawais) {
		if (!p.email || !p.name) continue;

		const passwordPrefix = p.email.split("@")[0]!;
		const hashedPassword = await argon2.hash(passwordPrefix);

		// Check if user exists
		const existing = await db.query.users.findFirst({
			where: eq(schema.users.email, p.email),
		});

		let userId;
		if (!existing) {
			try {
				// Use Better Auth API to sign up the user
				// This ensures password hashing is handled correctly by Better Auth
				await auth.api.signUpEmail({
					body: {
						email: p.email!,
						password: passwordPrefix!,
						name: p.name!,
					},
				});

				// Get the newly created user to get their ID
				const newUser = await db.query.users.findFirst({
					where: eq(schema.users.email, p.email!),
				});
				userId = newUser?.id;
				console.log(`👤 Created user: ${p.email}`);
			} catch (signupErr) {
				console.error(`❌ Failed to create user ${p.email}:`, signupErr);
				continue;
			}
		} else {
			userId = existing.id;
		}

		// Assign Role
		const isIhzakarunia = p.email === "ihzakarunia@bps.go.id";
		const targetRole = isIhzakarunia ? adminRole : userRole;

		// Link User to Role
		await db
			.insert(schema.usersToRoles)
			.values({
				userId: userId as string,
				roleId: targetRole!.id,
			})
			.onConflictDoNothing();

		if (isIhzakarunia) console.log("⭐ Assigned ADMIN role to ihzakarunia.");
	}

	console.log("🏁 Seeding completed successfully!");
	process.exit(0);
}

seed().catch((err) => {
	console.error("❌ Seeding failed:", err);
	process.exit(1);
});
