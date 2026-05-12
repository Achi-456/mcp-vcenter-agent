import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './hooks/**/*.{js,ts,jsx,tsx}',
    './lib/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        ops: {
          navy: '#1B3B6F',
          steel: '#2F6690',
          info: '#A3CEF1',
          beige: '#F6E4C8',
          cream: '#FFF8EE',
          ink: '#102033',
          muted: '#64748B',
        },
      },
      boxShadow: {
        card: '0 18px 45px rgba(27, 59, 111, 0.08)',
      },
    },
  },
  plugins: [],
}

export default config
