# Lightweight static file server for frontend
FROM nginx:alpine

# Copy static files
COPY . /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Healthcheck for static server
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget -q --spider http://localhost:80 || exit 1
