FROM python:3.8-buster

ARG GITHUB_SHA
ARG IMAGE_VERSION

RUN mkdir /stockbot
WORKDIR /stockbot

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# alpine
# RUN apk update && \
#     apk add --virtual build-deps gcc g++ python3-dev musl-dev mariadb-dev zeromq-dev && \
#     apk add --no-cache mariadb-connector-c libxml2-dev libxslt-dev && \
#     pip install --no-cache-dir -r requirements.txt && \
#     apk del build-deps

ENTRYPOINT ["python", "manage.py"]