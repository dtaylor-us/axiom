import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'
import importPlugin from 'eslint-plugin-import'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    plugins: {
      import: importPlugin,
    },
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },

  // -----------------------------------------------------------------------
  // ADL-020: UI Service — Domain Structure (Soft enforcement)
  //
  // Enforces that source files under src/ only import from the six allowed
  // domain directories: views, components, hooks, api, store, types.
  // -----------------------------------------------------------------------
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['src/main.tsx', 'src/App.tsx'],
    rules: {
      'import/no-restricted-paths': ['warn', {
        zones: [
          // Prevent any src file from importing outside the defined domains
          // by blocking parent traversal beyond src/
          {
            target: './src/**/*',
            from: './src',
            except: [
              './views',
              './components',
              './hooks',
              './api',
              './store',
              './types',
              './test',
            ],
          },
        ],
      }],
    },
  },

  // -----------------------------------------------------------------------
  // ADL-021: UI Service — API Call Boundary (Soft enforcement)
  //
  // Prohibits direct use of the fetch function in views and components.
  // All HTTP calls must go through the api/ modules.
  // -----------------------------------------------------------------------
  {
    files: ['src/views/**/*.{ts,tsx}', 'src/components/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-globals': ['warn',
        {
          name: 'fetch',
          message: 'ADL-021: Direct fetch() calls are prohibited in views and components. Use api/ modules instead.',
        },
      ],
    },
  },

  // -----------------------------------------------------------------------
  // ADL-022: UI Service — State Management Boundary (Soft enforcement)
  //
  // Prohibits views from importing directly from the store. Views must
  // access state exclusively through hooks.
  // -----------------------------------------------------------------------
  {
    files: ['src/views/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': ['warn', {
        patterns: [
          {
            group: ['**/store', '**/store/*', '../store', '../store/*', '../../store', '../../store/*'],
            message: 'ADL-022: Views must not import from store directly. Access state through hooks instead.',
          },
        ],
      }],
    },
  },
])
