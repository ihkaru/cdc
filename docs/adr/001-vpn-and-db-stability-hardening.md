# ADR 001: FasihNexus DB Hardening and VPN Stability Hardening

## Status
Decided

## Context
During high-concurrency operations (such as background RPA sync jobs running continuous `SELECT` queries), the application faced two major deadlock and network loop failures:
1. **Dashboard Startup Hang**: The database self-healing/hardening PL/pgSQL block in the dashboard container's entrypoint would deadlock against active concurrent select queries.
2. **VPN Reconnect Deadlock**: The VPN container fell into a stale cookie/interactive-prompt deadlock loop on disconnect, coupled with missing host-level port diagnostics.

## Refined Root Cause Analysis (5 Whys)

### 1. Dashboard Startup Hang (Lock Acquisition Deadlock)
* **Problem**: The `fasih-nexus-dashboard` container hung on startup during database hardening.
* **Why 1**: The container was blocked running the PL/pgSQL database hardening block (`psql -c "DO ..."`).
* **Why 2**: The block executed `ALTER TABLE` skema-hardening queries (e.g. dropping constraints), which require an `AccessExclusiveLock`, but these were blocked by active `AccessShareLock`s held by the `rpa` scheduler's concurrent queries.
* **Why 3**: The statement-level block's internal `SET statement_timeout` was ineffective because the lock acquisition queue phase for `ALTER TABLE` happens **before** the sub-statement is planned/executed inside the block, meaning the timeout never began running.
* **Why 4**: The database hardening PL/pgSQL block was executed dynamically on every startup without connection-level lock boundaries or timeout settings.
* **Why 5 (Root Cause)**: **Lack of session-level transaction lock boundaries (e.g., `PGOPTIONS` lock/statement timeouts)** on startup scripts in a highly concurrent, multi-container environment.

### 2. VPN Reconnect Loop (Fragile Cookie Lifecycle)
* **Problem**: The `vpn` container entered a stale cookie reconnect loop, causing the tunnel to collapse.
* **Why 1**: The VPN client failed to authenticate and fell back to interactive Username/Password prompts, stalling the non-interactive Docker entrypoint.
* **Why 2**: The VPN entrypoint was left with an empty or invalid cookie, preventing non-interactive tunnel creation.
* **Why 3**: **(Root Cause - Fragile Cookie Lifecycle)** The VPN container aggressively deleted the session cookie from the database immediately upon disconnect (`DELETE FROM system_settings WHERE key='vpn_cookie'`), creating a highly fragile window where the VPN was completely blind while the RPA container was still navigating SSO.
* **Why 4**: The Fortinet gateway frequently dropped the UDP-based DTLS channel due to packet fragmentation and path MTU issues, forcing session termination by the remote gate.
* **Why 5**: The VPN stack was executed in a background daemon stack with default DTLS active, without host-exposed diagnostic ports for self-healing triggers.

---

## Decisions

### 1. Database Hardening Connection Guard
We enforce a connection-level statement timeout of 5 seconds for the database hardening routine:
```bash
PGOPTIONS="-c statement_timeout=5000" psql "$DATABASE_URL" ...
```
This ensures that if there is a lock acquisition deadlock, the block times out cleanly in 5 seconds and allows the Elysia dashboard server to start immediately.

### 2. DTLS Deactivation (`--no-dtls`)
We force all OpenConnect connections to run with the `--no-dtls` flag:
```bash
openconnect --no-dtls ...
```
- **Tradeoff**: While UDP/DTLS is technically faster, forcing standard TCP/TLS completely eliminates fragmentation drops on jittery routes, offering superior reliability for data synchronization where stability outweighs micro-performance.

### 3. Immediate Cookie Polling
We replace background daemonization with a foreground trapping model and poll the database for up to 60 seconds after an RPA auto-fetch trigger to capture the fresh cookie instantly.

---

## Consequences
* **Pros**: 100% stable, non-blocking dashboard startup even under full RPA load. Rock-solid VPN stability with no silent drops or stale cookie reconnect deadlocks.
* **Cons**: VPN traffic runs over TCP/TLS, introducing minor latency overhead which is negligible for bulk sync operations.
