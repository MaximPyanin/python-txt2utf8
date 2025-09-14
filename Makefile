IMAGE  ?= python-txt2utf8:latest
MOUNTS ?=
ARGS   ?=

.PHONY: build run

build:
	docker build -t $(IMAGE) .

run:
	docker run --rm $(MOUNTS) $(IMAGE) $(ARGS)