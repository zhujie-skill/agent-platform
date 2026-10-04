FROM node:22-slim
WORKDIR /workspace
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN corepack pnpm install --frozen-lockfile
COPY apps/web apps/web
RUN corepack pnpm --filter @agent-platform/web build
CMD ["corepack", "pnpm", "--filter", "@agent-platform/web", "start"]
