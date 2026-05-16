FROM oven/bun:1 AS build
WORKDIR /app

# 1. Install root dependencies
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile

# 2. Install client dependencies separately for caching
COPY client/package.json client/bun.lock* ./client/
RUN cd client && bun install

# 3. Copy source and build
COPY . .
RUN cd client && bunx quasar build

FROM oven/bun:1-slim
WORKDIR /app
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/client/dist/spa ./client/dist/spa
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/server ./server
COPY --from=build /app/package.json .
COPY --from=build /app/drizzle.config.ts .
COPY --from=build /app/entrypoint.sh .

RUN chmod +x entrypoint.sh
EXPOSE 3000
ENTRYPOINT ["./entrypoint.sh"]
