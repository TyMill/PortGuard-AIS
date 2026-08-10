FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system portguard && useradd --system --gid portguard portguard
WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --upgrade pip && python -m pip install .

USER portguard
ENTRYPOINT ["portguard-ais"]
CMD ["--help"]
