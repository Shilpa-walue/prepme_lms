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
	{
		path: '/courses',
		name: 'Courses',
		component: () => import('@/pages/Courses.vue'),
	},
	{
		path: '/courses/:courseId',
		name: 'CourseDetail',
		component: () => import('@/pages/CourseDetail.vue'),
		props: true,
	},
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
