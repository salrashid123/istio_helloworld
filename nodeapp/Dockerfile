FROM node:latest

COPY . /app
RUN cd /app && npm  install --silent
EXPOSE  8080
ARG VER=0
ENV VER=$VER
CMD ["node", "/app/app.js"]
