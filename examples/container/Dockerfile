FROM python:3.11

WORKDIR /usr/src/app

COPY main.py /main.py

RUN set -eux; \
    python -m pip install --upgrade pip; \
    pip install --no-cache-dir pip-tools; \
    pip install --no-cache-dir \
    certbot \
    acme-dns-azure

CMD ["python", "/main.py"]