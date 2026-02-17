// vite.config.ts
import { projectBaseWithSlash } from './myconfig.js';

import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';

const backendUrls = {
	development: 'http://localhost:5000',
	production: 'http://localhost:5000'
} as const;

const frontendUrls = {
	development: 'http://localhost:3000',
	production: 'http://localhost:3000'
} as const;

type BackendUrlMode = keyof typeof backendUrls;

export default defineConfig(({ mode }) => {
	const safeMode = mode as BackendUrlMode;
	const backendUrl = backendUrls[safeMode] || backendUrls.production;
	const frontendUrl = frontendUrls[safeMode] || frontendUrls.production;

	const isProduction = mode === 'production';
	const isMobile = process.env.VITE_PLATFORM === 'mobile';
	const prodUrl = process.env.PROD_URL || 'https://your-app.example.com';

	return {
		base: isProduction ? projectBaseWithSlash : '/',

		plugins: [tailwindcss(), sveltekit()],

		build: {
			rollupOptions: {
				// Mobile: bundle Capacitor plugins so they resolve in the WebView
				// Web: externalize them (they don't exist, code paths are guarded by isWeb())
				external: isMobile ? [] : ['@capacitor/core', '@capacitor/app']
			}
		},

		ssr: {
			external: ['@capacitor/core', '@capacitor/app']
		},

		server: {
			host: '0.0.0.0',
			port: 3000
		},

		define: {
			'import.meta.env.VITE_BACKEND_URL': JSON.stringify(backendUrl),

			// Authentik OAuth
			'import.meta.env.VITE_AUTHENTIK_URL': JSON.stringify(process.env.AUTHENTIK_URL),
			'import.meta.env.VITE_AUTHENTIK_CLIENT_ID': JSON.stringify(process.env.AUTHENTIK_CLIENT_ID),
			'import.meta.env.VITE_AUTHENTIK_REDIRECT_URI': JSON.stringify(
				isMobile ? `${prodUrl}/callback/android/authentik` : `${frontendUrl}/callback/authentik`
			),

			// Google OAuth
			'import.meta.env.VITE_GOOGLE_CLIENT_ID': JSON.stringify(process.env.GOOGLE_CLIENT_ID),
			'import.meta.env.VITE_GOOGLE_REDIRECT_URI': JSON.stringify(
				isMobile ? `${prodUrl}/callback/android/google` : `${frontendUrl}/callback/google`
			),

			// Platform: 'mobile' for Capacitor, 'browser' for web
			'import.meta.env.VITE_PLATFORM': JSON.stringify(process.env.VITE_PLATFORM || 'browser')
		}
	};
});
