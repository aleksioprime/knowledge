FROM python:3.12.11-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV TZ=Europe/Moscow

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tzdata \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chmod=755 entrypoint.sh /app/entrypoint.sh
COPY . .

ENTRYPOINT ["/app/entrypoint.sh"]