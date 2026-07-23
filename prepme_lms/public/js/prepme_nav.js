/**
 * prepme_nav — owned by prepme_lms.
 *
 * Adds a "Calendar" entry to the stock Frappe LMS sidebar that opens the
 * prepme_lms Study Hub SPA (/prepme/calendar). The LMS sidebar is rendered by a
 * compiled Vue app that can't be extended from outside, so this runs at runtime
 * (injected into the LMS shell by prepme_lms) and clones an existing sidebar
 * link for native styling, then retargets it.
 *
 * This is deliberately defensive but inherently coupled to the LMS sidebar
 * markup; if a future LMS release restructures its sidebar, this entry may stop
 * appearing (the calendar itself is always reachable at /prepme/calendar).
 */
(function () {
	'use strict'

	var TARGET = '/prepme/calendar'
	var LABEL = 'Calendar'
	var MARK = 'data-prepme-nav'
	// lucide "calendar" icon paths
	var CAL_ICON =
		'<path d="M8 2v4"/><path d="M16 2v4"/>' +
		'<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>'
	var KNOWN = /^(Home|Courses|Batches|Jobs|Statistics|Notifications|Programs|Quizzes|Assignments)$/

	function locate() {
		var buttons = [].slice.call(document.querySelectorAll('button'))
		for (var i = 0; i < buttons.length; i++) {
			var text = (buttons[i].textContent || '').trim()
			if (!KNOWN.test(text)) continue
			var wrapper = buttons[i].closest('.mx-2') || buttons[i].parentElement
			if (wrapper && wrapper.parentElement) {
				return { container: wrapper.parentElement, template: wrapper, label: text }
			}
		}
		return null
	}

	function inject() {
		var spot = locate()
		if (!spot) return false
		if (spot.container.querySelector('[' + MARK + ']')) return true // already present

		var node = spot.template.cloneNode(true)
		node.setAttribute(MARK, '1')

		// Relabel: swap the leaf text span that held the template's label.
		var spans = node.querySelectorAll('span')
		for (var i = 0; i < spans.length; i++) {
			if ((spans[i].textContent || '').trim() === spot.label && !spans[i].children.length) {
				spans[i].textContent = LABEL
			}
		}

		// Swap the icon.
		var svg = node.querySelector('svg')
		if (svg) svg.innerHTML = CAL_ICON

		// Drop any "active/selected" styling carried over from the clone.
		var btn = node.querySelector('button')
		if (btn) {
			btn.className = btn.className
				.replace(/bg-surface-selected/g, '')
				.replace(/shadow-sm/g, '')
				.trim()
			if (btn.className.indexOf('hover:bg-surface-gray-2') < 0) {
				btn.className += ' hover:bg-surface-gray-2'
			}
		}

		// Clones don't carry the Vue click handlers, so navigate ourselves.
		node.style.cursor = 'pointer'
		node.addEventListener(
			'click',
			function (e) {
				e.preventDefault()
				e.stopPropagation()
				window.location.href = TARGET
			},
			true,
		)

		spot.container.appendChild(node)
		return true
	}

	function ensure() {
		try {
			inject()
		} catch (e) {
			/* sidebar not ready or markup changed; ignore */
		}
	}

	// The sidebar renders on SPA boot and again when async settings load, which
	// can wipe an appended node. Poll across that window (inject() is idempotent),
	// then let navigation hooks keep it in place.
	var tries = 0
	var iv = setInterval(function () {
		tries++
		ensure()
		if (tries > 30) clearInterval(iv)
	}, 500)

	function hook(method) {
		var original = history[method]
		history[method] = function () {
			var result = original.apply(this, arguments)
			window.setTimeout(ensure, 50)
			return result
		}
	}
	hook('pushState')
	hook('replaceState')
	window.addEventListener('popstate', function () {
		window.setTimeout(ensure, 50)
	})

	if (document.readyState !== 'loading') ensure()
	else document.addEventListener('DOMContentLoaded', ensure)
})()
