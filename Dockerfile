FROM nginx:stable-alpine
COPY index.html styles.css liquid-glass.css glass-refraction.css aurora-landscape.svg app.js /usr/share/nginx/html/
EXPOSE 80
