FROM node:22-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV API_URL=http://api:8000
RUN npm run build
CMD ["npm", "run", "start"]

