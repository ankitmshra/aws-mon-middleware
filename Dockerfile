FROM python:3.10.13-bookworm

ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY ./requirements.txt .

RUN apt-get update -y && \
    apt-get install -y netcat-traditional && \
    apt-get install -y libpq-dev postgresql-client && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY ./entrypoint.sh .
RUN chmod +x /code/entrypoint.sh

COPY . .

ENTRYPOINT ["/code/entrypoint.sh"]