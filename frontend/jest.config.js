/** @type {import('jest').Config} */
const config = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testPathIgnorePatterns: ['<rootDir>/node_modules/', '<rootDir>/.next/', '<rootDir>/.next/standalone/'],
  modulePathIgnorePatterns: ['<rootDir>/.next/standalone/'],
  moduleNameMapper: {
    // Handle CSS imports
    '^.+\\.(css|sass|scss)$': 'identity-obj-proxy',
    // Handle module aliases (if using paths in tsconfig)
    '^@/(.*)$': '<rootDir>/$1',
  },
  transform: {
    // Use ts-jest for TypeScript and JavaScript files
    '^.+\\.(ts|tsx|js|jsx)$': ['ts-jest', {
      tsconfig: 'tsconfig.jest.json',
    }],
  },
  transformIgnorePatterns: [
    '/node_modules/(?!(@testing-library)/)',
  ],
  collectCoverageFrom: [
    'components/**/*.{ts,tsx}',
    'store/**/*.{ts,tsx}',
    'lib/**/*.{ts,tsx}',
    'hooks/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
  ],
  coverageThreshold: {
    global: {
      branches: 50,
      functions: 50,
      lines: 50,
      statements: 50,
    },
  },
};

module.exports = config;
