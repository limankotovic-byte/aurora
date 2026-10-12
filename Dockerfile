FROM nginx:stable-alpine
COPY index.html styles.css liquid-glass.css app.js /usr/share/nginx/html/
EXPOSE 80
