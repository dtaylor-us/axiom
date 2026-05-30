# ── Stage 1: Build ──────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2: Serve ─────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Run as non-root user (required by ARCHITECTURE.md security rules)
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    chown -R appuser:appgroup \
      /var/cache/nginx \
      /var/log/nginx \
      /var/run \
      /run && \
    chmod -R 755 /var/cache/nginx /var/log/nginx /var/run /run

USER appuser

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
