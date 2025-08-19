proto_dest=src/arctic_spa_dc/proto
proto_src=src/schemas

protos=$(wildcard $(proto_src)/*.proto)
py_protos=$(patsubst $(proto_src)/%.proto,$(proto_dest)/%_pb2.py,$(protos))

compile: $(py_protos)

$(proto_dest):
	mkdir -p $@

$(proto_dest)/%_pb2.py: $(proto_src)/%.proto | $(proto_dest)
	protoc --python_out=$(proto_dest) -I$(proto_src) $<

clean:
	rm -rf $(proto_dest)
	rm -rf dist/
