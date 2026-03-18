# Stage 1: Builder - Build Vue.js application with Vite
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Build arguments — baked into the JS bundle by Vite at build time
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

# Copy package files
COPY package.json package-lock.json* yarn.lock* ./

# Install dependencies
# Using --frozen-lockfile for reproducible builds when lockfile exists
RUN if [ -f yarn.lock ]; then \
      yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm install; \
    fi

# Copy application source code
COPY . .

# Build the application with Vite
# This creates the optimized production bundle in dist/
RUN npm run build

# Stage 2: Production - Serve with Nginx
FROM nginx:alpine

# Copy nginx configuration for SPA routing
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder stage
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Create non-root user if needed (nginx already runs as nginx user by default)
# Set proper permissions
RUN chmod -R 755 /usr/share/nginx/html

# Expose port for Nginx
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
