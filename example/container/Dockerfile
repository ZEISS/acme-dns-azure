FROM python:3.11-alpine

ENV TIMEZONE=${TIMEZONE:-} \
    LANG=${LANGUAGE:-en_US}.${ENCODING:-UTF-8} \
    LANGUAGE=${LANGUAGE:-en_US}.${ENCODING:-UTF-8} \
    LC_ALL=${LANGUAGE:-en_US}.${ENCODING:-UTF-8}

WORKDIR /usr/src/app


COPY entrypoint.sh /entrypoint.sh
RUN set -eux; \
    chmod +x /entrypoint.sh; \
    # Install permanent system packages
    apk --update add --no-cache \
    coreutils \
    curl \
    bash \
    zip \
    git \
    jq \
    ; \
    # Install build-dependent system packages
    apk add --no-cache --virtual .build-deps \
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
    pip install --no-cache-dir pip-tools; \
    # pip install --no-cache-dir acme-dns-azure; \
    \
    # Remove build-dependent system packages and files
    apk del .build-deps; \
    pip cache purge; \
    rm -rf ~/.cache /tmp/*

CMD [ "/bin/sh","-c","/entrypoint.sh" ]