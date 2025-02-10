
class director(object):
	def __init__(self, *args, host="0.0.0.0", port=61000, **kwargs):
		self.host = host
		self.port = port
		self._data = kwargs


Options = {
    "x": "Cell Types",
    "y": "Expression Counts",
    "title": "Violin Plot Example",
}

