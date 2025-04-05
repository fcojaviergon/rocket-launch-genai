// Add any global setup for Jest tests here
import '@testing-library/jest-dom';

// Mock next/router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    refresh: jest.fn(),
    pathname: '/',
    query: {},
  }),
  usePathname: jest.fn().mockReturnValue('/'),
  useSearchParams: jest.fn().mockReturnValue(new URLSearchParams()),
}));

// Mock next-auth
jest.mock('next-auth/react', () => {
  const originalModule = jest.requireActual('next-auth/react');
  return {
    __esModule: true,
    ...originalModule,
    signIn: jest.fn(),
    signOut: jest.fn(),
    useSession: jest.fn(() => {
      return {
        data: { user: { name: 'Test User', email: 'test@example.com' } },
        status: 'authenticated',
      };
    }),
    getSession: jest.fn(() => Promise.resolve({ user: { name: 'Test User' } })),
  };
});

// Reset all mocks after each test
afterEach(() => {
  jest.clearAllMocks();
}); 