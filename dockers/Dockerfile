FROM python:3.12.12

ARG USERNAME=sebrestin
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} --create-home ${USERNAME}

RUN apt-get update && apt-get install -y zstd
RUN curl -fsSL https://ollama.com/install.sh | sh

COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

USER ${USERNAME}
