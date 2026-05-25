# ──────────────────────────────────────────────
# Dockerfile — Angular Frontend (Price Intelligence)
# Multi-stage build : Node 20 → nginx:alpine
# ──────────────────────────────────────────────
# Build : docker build -t price-intel-frontend ./frontend
# Run   : Géré par docker-compose
# ──────────────────────────────────────────────

# ═══════ STAGE 1 : BUILD ═══════
FROM node:20-alpine AS builder

WORKDIR /app

# Copier les fichiers de dépendances du projet Angular
COPY sportsintelligence/package.json sportsintelligence/package-lock.json ./

# Installer les dépendances
RUN npm ci --ignore-scripts

# Copier le code source Angular
COPY sportsintelligence/ .

# Build de production (SPA mode — sans SSR)
RUN npm run build -- --configuration production

# ═══════ STAGE 2 : SERVE ═══════
FROM nginx:1.25-alpine

# Remove the stock nginx welcome page so it can't shadow index.csr.html
RUN rm -f /usr/share/nginx/html/index.html

# Copier le bundle Angular buildé dans nginx
# Angular 21 avec @angular/build output le bundle dans dist/<project-name>/browser/
COPY --from=builder /app/dist/sportsintelligence/browser /usr/share/nginx/html

# Configuration nginx pour Angular (SPA routing)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Healthcheck — nginx:alpine ships busybox wget (no curl)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O - http://127.0.0.1:80/ > /dev/null 2>&1 || exit 1
