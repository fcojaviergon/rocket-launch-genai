FROM node:20-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application code
COPY . .

# Create public directory if it doesn't exist
RUN mkdir -p public

# Set environment variables
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_TYPESCRIPT_COMPILE_LINT=false
ENV TYPESCRIPT_SKIP_ERRORS=true

# Build the application
RUN echo "Starting build process..."
RUN npm run build:safe
RUN echo "Build completed, checking .next directory..."
RUN ls -la .next || echo "No .next directory found"

# Check for standalone directory and static files
RUN if [ -d ".next/standalone" ]; then \
      echo "Standalone directory exists, checking contents:"; \
      ls -la .next/standalone; \
    else \
      echo "No standalone directory found"; \
      mkdir -p .next/standalone; \
    fi

# Ensure static files directory exists and copy styles
RUN mkdir -p .next/static
RUN cp -R .next/static .next/standalone/.next/

# Copy src directory for CSS access
RUN mkdir -p .next/standalone/src
RUN cp -R src .next/standalone/

# Expose port 3000
EXPOSE 3000

# Start the application
CMD if [ -d ".next/standalone" ] && [ -f ".next/standalone/server.js" ]; then \
        echo "Starting standalone server..."; \
        cd .next/standalone; \
        ls -la; \
        node server.js; \
    elif [ -d ".next" ] && [ "$(ls -A .next)" ] && [ -f ".next/BUILD_ID" ]; then \
        echo "Starting in production mode with next start"; \
        npm start; \
    else \
        echo "No production build found, starting in development mode"; \
        npm run dev; \
    fi 