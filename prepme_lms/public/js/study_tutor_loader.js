/**
 * Study Tutor loader — owned by prepme_lms.
 *
 * The Study Tutor chat widget must appear on the stock Frappe LMS course pages
 * (/lms/courses/<id> and their lesson pages). The LMS UI is a compiled Vue SPA
 * that cannot be extended by another app, so prepme_lms injects THIS small
 * loader into the LMS page shell (lms.html) via an after_migrate hook. The
 * loader then owns the widget's lifecycle:
 *
 *   - it watches SPA navigation (pushState / replaceState / popstate),
 *   - injects the vendor widget scoped to the current course,
 *   - re-scopes it when the course changes, and removes it off course pages.
 *
 * Everything here lives in prepme_lms; the only touch to the LMS app is the
 * one <script> include, which the migrate hook re-applies after every update.
 */
(function () {
	'use strict'

	// ── Config (overridable via data-* on this script tag) ──────────────
	var self = document.currentScript
	var WIDGET_SRC =
		(self && self.getAttribute('data-widget-src')) ||
		'http://15.207.249.35:8001/static/widget.js'
	var COURSE_PREFIX =
		(self && self.getAttribute('data-course-path')) || '/lms/courses/'
	var WIDGET_TITLE = (self && self.getAttribute('data-title')) || 'Study Tutor'

	// ── State ───────────────────────────────────────────────────────────
	var currentCourseId = null
	var scriptEl = null
	var hostEl = null // the shadow-DOM host the widget appends to <body>
	var observer = null

	function courseIdFromPath() {
		var prefix = COURSE_PREFIX
		if (prefix.charAt(prefix.length - 1) !== '/') prefix += '/'
		var path = location.pathname
		var i = path.indexOf(prefix)
		if (i !== 0) return ''
		var segment = path.slice(prefix.length).split('/')[0]
		if (!segment || segment === 'new') return ''
		try {
			return decodeURIComponent(segment)
		} catch (e) {
			return segment
		}
	}

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
		// Already mounted or still mounting this course? Do nothing. Guarding on
		// scriptEl (set synchronously on inject) — not hostEl, which only appears
		// after the async vendor script executes — prevents rapid SPA-boot
		// sync() calls from stacking several widgets before the first mounts.
		if (courseId === currentCourseId && scriptEl) return
		removeWidget()
		currentCourseId = courseId

		// The vendor widget appends a shadow-root <div> to <body>; capture it so
		// we can remove exactly that node when the course changes.
		observer = new MutationObserver(function (mutations) {
			for (var m = 0; m < mutations.length; m++) {
				var added = mutations[m].addedNodes
				for (var n = 0; n < added.length; n++) {
					var node = added[n]
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

		var s = document.createElement('script')
		s.src = WIDGET_SRC
		s.async = false
		s.setAttribute('data-course-path', COURSE_PREFIX)
		s.setAttribute('data-course-id', courseId)
		s.setAttribute('data-title', WIDGET_TITLE)
		scriptEl = s
		document.body.appendChild(s)
	}

	function sync() {
		var courseId = courseIdFromPath()
		if (courseId) mountWidget(courseId)
		else removeWidget()
	}

	// ── React to SPA navigation ─────────────────────────────────────────
	function hook(method) {
		var original = history[method]
		history[method] = function () {
			var result = original.apply(this, arguments)
			// let the router update location first
			window.setTimeout(sync, 0)
			return result
		}
	}
	hook('pushState')
	hook('replaceState')
	window.addEventListener('popstate', function () {
		window.setTimeout(sync, 0)
	})

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', sync)
	} else {
		sync()
	}
})()
