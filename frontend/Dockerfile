FROM node:20-alpine AS build

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

ARG VITE_ENABLE_LOGISTICS_MAP=false
ARG VITE_AMAP_JS_KEY=
ARG VITE_AMAP_SECURITY_JS_CODE=
ENV VITE_ENABLE_LOGISTICS_MAP=$VITE_ENABLE_LOGISTICS_MAP \
    VITE_AMAP_JS_KEY=$VITE_AMAP_JS_KEY \
    VITE_AMAP_SECURITY_JS_CODE=$VITE_AMAP_SECURITY_JS_CODE

RUN pnpm build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
