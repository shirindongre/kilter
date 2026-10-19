# Convenience wrappers. On Windows without make, call the kilter commands directly (AIMS D-002).
.PHONY: test demo
test:
	pytest
demo:
	kilter demo
