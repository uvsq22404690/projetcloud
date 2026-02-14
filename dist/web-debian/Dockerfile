FROM debian:12
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx curl wget \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
