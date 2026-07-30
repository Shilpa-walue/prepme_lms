<template>
	<div class="flex h-full flex-col overflow-hidden">
		<header
			class="sticky top-0 z-10 flex flex-col justify-between gap-2 border-b bg-surface-white px-4 py-3 md:flex-row md:items-center"
		>
			<div class="flex items-center gap-3">
				<Button variant="ghost" label="Back to LMS" @click="backToLms">
					<template #prefix><ArrowLeft class="h-4 w-4" /></template>
				</Button>
				<div class="border-l pl-3">
					<h1 class="text-lg font-semibold text-ink-gray-9">My Classes</h1>
					<p class="text-sm text-ink-gray-5">Your scheduled live classes</p>
				</div>
			</div>
			<div class="flex items-center gap-3 text-sm text-ink-gray-6">
				<span v-if="summary">
					{{ summary.upcoming }} upcoming · {{ summary.total_events }} total
				</span>
				<Button variant="subtle" :loading="schedule.loading" @click="schedule.reload()">
					Refresh
				</Button>
			</div>
		</header>

		<div class="flex-1 overflow-hidden p-3 sm:p-5">
			<div
				v-if="schedule.loading && !schedule.data"
				class="flex h-full items-center justify-center text-ink-gray-5"
			>
				Loading your schedule…
			</div>

			<div v-else-if="schedule.error" class="flex h-full items-center justify-center">
				<div class="text-center">
					<div class="font-medium text-ink-gray-7">Could not load your schedule</div>
					<div class="mt-1 text-sm text-ink-gray-5">
						{{ schedule.error.messages?.[0] || schedule.error.message }}
					</div>
					<Button class="mt-3" variant="subtle" @click="schedule.reload()">Try again</Button>
				</div>
			</div>

			<div
				v-else-if="events.length === 0"
				class="flex h-full items-center justify-center"
			>
				<div class="text-center">
					<div class="font-medium text-ink-gray-7">No scheduled classes</div>
					<div class="mt-1 text-sm text-ink-gray-5">
						Live classes from your enrolled batches will appear here.
					</div>
				</div>
			</div>

			<Calendar v-else :config="config" :events="events" :onClick="openEvent" />
		</div>

		<Dialog v-model="showEvent" :options="dialogOptions">
			<template #body-content>
				<div v-if="activeEvent" class="space-y-4">
					<div class="text-sm text-ink-gray-6">{{ activeEvent.batch_title }}</div>

					<div class="grid grid-cols-2 gap-4 text-sm">
						<div>
							<div class="text-ink-gray-5">Date</div>
							<div class="text-ink-gray-8">{{ formatDate(activeEvent.fromDate) }}</div>
						</div>
						<div>
							<div class="text-ink-gray-5">Time</div>
							<div class="text-ink-gray-8">
								{{ activeEvent.fromTime }} – {{ activeEvent.toTime }}
								<span v-if="activeEvent.timezone" class="text-ink-gray-5">
									({{ activeEvent.timezone }})
								</span>
							</div>
						</div>
						<div>
							<div class="text-ink-gray-5">Duration</div>
							<div class="text-ink-gray-8">{{ activeEvent.duration }} minutes</div>
						</div>
						<div>
							<div class="text-ink-gray-5">Host</div>
							<div class="text-ink-gray-8">{{ activeEvent.host_name }}</div>
						</div>
					</div>

					<div v-if="activeEvent.description">
						<div class="text-sm text-ink-gray-5">Description</div>
						<div class="mt-0.5 text-sm text-ink-gray-8">{{ activeEvent.description }}</div>
					</div>

					<div v-if="activeEvent.join_url" class="pt-1">
						<a :href="activeEvent.join_url" target="_blank" rel="noopener noreferrer">
							<Button variant="solid">
								{{ activeEvent.is_host ? 'Start Class' : 'Join Class' }}
							</Button>
						</a>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { Button, Calendar, Dialog, createResource, usePageMeta } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import { ArrowLeft } from 'lucide-vue-next'

const dayjs = inject('$dayjs')

// Return to the stock LMS dashboard (a separate SPA, so a full navigation).
const backToLms = () => {
	window.location.href = '/lms'
}

const showEvent = ref(false)
const activeEvent = ref(null)

const config = {
	defaultMode: 'Month',
	isEditMode: false,
	eventIcons: {},
	allowCustomClickEvents: true,
	enableShortcuts: false,
}

const schedule = createResource({
	url: 'prepme_lms.api.v1.calendar.get_my_classes',
	auto: true,
	cache: 'prepme-my-class-schedule',
})

// The endpoint returns {events, summary, context}; createResource unwraps
// response.message into schedule.data, so these read straight off it.
const events = computed(() => schedule.data?.events || [])
const summary = computed(() => schedule.data?.summary || null)

// The Calendar invokes onClick with { e, calendarEvent }, not the event itself.
const openEvent = (payload) => {
	const clicked = payload?.calendarEvent || payload || {}
	activeEvent.value = events.value.find((e) => e.id === clicked.id) || clicked
	showEvent.value = true
}

const dialogOptions = computed(() => ({
	title: activeEvent.value?.title || 'Live Class',
	size: 'lg',
}))

const formatDate = (date) => (date ? dayjs(date).format('DD MMM YYYY') : '')

usePageMeta(() => ({ title: 'Calendar' }))
</script>
