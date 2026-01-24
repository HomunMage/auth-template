<!-- src/routes/+page.svelte -->
<script lang="ts">
	import { authStore, logout } from '$lib/stores/auth.store';
</script>

<div class="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
	<div class="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
		{#if $authStore}
			<div class="text-center">
				<h1 class="mb-4 text-2xl font-bold text-gray-900">Welcome!</h1>
				<p class="mb-2 text-gray-600">Logged in as:</p>
				<p class="mb-4 font-semibold text-gray-800">{$authStore.userInfo?.email || $authStore.userInfo?.name || 'User'}</p>
				<p class="mb-6 text-sm text-gray-500">Provider: {$authStore.provider}</p>
				<button
					on:click={logout}
					class="rounded-lg bg-red-600 px-6 py-2 font-semibold text-white transition hover:bg-red-700"
				>
					Logout
				</button>
			</div>
		{:else}
			<div class="text-center">
				<h1 class="mb-4 text-2xl font-bold text-gray-900">Auth Template</h1>
				<p class="mb-6 text-gray-600">Please login to continue</p>
				<a
					href="/login"
					class="inline-block rounded-lg bg-blue-600 px-6 py-2 font-semibold text-white transition hover:bg-blue-700"
				>
					Go to Login
				</a>
			</div>
		{/if}
	</div>
</div>
