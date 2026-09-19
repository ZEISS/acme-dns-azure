FROM python:3.12-alpine

ARG TIMEZONE=""
ARG LANGUAGE="en_US"
ARG ENCODING="UTF-8"

ENV TIMEZONE="${TIMEZONE}" \
    LANG="${LANGUAGE}.${ENCODING}" \
    LANGUAGE="${LANGUAGE}.${ENCODING}" \
    LC_ALL="${LANGUAGE}.${ENCODING}"

WORKDIR /usr/src/app

COPY main.py /main.py

RUN set -eux; \
    # Update ALL packages to latest available versions
    apk update && apk upgrade --no-cache; \
    # Install permanent system packages
    apk add --no-cache \
    coreutils \
    curl \
    bash \
    zip \
    git \
    jq \
    ; \
    # Install build-dependent system packages
    apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    pkgconfig \
    tzdata \
    ; \
    \
    # Set timezone
    if [ -n "${TIMEZONE}" ]; then \
    cp /usr/share/zoneinfo/${TIMEZONE} /etc/localtime; \
    echo "${TIMEZONE}" > /etc/timezone; \
    fi; \
    \
    # Install ACME client
    python -m pip install --upgrade pip; \
    pip install --no-cache-dir pip-tools \
    acme-dns-azure \
    ; \
    # Remove build-dependent system packages and files
    apk del .build-deps; \
    pip cache purge; \
    python -m pip uninstall --yes pip-tools pip setuptools; \
    rm -rf ~/.cache /tmp/*

CMD ["python", "/main.py"]