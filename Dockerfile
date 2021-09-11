ARG BYOND_VERSION=513.1542
FROM beestation/byond:${BYOND_VERSION}

WORKDIR /app

COPY compile.sh .

RUN adduser dmcompile && \
    chown -R  dmcompile:dmcompile /app

USER dmcompile

ENTRYPOINT ["bash", "/app/compile.sh"]
