/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark mode palette optimized for mobile
        dark: {
          bg: {
            primary: '#0f172a',    // Main background
            secondary: '#1e293b',  // Card background
            tertiary: '#334155',   // Hover states
          },
          text: {
            primary: '#f1f5f9',    // Main text
            secondary: '#cbd5e1',  // Muted text
            tertiary: '#94a3b8',   // Disabled text
          },
          border: '#334155',       // Borders
        },
        accent: {
          blue: '#3b82f6',
          green: '#10b981',
          amber: '#f59e0b',
          red: '#ef4444',
        }
      },
      spacing: {
        'safe-bottom': 'env(safe-area-inset-bottom, 0px)',
        'safe-top': 'env(safe-area-inset-top, 0px)',
      },
      minHeight: {
        'touch': '44px',  // Minimum touch target size
      },
      minWidth: {
        'touch': '44px',
      }
    },
  },
  plugins: [],
}
