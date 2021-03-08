FROM python:3.8-buster

ARG COMMIT_SHA
ENV COMMIT_SHA=${COMMIT_SHA}

RUN mkdir /stockbot
WORKDIR /stockbot

RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -R ta-lib ta-lib-0.4.0-src.tar.gz

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# alpine
# RUN apk update && \
#     apk add --virtual build-deps gcc g++ python3-dev musl-dev mariadb-dev zeromq-dev && \
#     apk add --no-cache mariadb-connector-c libxml2-dev libxslt-dev && \
#     pip install --no-cache-dir -r requirements.txt && \
#     apk del build-deps

ENTRYPOINT ["python", "manage.py"]