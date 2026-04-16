import js from '@eslint/js';

export default [
  {
    ignores: ['node_modules', 'public'],
  },
  js.configs.recommended,
  {
    files: ['tests/**/*.ts', 'tests/**/*.js'],
  },
];