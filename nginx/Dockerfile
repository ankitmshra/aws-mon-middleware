FROM nginx:stable-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d
COPY tonserve.com.key /etc/tonserve.com.key
COPY tonserve.com.pem /etc/tonserve.com.pem

EXPOSE 80 443