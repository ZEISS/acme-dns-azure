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
    jq \
    gcc \
    musl-dev \
    libffi-dev \
    certbot 

RUN set -eux; \

    # Install ACME client
    python -m pip install --upgrade pip; \
    pip install --no-cache-dir pip-tools; \
    pip install --no-cache-dir acme-dns-azure


CMD ["python", "/main.py"]