<template>
	<FrappeUIProvider>
		<div class="h-screen w-screen overflow-hidden bg-surface-white text-ink-gray-8">
			<router-view />
		</div>
	</FrappeUIProvider>
</template>

<script setup>
import { FrappeUIProvider } from 'frappe-ui'
</script>
