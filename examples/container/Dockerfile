FROM python:3.12-alpine



WORKDIR /usr/src/app

COPY main.py /main.py
RUN set -eux; \
    # Install permanent system packages
    apk --update add --no-cache \
    # libexpat=2.6.0-r0 \
    coreutils \
    curl \
    bash \
    zip \
    git \
    jq 

RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    pkgconfig

RUN set -eux; \
    # Install ACME client
    python -m pip install --upgrade pip; \
    pip install --no-cache-dir pip-tools; \
    pip install --no-cache-dir \
    certbot \
    acme-dns-azure

RUN apk del .build-deps; \
    pip cache purge; \
    rm -rf ~/.cache /tmp/*

CMD ["python", "/main.py"]