FROM registry.access.redhat.com/ubi9/python-312

# Database environment
ENV DB_URL=mongodb://localhost
ENV VECTORDB_URL=localhost
ENV VECTORDB_COLLECTION_NAME=None

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip
RUN pip3 --no-cache-dir install -r /tmp/requirements.txt

# Deploy the app
USER root
RUN mkdir -p /app && \
    chgrp -R 0 /app && \
    chmod -R g=u /app
COPY src/ /app

WORKDIR /app
USER 65532:65532

EXPOSE 8000

CMD ["chainlit", "run", "app.py"]
