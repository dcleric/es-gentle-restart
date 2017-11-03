REGISTRY = docker-hub.2gis.ru
REGISTRY_PATH = 2gis-io
IMAGE_NAME = es-gentle-restart
IMAGE_VERSION ?= latest
IMAGE_PATH = ${REGISTRY}/${REGISTRY_PATH}/${IMAGE_NAME}:${IMAGE_VERSION}
build:
	docker build -f Dockerfile -t ${IMAGE_PATH} .
push:
	docker push ${IMAGE_PATH}
clean:
	docker rmi -f ${IMAGE_PATH}
