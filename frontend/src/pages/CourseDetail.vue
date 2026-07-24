<template>
	<div class="flex h-full flex-col overflow-hidden">
		<header class="sticky top-0 z-10 flex items-center gap-3 border-b bg-surface-white px-4 py-3">
			<Button variant="ghost" @click="$router.push({ name: 'Courses' })">
				<template #icon><ArrowLeft class="h-4 w-4" /></template>
			</Button>
			<div class="min-w-0">
				<h1 class="truncate text-lg font-semibold text-ink-gray-9">
					{{ course?.title || 'Course' }}
				</h1>
				<p v-if="course" class="text-sm text-ink-gray-5">
					{{ summary?.total_chapters }} chapters · {{ summary?.total_lessons }} lessons
				</p>
			</div>
		</header>

		<div class="flex-1 overflow-y-auto">
			<div
				v-if="resource.loading && !resource.data"
				class="flex h-40 items-center justify-center text-ink-gray-5"
			>
				Loading course…
			</div>

			<div v-else-if="resource.error" class="flex h-40 items-center justify-center">
				<div class="text-center">
					<div class="font-medium text-ink-gray-7">Could not load this course</div>
					<div class="mt-1 text-sm text-ink-gray-5">
						{{ resource.error.messages?.[0] || resource.error.message }}
					</div>
					<Button class="mt-3" variant="subtle" @click="resource.reload()">Try again</Button>
				</div>
			</div>

			<div v-else-if="course" class="mx-auto max-w-4xl p-4 sm:p-6">
				<!-- overview -->
				<div class="flex flex-col gap-4 sm:flex-row">
					<img
						v-if="course.image"
						:src="course.image"
						:alt="course.title"
						class="h-40 w-full rounded-lg object-cover sm:w-64"
					/>
					<div class="flex-1">
						<div class="flex flex-wrap items-center gap-2">
							<Badge v-for="tag in course.tags" :key="tag" variant="subtle">{{ tag }}</Badge>
						</div>
						<p class="mt-2 text-ink-gray-7">{{ course.short_introduction }}</p>
						<div class="mt-3 flex flex-wrap gap-4 text-sm text-ink-gray-5">
							<span>{{ course.stats.enrollments }} enrolled</span>
							<span>{{ course.stats.lesson_count }} lessons</span>
							<span v-if="course.instructors.length">
								By {{ course.instructors.map((i) => i.full_name).join(', ') }}
							</span>
						</div>
					</div>
				</div>

				<!-- curriculum -->
				<h2 class="mt-8 mb-3 text-base font-semibold text-ink-gray-9">Course content</h2>
				<div class="space-y-3">
					<div
						v-for="chapter in chapters"
						:key="chapter.id"
						class="overflow-hidden rounded-lg border"
					>
						<div class="bg-surface-gray-2 px-4 py-2.5 font-medium text-ink-gray-8">
							{{ chapter.index }}. {{ chapter.title }}
							<span class="ml-1 text-xs font-normal text-ink-gray-5">
								({{ chapter.lesson_count }} lessons)
							</span>
						</div>
						<ul class="divide-y">
							<li
								v-for="lesson in chapter.lessons"
								:key="lesson.id"
								class="flex items-center gap-3 px-4 py-2.5 text-sm"
							>
								<component
									:is="lesson.videos && lesson.videos.length ? PlayCircle : FileText"
									class="h-4 w-4 shrink-0 text-ink-gray-5"
								/>
								<span class="flex-1 text-ink-gray-8">{{ lesson.title }}</span>
								<Lock v-if="lesson.content_locked" class="h-3.5 w-3.5 text-ink-gray-4" />
								<span v-else-if="lesson.videos?.length" class="text-xs text-ink-gray-4">
									video
								</span>
							</li>
						</ul>
					</div>
				</div>
			</div>
		</div>

		<!-- Study Tutor, scoped to this course (config-driven; see component) -->
		<StudyTutorWidget :course-id="courseId" />
	</div>
</template>

<script setup>
import { Badge, Button, createResource, usePageMeta } from 'frappe-ui'
import { computed } from 'vue'
import { ArrowLeft, FileText, Lock, PlayCircle } from 'lucide-vue-next'
import StudyTutorWidget from '@/components/StudyTutorWidget.vue'

const props = defineProps({
	courseId: { type: String, required: true },
})

const resource = createResource({
	url: 'prepme_lms.api.v1.course.get_course',
	auto: true,
	cache: ['prepme-course', props.courseId],
	makeParams: () => ({ course: props.courseId, include_content: 0 }),
})

const course = computed(() => resource.data?.course || null)
const chapters = computed(() => resource.data?.chapters || [])
const summary = computed(() => resource.data?.summary || null)

usePageMeta(() => ({ title: course.value?.title || 'Course' }))
</script>
