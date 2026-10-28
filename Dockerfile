FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-liberation fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -r -u 1001 app && mkdir -p /app/media /app/staticfiles /data && chown -R app /app/media /app/staticfiles /data
USER app
RUN DJANGO_SECRET_KEY=build python manage.py collectstatic --noinput
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/saude/', timeout=4)" || exit 1
EXPOSE 8000
CMD ["sh", "deploy/start.sh"]
