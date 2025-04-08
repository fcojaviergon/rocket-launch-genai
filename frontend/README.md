# Rocket Launch GenAI Platform - Frontend

This directory contains the frontend application for the Rocket Launch GenAI Platform, built with Next.js 14+, TypeScript, and Tailwind CSS.

## Overview

The frontend provides a modern, responsive user interface for interacting with the platform's features, including:

- Document upload, processing, and management
- AI completions with configurable model parameters
- Conversational chat interfaces with persistent history
- Semantic search over processed documents
- User management and role-based access control
- Analytics dashboard for system monitoring

## Tech Stack

- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS + Radix UI
- **State Management:** React Context API & Hooks
- **Authentication:** NextAuth.js (JWT)
- **Real-time Updates:** Server-Sent Events (SSE)
- **API Communication:** Fetch API to the backend API Gateway
- **Testing:** Jest (unit) + Playwright (e2e)

## Project Structure

```
frontend/
├── public/                # Static assets
├── src/
│   ├── app/               # Next.js App Router (Pages & Layouts)
│   │   ├── (auth)/        # Authentication pages (Login, Register)
│   │   ├── api/           # Client-side API routes
│   │   ├── dashboard/     # Protected application routes
│   │   └── ...            # Other routes and layouts
│   ├── components/        # Reusable React components
│   │   ├── documents/     # Document-related components
│   │   ├── pipelines/     # Pipeline components
│   │   └── ui/            # Common UI components
│   ├── lib/               # Core libraries, hooks, types, utils
│   │   ├── api/           # API client
│   │   ├── hooks/         # Custom hooks
│   │   └── services/      # Frontend services
│   └── middleware.ts      # Next.js middleware (auth protection)
├── e2e/                   # End-to-end tests
├── .env.local             # Environment variables (development)
├── .env.production        # Environment variables (production)
├── next.config.js         # Next.js configuration
├── tailwind.config.ts     # Tailwind CSS configuration
├── tsconfig.json          # TypeScript configuration
├── jest.config.js         # Jest testing configuration
└── package.json           # Project dependencies and scripts
```

## Getting Started

-See the main installation guides:
- [Docker Installation Guide](../docs/DOCKER_INSTALLATION.md)
- [Local Installation Guide](../docs/LOCAL_INSTALLATION.md)

-See [Configuration Variables](../docs/CONFIGURATION.md) for details on environment variables.

### Running the Development Server

```bash
npm run dev
# or
yarn dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

### Building for Production

```bash
npm run build
# or
yarn build
```

### Starting the Production Server

```bash
npm start
# or
yarn start
```

## Available Scripts

- `dev`: Starts the development server
- `build`: Creates a production build
- `start`: Starts the production server
- `lint`: Runs ESLint for code quality
- `test`: Runs Jest unit tests
- `test:e2e`: Runs Playwright end-to-end tests

## Testing

- **Unit Tests:** Written with Jest and React Testing Library
  ```bash
  npm test
  ```

- **End-to-End Tests:** Written with Playwright
  ```bash
  npm run test:e2e
  ```

## Docker Deployment

A Dockerfile is provided for containerized deployment.

Refer to the main [Docker Installation Guide](../docs/DOCKER_INSTALLATION.md) for building and running with Docker Compose.

## Customization

The frontend is designed to be easily white-labeled:

- **Theming:** Modify `tailwind.config.ts` for colors and styling
- **Branding:** Replace assets in the `public/` directory
- **Components:** Adjust UI components in `src/components/ui`
- **Configuration:** Environment variables control backend connectivity and features

## Development Guidelines

- Follow TypeScript best practices for type safety
- Use the Next.js App Router patterns for routing
- Utilize the provided UI components for consistency
- Implement responsive design for all new interfaces 