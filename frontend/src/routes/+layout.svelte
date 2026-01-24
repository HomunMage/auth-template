<!--routes/+layout.svelte-->

<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<svelte:head></svelte:head>

<main>
	{@render children?.()}
</main>
