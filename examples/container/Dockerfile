FROM python:3.12-alpine

ENV TIMEZONE=${TIMEZONE:-} \
    LANG=${LANGUAGE:-en_US}.${ENCODING:-UTF-8} \
    LANGUAGE=${LANGUAGE:-en_US}.${ENCODING:-UTF-8} \
    LC_ALL=${LANGUAGE:-en_US}.${ENCODING:-UTF-8}

WORKDIR /usr/src/app

COPY main.py /main.py

RUN set -eux; \
    # Install permanent system packages
    apk --update add --no-cache \
    libexpat=2.6.0-r0 \
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
    \
    # Remove build-dependent system packages and files
    apk del .build-deps; \
    pip cache purge; \
    rm -rf ~/.cache /tmp/*

CMD ["python", "/main.py"]