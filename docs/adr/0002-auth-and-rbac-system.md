# ADR-0002: Secure Authentication & Spatie-Style RBAC Implementation

## Status
Proposed

## Context
Aplikasi CDC akan di-deploy secara publik. Diperlukan sistem keamanan yang membatasi akses API dan UI hanya untuk user terautentikasi dengan hak akses yang tepat. Data pegawai dari `data-pegawai.php` akan digunakan sebagai sumber identitas awal.

## Decision
1.  **Auth Engine**: Menggunakan **Better Auth** untuk manajemen sesi berbasis database (HttpOnly Cookies).
2.  **Identity Mapping**:
    *   Username: Email BPS (misal: `ihzakarunia@bps.go.id`).
    *   Initial Password: Email prefix (misal: `ihzakarunia`).
3.  **RBAC (Role-Based Access Control)**:
    *   Implementasi tabel `roles` dan `permissions` serta tabel pivot `users_roles` dan `roles_permissions`.
    *   Mekanisme middleware di Elysia untuk pengecekan role/permission pada level route (mirip Spatie).
    *   Default Admin: `ihzakarunia@bps.go.id`.
4.  **Frontend (Quasar)**:
    *   Menggunakan **Vue Router Guards** untuk memproteksi halaman.
    *   **Axios Interceptors** untuk menangani error 401 (Unauthorized) dan redirect ke login.
    *   Komponen UI (Menu/Button) akan menggunakan directive atau helper `v-can="'permission-name'"` untuk kontrol visibilitas.
5.  **User Management**:
    *   Hanya Admin yang memiliki akses ke menu User Management.
    *   Self-registration dimatikan total.

## Implementation Plan
### Backend (Elysia)
1.  [ ] Instalasi `@better-auth/elysia` dan konvergensi dengan Drizzle.
2.  [ ] Update `db/schema.ts` untuk menyertakan tabel `users`, `sessions`, `roles`, `permissions`.
3.  [ ] Buat script seeder `db/seed-pegawai.ts` yang mem-parsing `data-pegawai.php`.
4.  [ ] Implementasi middleware `withRole` dan `withPermission` di Elysia.

### Frontend (Quasar)
1.  [ ] Buat `LoginPage.vue` dengan desain premium Quasar.
2.  [ ] Implementasi `authStore` (Pinia) untuk menyimpan state user dan permissions.
3.  [ ] Setup Axios untuk menyertakan kredensial (cookies) pada setiap request.

## Verification
- [ ] User tanpa login tidak bisa mengakses `/api/surveys`.
- [ ] User non-admin tidak bisa mengakses `/api/users`.
- [ ] Logout membersihkan session di database dan cookie di browser.
