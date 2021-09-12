FROM beestation/byond

WORKDIR /app

COPY compile.sh .

RUN adduser dmcompile && \
    chown -R  dmcompile:dmcompile /app

USER dmcompile

ENTRYPOINT ["bash", "/app/compile.sh"]
