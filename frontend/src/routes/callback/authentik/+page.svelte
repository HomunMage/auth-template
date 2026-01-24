<!-- src/routes/callback/authentik/+page.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.store';
	import { handleOAuthCallback } from '$lib/auth/auth.service';

	let error = '';
	let loading = true;

	onMount(async () => {
		try {
			const params = new URLSearchParams(window.location.search);
			const code = params.get('code');
			const state = params.get('state');
			const errorParam = params.get('error');

			if (errorParam) {
				throw new Error(errorParam);
			}

			if (!code || !state) {
				throw new Error('Missing authorization response');
			}

			const loginInfo = await handleOAuthCallback('authentik', code, state);
			authStore.set(loginInfo);
			goto('/');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Authentication failed';
		} finally {
			loading = false;
		}
	});
</script>

<div class="flex min-h-screen items-center justify-center bg-gray-50 p-4">
	<div class="w-full max-w-md rounded-lg bg-white p-8 text-center shadow-lg">
		{#if loading}
			<div
				class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-4 border-blue-600"
			></div>
			<h2 class="text-xl font-semibold">Signing you in…</h2>
			<p class="mt-2 text-gray-600">Please wait</p>
		{:else if error}
			<div class="mb-4 text-lg font-semibold text-red-600">Authentication Failed</div>
			<p class="mb-6 text-gray-700">{error}</p>
			<button
				on:click={() => goto('/login')}
				class="rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700"
			>
				Back to Login
			</button>
		{/if}
	</div>
</div>
