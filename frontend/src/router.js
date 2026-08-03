import { createRouter, createWebHistory } from 'vue-router'

const routes = [
	{
		path: '/',
		redirect: '/calendar',
	},
	{
		path: '/calendar',
		name: 'Calendar',
		component: () => import('@/pages/Calendar.vue'),
	},
	// Course browsing stays in the stock LMS (where the floating Study Tutor is
	// now injected). The prepme surface is the calendar.
	{
		path: '/:pathMatch(.*)*',
		redirect: '/calendar',
	},
]

const router = createRouter({
	// Served under /prepme by the study_hub www page + website_route_rules.
	history: createWebHistory('/prepme'),
	routes,
})

export default router
