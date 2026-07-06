# --- Étape 1 : build de la librairie et de l'application Angular ---
FROM node:20-bookworm-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# La librairie ngx-chess-board (source locale) est compilée avant l'application.
RUN npx ng build ngx-chess-board && npx ng build

# --- Étape 2 : service des fichiers statiques par nginx ---
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

EXPOSE 80
