ARG BYOND_VERSION=513.1527
FROM beestation/byond:${BYOND_VERSION}

WORKDIR /app

COPY compile.sh .

ENTRYPOINT ["bash", "/app/compile.sh"]
