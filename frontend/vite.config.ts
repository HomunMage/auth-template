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

	return {
		base: isProduction ? projectBaseWithSlash : '/',

		plugins: [tailwindcss(), sveltekit()],

		server: {
			host: '0.0.0.0',
			port: 3000
		},

		define: {
			'import.meta.env.VITE_BACKEND_URL': JSON.stringify(backendUrl),

			// Authentik OAuth
			'import.meta.env.VITE_AUTHENTIK_URL': JSON.stringify(process.env.AUTHENTIK_URL),
			'import.meta.env.VITE_AUTHENTIK_CLIENT_ID': JSON.stringify(process.env.AUTHENTIK_CLIENT_ID),
			'import.meta.env.VITE_AUTHENTIK_REDIRECT_URI': JSON.stringify(`${frontendUrl}/callback/authentik`),

			// Google OAuth
			'import.meta.env.VITE_GOOGLE_CLIENT_ID': JSON.stringify(process.env.GOOGLE_CLIENT_ID),
			'import.meta.env.VITE_GOOGLE_REDIRECT_URI': JSON.stringify(`${frontendUrl}/callback/google`)
		}
	};
});
