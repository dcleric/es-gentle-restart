REGISTRY = docker-hub.2gis.ru
REGISTRY_PATH = 2gis-io
IMAGE_NAME = es-gentle-restart
IMAGE_VERSION ?= latest
IMAGE_PATH = ${REGISTRY}/${REGISTRY_PATH}/${IMAGE_NAME}:${IMAGE_VERSION}
LATEST_PATH = ${REGISTRY}/${REGISTRY_PATH}/${IMAGE_NAME}:latest

build:
	docker build -f Dockerfile -t ${IMAGE_PATH} .
push:
	docker push ${IMAGE_PATH}
clean:
	docker rmi -f ${IMAGE_PATH}
push-latest:
	docker tag ${IMAGE_PATH} ${LATEST_PATH}
	docker push ${LATEST_PATH}
