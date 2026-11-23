FROM node:24-alpine
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 API_INTERNAL_URL=http://backend:8000
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
USER node
CMD ["npm", "start"]
