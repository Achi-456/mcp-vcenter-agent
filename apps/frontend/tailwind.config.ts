import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        console: {
          bg: '#07100d',
          panel: '#0d1b17',
          line: '#1f3d34',
          glow: '#38f8a7',
        },
      },
    },
  },
  plugins: [],
}

export default config

