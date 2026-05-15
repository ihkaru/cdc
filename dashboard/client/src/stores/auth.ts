import { defineStore } from 'pinia'
import { createAuthClient } from 'better-auth/vue'
import { api } from 'boot/axios'

// Better Auth Client Initialization
const authClient = createAuthClient({
  baseURL: window.location.origin + '/api/auth',
  advanced: {
    cookiePrefix: "cdc_auth",
  }
})

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as any,
    roles: [] as string[],
    isInitialized: false
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
    isAdmin: (state) => state.roles.includes('admin')
  },

  actions: {
    async fetchSession() {
      console.log('[AuthStore] Fetching session...');
      try {
        const res = await authClient.getSession()
        console.log('[AuthStore] Session response:', res);
        
        if (res?.data) {
          this.user = res.data.user
          console.log('[AuthStore] User found:', this.user.email);
          // FIX: Use authClient.$fetch instead of Axios to fetch roles.
          // Axios cannot reliably send HttpOnly cookies across the dev proxy
          // port boundary (9000 → 3000). authClient.$fetch uses the same
          // cookie transport mechanism as getSession() which is proven to work.
          const rolesRes = await authClient.$fetch<{ roles: string[] }>('/api/me/roles', {
            credentials: 'include'
          })
          this.roles = (rolesRes as any)?.roles ?? []
          console.log('[AuthStore] Roles fetched:', this.roles);
        } else {
          console.log('[AuthStore] No session data');
          this.user = null
          this.roles = []
        }
      } catch (err) {
        console.error('[AuthStore] Fetch session error:', err);
        // Don't block auth on roles failure — user is still authenticated
        // If roles fail, keep the user logged in with empty roles
        if (this.user) {
          console.warn('[AuthStore] Roles fetch failed but user is authenticated, proceeding with empty roles');
          this.roles = []
        } else {
          this.user = null
          this.roles = []
        }
      } finally {
        this.isInitialized = true
      }
    },

    async login(email: string, password: string) {
      console.log(`[AuthStore] Attempting login for ${email}...`);
      const { data, error } = await authClient.signIn.email({
        email,
        password
      })

      if (error) {
        console.error('[AuthStore] Login error:', error);
        throw error
      }
      
      console.log('[AuthStore] Login successful, updating user state...');
      this.user = data.user; // Update immediately
      
      console.log('[AuthStore] Refreshing session and roles...');
      await this.fetchSession()
      console.log('[AuthStore] Login flow complete. Final state:', { user: this.user?.email, roles: this.roles });
      return data
    },

    async logout() {
      console.log('[AuthStore] Logging out...');
      try {
        await authClient.signOut()
      } catch (e) {
        console.error('[AuthStore] Sign out error:', e)
      } finally {
        this.user = null
        this.roles = []
        this.isInitialized = false
        console.log('[AuthStore] State cleared, redirecting to login...')
        window.location.href = '/login'
      }
    }
  }
})
