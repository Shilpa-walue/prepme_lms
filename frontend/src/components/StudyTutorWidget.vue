<!--
	Study Tutor widget, mounted on prepme_lms's own course pages.

	Because this is prepme_lms's SPA, we control the page and can mount the
	vendor widget directly (no injection into the LMS app). The widget renders
	its own floating launcher + chat panel in a shadow DOM on <body>; this
	component injects/removes its script as the course changes.

	The widget URL comes from boot data (window.study_tutor_widget_url), set in
	site_config.json - so an https endpoint can be pointed at without a rebuild.
	When it's empty, the widget is disabled. Note: an http widget URL is blocked
	as mixed content on an https site, so a production (https) deployment needs
	an https widget endpoint for the launcher to appear.
-->
<script setup>
import { watch, onUnmounted } from 'vue'

const props = defineProps({
	courseId: { type: String, default: '' },
})

const WIDGET_SRC = (typeof window !== 'undefined' && window.study_tutor_widget_url) || ''
const WIDGET_TITLE = 'Study Tutor'

let currentCourseId = null
let scriptEl = null
let hostEl = null
let observer = null

function removeWidget() {
	if (observer) {
		observer.disconnect()
		observer = null
	}
	if (hostEl && hostEl.parentNode) hostEl.parentNode.removeChild(hostEl)
	if (scriptEl && scriptEl.parentNode) scriptEl.parentNode.removeChild(scriptEl)
	hostEl = null
	scriptEl = null
	currentCourseId = null
}

function mountWidget(courseId) {
	if (!WIDGET_SRC || !courseId) {
		removeWidget()
		return
	}
	// Guard on scriptEl (set synchronously) so re-renders don't stack widgets.
	if (courseId === currentCourseId && scriptEl) return

	removeWidget()
	currentCourseId = courseId

	observer = new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			for (const node of mutation.addedNodes) {
				if (node.nodeType === 1 && node.shadowRoot && node !== scriptEl) {
					hostEl = node
					observer.disconnect()
					observer = null
					return
				}
			}
		}
	})
	observer.observe(document.body, { childList: true })

	const script = document.createElement('script')
	script.src = WIDGET_SRC
	script.async = false
	script.setAttribute('data-course-id', courseId)
	script.setAttribute('data-title', WIDGET_TITLE)
	scriptEl = script
	document.body.appendChild(script)
}

watch(() => props.courseId, (id) => mountWidget(id), { immediate: true })
onUnmounted(removeWidget)
</script>

<template>
	<span aria-hidden="true" style="display: none" />
</template>
