import js from '@eslint/js';
import globals from 'globals';

export default [
  {
    ignores: ['node_modules', 'public'],
  },
  js.configs.recommended,
  {
    files: ['themes/**/*.js', 'tests/**/*.ts', 'tests/**/*.js'],
    languageOptions: {
      globals: globals.browser,
    },
  },
];