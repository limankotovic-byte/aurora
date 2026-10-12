FROM nginx:stable-alpine
COPY index.html styles.css liquid-glass.css glass-refraction.css glass-v05.css app.js /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/
EXPOSE 80
