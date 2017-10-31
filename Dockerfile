FROM alpine:3.6

MAINTAINER 2gis-io <io@2gis.ru>

RUN apk add --no-cache python py-pip py2-cffi make g++ python-dev openssl-dev libssl1.0 libffi-dev && pip install -r /tmp/es-gentle-restart/requirements.txt && \
	apk del g++ *-dev

ADD . /tmp/es-gentle-restart

WORKDIR /tmp/es-gentle-restart/

CMD ["bash", "-c"]
