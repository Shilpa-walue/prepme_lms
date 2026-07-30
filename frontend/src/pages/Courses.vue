<template>
	<div class="flex h-full flex-col overflow-hidden">
		<header
			class="sticky top-0 z-10 flex items-center gap-3 border-b bg-surface-white px-4 py-3"
		>
			<Button variant="ghost" label="Back to LMS" @click="backToLms">
				<template #prefix><ArrowLeft class="h-4 w-4" /></template>
			</Button>
			<div class="border-l pl-3">
				<h1 class="text-lg font-semibold text-ink-gray-9">Courses</h1>
				<p class="text-sm text-ink-gray-5">Browse the course catalogue</p>
			</div>
		</header>

		<div class="flex-1 overflow-y-auto p-4 sm:p-6">
			<div
				v-if="resource.loading && !resource.data"
				class="flex h-40 items-center justify-center text-ink-gray-5"
			>
				Loading courses…
			</div>

			<div v-else-if="resource.error" class="flex h-40 items-center justify-center">
				<div class="text-center">
					<div class="font-medium text-ink-gray-7">Could not load courses</div>
					<Button class="mt-3" variant="subtle" @click="resource.reload()">Try again</Button>
				</div>
			</div>

			<div
				v-else-if="courses.length === 0"
				class="flex h-40 items-center justify-center text-ink-gray-5"
			>
				No published courses yet.
			</div>

			<div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
				<router-link
					v-for="course in courses"
					:key="course.id"
					:to="{ name: 'CourseDetail', params: { courseId: course.id } }"
					class="group flex flex-col overflow-hidden rounded-lg border bg-surface-white transition hover:shadow-md"
				>
					<div class="aspect-video w-full overflow-hidden bg-surface-gray-2">
						<img
							v-if="course.image"
							:src="course.image"
							:alt="course.title"
							class="h-full w-full object-cover"
						/>
						<div
							v-else
							class="flex h-full w-full items-center justify-center text-ink-gray-4"
						>
							<BookOpen class="h-8 w-8" />
						</div>
					</div>
					<div class="flex flex-1 flex-col p-3">
						<div class="flex items-center gap-2">
							<Badge v-if="course.featured" theme="orange" variant="subtle">Featured</Badge>
							<span v-if="course.category" class="text-xs text-ink-gray-5">
								{{ course.category }}
							</span>
						</div>
						<h3 class="mt-1 font-medium text-ink-gray-9 group-hover:text-ink-gray-9">
							{{ course.title }}
						</h3>
						<p class="mt-1 line-clamp-2 text-sm text-ink-gray-6">
							{{ course.short_introduction }}
						</p>
						<div class="mt-auto flex items-center justify-between pt-3 text-xs text-ink-gray-5">
							<span>{{ course.stats.lesson_count }} lessons</span>
							<span v-if="course.pricing.is_paid" class="font-medium text-ink-gray-7">
								{{ course.pricing.currency }} {{ course.pricing.amount }}
							</span>
							<span v-else class="font-medium text-ink-green-3">Free</span>
						</div>
					</div>
				</router-link>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Badge, Button, createResource, usePageMeta } from 'frappe-ui'
import { computed } from 'vue'
import { ArrowLeft, BookOpen } from 'lucide-vue-next'

const backToLms = () => {
	window.location.href = '/lms'
}

const resource = createResource({
	url: 'prepme_lms.api.v1.course.get_courses',
	auto: true,
	cache: 'prepme-courses',
})

const courses = computed(() => resource.data?.courses || [])

usePageMeta(() => ({ title: 'Courses' }))
</script>
