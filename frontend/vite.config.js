import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import frappeui from 'frappe-ui/vite'

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [
		frappeui({
			frappeProxy: true,
			lucideIcons: true,
			jinjaBootData: true,
			buildConfig: {
				indexHtmlPath: '../prepme_lms/www/study_hub.html',
			},
		}),
		vue({
			script: {
				defineModel: true,
				propsDestructure: true,
			},
		}),
	],
	server: {
		host: '0.0.0.0',
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
			'tailwind.config.js': path.resolve(__dirname, 'tailwind.config.js'),
		},
	},
	optimizeDeps: {
		include: ['feather-icons', 'tailwind.config.js'],
	},
})
