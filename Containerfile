FROM registry.access.redhat.com/ubi9/ubi

# LLM spec
ENV OPENAI_API_BASE=localhost
ENV OPENAI_API_KEY=redhat

# MongoDB
ENV DB_URL=mongodb://localhost

# VectorDB
ENV VECTORDB_URL=localhost
ENV VECTORDB_COLLECTION_NAME=None

# Install python 
RUN yum update -y && \
    yum install -y \
    python3 \
    python3-devel && \
    rm -rf /var/cache/yum

# Install python libraries
COPY requirements.txt /tmp/requirements.txt
RUN pip3 --no-cache-dir install -r /tmp/requirements.txt

#Copy project files
RUN mkdir -p /app
COPY src/ /app

# Support arbitrary user ids
RUN chgrp -R 0 /app && \
    chmod -R g=u /app

WORKDIR /app

EXPOSE 8000

CMD ["chainlit", "run", "app.py"]
