<template>
	<FrappeUIProvider>
		<div class="flex h-screen w-screen overflow-hidden bg-surface-white text-ink-gray-8">
			<!-- sidebar -->
			<aside
				class="hidden sm:flex w-56 shrink-0 flex-col border-r bg-surface-menu-bar px-3 py-4"
			>
				<div class="flex items-center gap-2 px-2 pb-4">
					<div
						class="flex h-8 w-8 items-center justify-center rounded-md bg-surface-gray-7 text-ink-white"
					>
						<GraduationCap class="h-5 w-5" />
					</div>
					<div class="text-base font-semibold text-ink-gray-9">Study Hub</div>
				</div>

				<nav class="flex flex-col gap-0.5">
					<router-link
						v-for="link in navLinks"
						:key="link.to"
						:to="link.to"
						class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm"
						:class="
							isActive(link)
								? 'bg-surface-selected font-medium text-ink-gray-9'
								: 'text-ink-gray-7 hover:bg-surface-gray-2'
						"
					>
						<component :is="link.icon" class="h-4 w-4" />
						{{ link.label }}
					</router-link>
				</nav>

				<div class="mt-auto px-2 text-xs text-ink-gray-5">
					{{ user || 'Not signed in' }}
				</div>
			</aside>

			<!-- main -->
			<main class="flex-1 overflow-hidden">
				<router-view />
			</main>
		</div>
	</FrappeUIProvider>
</template>

<script setup>
import { FrappeUIProvider } from 'frappe-ui'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { BookOpen, Calendar as CalendarIcon, GraduationCap } from 'lucide-vue-next'

const route = useRoute()

const navLinks = [
	{ label: 'Courses', to: '/courses', icon: BookOpen, names: ['Courses', 'CourseDetail'] },
	{ label: 'Calendar', to: '/calendar', icon: CalendarIcon, names: ['Calendar'] },
]

function isActive(link) {
	return link.names.includes(route.name)
}

// Session user from the cookie set by Frappe (null when Guest).
const user = computed(() => {
	const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
	const u = cookies.get('user_id')
	return u && u !== 'Guest' ? u : null
})
</script>
