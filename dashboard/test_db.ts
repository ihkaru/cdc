import postgres from "postgres";
const dbUrl = "postgresql://fasih:changeme_generate_random@localhost:5432/fasih_dashboard";
console.log("Connecting to", dbUrl);
const sql = postgres(dbUrl, { max: 1 });
async function test() {
    try {
        const res = await sql`SELECT 1 as connected`;
        console.log("Success:", res);
    } catch (e) {
        console.error("DB Error:", e);
    } finally {
        process.exit(0);
    }
}
test();
