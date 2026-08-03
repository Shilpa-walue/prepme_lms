/**
 * Study Tutor loader — owned by prepme_lms.
 *
 * Injected into the stock Frappe LMS pages by an after_request hook
 * (prepme_lms.utils.inject.inject_study_tutor_script), which rewrites the HTML
 * response in memory — so it works on the standalone LMS SPA shell and on
 * managed hosts (Frappe Cloud) where the app files are read-only.
 *
 * This loader shows the vendor Study Tutor widget as a floating launcher ONLY on
 * course/lesson pages (/lms/courses/...), scoped to the current course, and
 * re-scopes as the user navigates the SPA.
 *
 * Config comes from this script tag's data-* attributes (set by the injector):
 *   data-widget-src   the vendor widget URL (from site_config study_tutor_widget_url)
 *   data-course-path  the course URL prefix (default /lms/courses/)
 *   data-title        the widget header title
 */
(function () {
	'use strict'

	var self = document.currentScript
	var WIDGET_SRC = (self && self.getAttribute('data-widget-src')) || ''
	var COURSE_PREFIX = (self && self.getAttribute('data-course-path')) || '/lms/courses/'
	var WIDGET_TITLE = (self && self.getAttribute('data-title')) || 'Study Tutor'

	if (!WIDGET_SRC) return // widget URL not configured → nothing to do

	var currentCourseId = null
	var scriptEl = null
	var hostEl = null
	var observer = null

	function courseIdFromPath() {
		var prefix = COURSE_PREFIX
		if (prefix.charAt(prefix.length - 1) !== '/') prefix += '/'
		var path = location.pathname
		if (path.indexOf(prefix) !== 0) return ''
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
		// Guard on scriptEl (set synchronously) so rapid SPA-boot syncs don't stack widgets.
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

	// React to SPA navigation (the LMS is a single-page app).
	function hook(method) {
		var original = history[method]
		history[method] = function () {
			var result = original.apply(this, arguments)
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
