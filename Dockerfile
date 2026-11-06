FROM python:3.12-slim-bookworm AS fonts

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir 'fonttools>=4,<5'
COPY scripts/prepare_fonts.py /prepare_fonts.py
RUN python /prepare_fonts.py

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src \
    RECEIPT_FONT_DIR=/usr/local/share/receipt-fonts

WORKDIR /app
COPY --from=fonts /usr/local/share/receipt-fonts /usr/local/share/receipt-fonts
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY src ./src
COPY README.md LICENSE .

EXPOSE 8000
ENV WEB_APP_HOST=0.0.0.0 WEB_APP_PORT=8000
CMD ["python", "-m", "uvicorn", "task_card_generator.web_app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test
RUN pip install pytest httpx
COPY tests ./tests
RUN python -m pytest -q

FROM runtime AS final
