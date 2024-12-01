FROM python:3.11.0-slim
RUN python -m pip install --upgrade pip

RUN apt-get update && \
    apt-get install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata


RUN apt-get update && apt-get install -y wget
RUN pip install -U pip setuptools wheel
RUN pip install poetry
RUN poetry config virtualenvs.create false
COPY ./ /application
RUN pip install pydantic[dotenv]
RUN pip install pydantic[email]


ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

WORKDIR /application
RUN poetry install --no-root
ENV PYTHONPATH "${PYTHONPATH}:/application"
EXPOSE 8000
COPY --chown=www-data:www-data docker/dev/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]