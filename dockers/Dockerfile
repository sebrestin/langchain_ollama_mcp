FROM python:3.12.12

RUN apt-get update && apt-get install -y zstd
RUN curl -fsSL https://ollama.com/install.sh | sh

COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp
