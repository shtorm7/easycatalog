

class PathException(Exception):
	def __init__(self, path):
		self.message = f'Path \'{path}\' is not correct.'
		super().__init__(self.message)


class CatalogNotFound(Exception):
	def __init__(self, catalog):
		self.message = f'Catalog \'{catalog}\' not found.'
		super().__init__(self.message)


class CatalogExists(Exception):
	def __init__(self, catalog):
		self.message = f'Catalog \'{catalog}\' already exists.'
		super().__init__(self.message)


class CatalogNotEmpty(Exception):
	def __init__(self, catalog):
		self.message = f'Catalog \'{catalog}\' is not empty.'
		super().__init__(self.message)


class ProductNotFound(Exception):
	def __init__(self, id):
		self.message = f'Product with id {id} not found'
		super().__init__(self.message)
