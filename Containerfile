FROM registry.access.redhat.com/ubi9/python-312

ENV DB_URL=mongodb://localhost
ENV VECTORDB_URL=localhost
ENV VECTORDB_COLLECTION_NAME=None
ENV OPENAI_API_KEY=CHANGEME

USER root
RUN groupadd -g 65532 chatgroup && \
    useradd -u 65532 -g chatgroup chatuser

WORKDIR /app
RUN chown -R chatuser:chatgroup /app

COPY src/ .
COPY pdm.lock pyproject.toml Makefile .
RUN make install-pdm install-global

USER chatuser
EXPOSE 8000

CMD ["chainlit", "run", "app.py", "--host",  "0.0.0.0"]
