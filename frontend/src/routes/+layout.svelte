<!--routes/+layout.svelte-->

<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.store';
	import { isWeb } from '$lib/platform';
	import { handleDeepLinkCallback } from '$lib/auth/auth.service';

	let { children } = $props();

	// Dedup deep link processing (cold start + appUrlOpen may both fire)
	let lastProcessedUrl = '';

	function processDeepLink(url: string) {
		if (!url.startsWith('authtemplate://auth')) return;
		if (url === lastProcessedUrl) return;
		lastProcessedUrl = url;

		try {
			const loginInfo = handleDeepLinkCallback(url);
			authStore.set(loginInfo);
			goto('/');
		} catch (e) {
			console.error('[DeepLink] Failed to parse auth data:', e);
			goto('/login');
		}
	}

	onMount(() => {
		if (!isWeb()) {
			// Direct import (bundled in mobile build, externalized in web build)
			import('@capacitor/app').then(({ App }) => {
				// Listen for deep links when app is resumed from background (warm start)
				App.addListener('appUrlOpen', ({ url }) => {
					processDeepLink(url);
				});

				// Cold start: app was killed by Android and relaunched via deep link.
				// appUrlOpen does NOT fire in this case — must check getLaunchUrl().
				App.getLaunchUrl().then((result) => {
					if (result?.url) {
						processDeepLink(result.url);
					}
				});
			});
		}
	});
</script>

<svelte:head></svelte:head>

<main>
	{@render children?.()}
</main>
