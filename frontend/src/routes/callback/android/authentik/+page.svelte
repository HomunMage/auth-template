<!-- src/routes/callback/android/authentik/+page.svelte -->
<!-- Trampoline: exchanges code for tokens, then redirects to app via deep link -->
<script lang="ts">
	import { onMount } from 'svelte';

	let status = $state('Signing you in...');

	onMount(async () => {
		const params = new URLSearchParams(window.location.search);
		const code = params.get('code');
		const state = params.get('state');
		const error = params.get('error');

		if (error) {
			status = `Authentication error: ${error}`;
			return;
		}

		if (!code || !state) {
			status = 'Missing authorization response';
			return;
		}

		// Extract PKCE verifier from state (format: nonce.verifier)
		const dotIndex = state.indexOf('.');
		if (dotIndex === -1) {
			status = 'Invalid state format';
			return;
		}
		const verifier = state.substring(dotIndex + 1);

		try {
			const apiBase = window.location.origin;
			const redirectUri = `${apiBase}/callback/android/authentik`;

			// Exchange code for tokens via backend
			const tokenResp = await fetch(`${apiBase}/api/login/authentik/token`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					code,
					redirect_uri: redirectUri,
					code_verifier: verifier
				})
			});

			if (!tokenResp.ok) {
				const err = await tokenResp.json().catch(() => ({ detail: 'Token exchange failed' }));
				status = err.detail || 'Token exchange failed';
				return;
			}

			const tokens = await tokenResp.json();

			// Get user role from backend
			let role: string | undefined;
			try {
				const meResp = await fetch(`${apiBase}/api/login/me`, {
					headers: { Authorization: `Bearer ${tokens.access_token}` }
				});
				if (meResp.ok) {
					const me = await meResp.json();
					role = me.role;
				}
			} catch {
				/* role stays undefined */
			}

			// Build login data and redirect to app via deep link
			const loginData = {
				provider: 'authentik',
				accessToken: tokens.access_token,
				refreshToken: tokens.refresh_token,
				idToken: tokens.id_token,
				expiresAt: tokens.expires_in
					? Math.floor(Date.now() / 1000) + tokens.expires_in
					: undefined,
				userInfo: tokens.userinfo,
				role
			};

			const deepLink = `authtemplate://auth?data=${encodeURIComponent(JSON.stringify(loginData))}`;
			status = 'Opening app...';
			window.location.href = deepLink;
		} catch (e) {
			status = e instanceof Error ? e.message : 'Authentication failed';
		}
	});
</script>

<div class="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
	<div class="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-xl">
		<div
			class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-4 border-blue-600"
		></div>
		<h2 class="text-xl font-semibold text-gray-800">{status}</h2>
	</div>
</div>
