FROM python:3.12-slim
WORKDIR /app
COPY publisher/requirements.lock publisher/requirements.lock
RUN pip install --no-cache-dir -r publisher/requirements.lock
COPY publisher publisher
COPY scripts scripts
RUN useradd --uid 10001 --create-home publisher && mkdir /data && chown publisher /data
USER publisher
ENV PUBLISHER_DB=/data/publications.sqlite3
EXPOSE 8000
CMD ["python", "-m", "publisher.server"]
