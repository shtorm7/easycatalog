from psycopg2 import connect
from psycopg2.extras import RealDictCursor

from .exceptions import (CatalogExists,
						CatalogNotFound,
						CatalogNotEmpty,
						PathException,
						ProductNotFound)
from .utils import format_dict, remove_null_attrs


class Catalog:

	def __init__(self, row_catalog, config, db_conf):
		self.row_catalog = row_catalog
		self.config = config
		self.db_conf = db_conf
		self.name = row_catalog['name']
		self.row_subcatalogs = row_catalog['subcatalogs']
		self.subcatalogs = {}
		for key in self.row_subcatalogs.keys():
			row_catalog = self.row_subcatalogs[key]
			if 'subcatalogs' in row_catalog:
				self.subcatalogs[key] = Catalog(row_catalog, config, db_conf)
			else:
				self.subcatalogs[key] = ProductCatalog(row_catalog, db_conf)

	def _save_cfg(func):
		def save(self, *args, **kwargs):
			func(self, *args, **kwargs)
			self.config.save_cfg()
		return save

	def is_subcatalog_exists(self, pathname):
		return pathname in self.subcatalogs.keys()

	@_save_cfg
	def create_subcatalog(self, pathname, name):
		if self.is_subcatalog_exists(pathname):
			raise CatalogExists(pathname)
		if not pathname.isalpha():
			raise PathException(pathname)
		cfgCat = {'name': name, 'subcatalogs': {}}
		self.row_catalog['subcatalogs'][pathname] = cfgCat
		self.subcatalogs[pathname] = Catalog(cfgCat, self.config, self.db_conf)

	@_save_cfg
	def create_prod_subcatalog(self, pathname, name, table_name, config):
		if self.is_subcatalog_exists(pathname):
			raise CatalogExists(pathname)
			return
		if not pathname.isalpha():
			raise PathException(pathname)
		cfgCat = {'name': name, 'config': config, 'table_name': table_name}
		self.subcatalogs[pathname] = ProductCatalog(cfgCat, self.db_conf, check=True)
		self.row_catalog['subcatalogs'][pathname] = cfgCat

	def get_subcatalog(self, pathname):
		subcatalog = self.subcatalogs.get(pathname, None)
		if subcatalog is None:
			raise CatalogNotFound(pathname)
		return subcatalog

	def get_by_path(self, path):
		if path == '' and path == '/':
			return self
		subcatalog = self
		for subpath in path.split('/'):
			if subpath != '':
				subcatalog = subcatalog.get_subcatalog(subpath)
		return subcatalog

	def get_pathnames(self):
		return self.subcatalogs.keys()

	def get_subcatalogs(self):
		return self.subcatalogs

	@_save_cfg
	def remove_subcatalog(self, pathname, recursive=False):
		subcatalog = self.get_subcatalog(pathname)
		if isinstance(subcatalog, Catalog):
			if recursive:
				for path in list(subcatalog.get_pathnames()):
					subcatalog.remove_subcatalog(path, recursive=True)
			elif subcatalog.get_subcatalogs() != {}:
				raise CatalogNotEmpty(pathname)
		if isinstance(subcatalog, ProductCatalog):
			subcatalog.remove_self()
		del subcatalog
		self.row_catalog['subcatalogs'].pop(pathname)
		self.subcatalogs.pop(pathname)

	def _row_catalog(self):
		return self._row_catalog


def _with_conn(cursor_factory=RealDictCursor):
	def decarator(func):
		def wraper(self, *args):
			conn = connect(**self.db_conf)
			try:
				with conn.cursor(cursor_factory=cursor_factory) as curs:
					result = func(self, curs, *args)
			except Exception as exp:
				conn.rollback()
				raise exp
			else:
				conn.commit()
				return result
			finally:
				conn.close()
		return wraper
	return decarator


class MainCatalog(Catalog):

	def __init__(self, config, db_conf, main_config):
		row_catalog = config.get_cfg()
		if row_catalog == {}:
			row_catalog['main_config'] = main_config
			row_catalog['name'] = 'Главная страница'
			row_catalog['subcatalogs'] = {}
			config.save_cfg()
		self.main_config = row_catalog['main_config']
		super().__init__(row_catalog, config, db_conf)
		self.__initializate()

	@_with_conn()
	def __initializate(self, curs):
		if self.main_config != '':
			ct_vars = ',' + self.main_config
		else:
			ct_vars = ''
		curs.execute(f'''CREATE TABLE 
						IF NOT EXISTS 
						main(id BIGSERIAL PRIMARY KEY, 
						table_name VARCHAR(255) NOT NULL
						{ct_vars});''')

	@_with_conn()
	def get_by_id(self, curs, id):
		curs.execute(f'''SELECT table_name FROM main 
						WHERE id={id};''')
		table_name = curs.fetchone()
		curs.execute(f'''SELECT * FROM main 
						WHERE id={id}
						INNER JOIN "{table_name}" ch 
						ON ch.id = main.id;''')
		product = curs.fetchone()
		if product is None:
			raise ProductNotFound(id)
		return product

	@_with_conn()
	def remove_by_id(self, curs, id):
		curs = self.conn.cursor()
		curs.execute(f'''SELECT table_name FROM main 
						WHERE id={id};''')
		table_name = curs.fetchone()
		curs.execute(f'''DELETE FROM main 
						WHERE main.id={id}';''')
		curs.execute(f'''DELETE FROM {table_name} as ch
						WHERE ch.id = {id};''')


class ProductCatalog:

	def __init__(self, row_catalog, db_conf, check=False):
		self.db_conf = db_conf
		self.name = row_catalog['name']
		self.table_name = row_catalog['table_name']
		self.config = row_catalog['config']
		self.__initializate(check)

	@_with_conn()
	def __initializate(self, curs, check):
		if self.config != '':
			ct_vars = ',' + self.config
		else:
			ct_vars = ''
		if check:
			curs.execute(f'''CREATE TABLE
						"{self.table_name}"
						(id INT NOT NULL UNIQUE
						{ct_vars});''')
		else:
			curs.execute(f'''CREATE TABLE 
						IF NOT EXISTS "{self.table_name}"
						(id INT NOT NULL UNIQUE
						{ct_vars});''')

	@_with_conn()
	def add_products(self, curs, products): 
		main_columns = ProductCatalog._get_columns(curs, 'main')
		catalog_columns = ProductCatalog._get_columns(curs, self.table_name)
		for product in products:
			product.pop('id', None)
			product['table_name'] = self.table_name
			ProductCatalog._insert_(curs, 'main', format_dict(product, main_columns))
			product['id'] = curs.fetchone()['id']
			ProductCatalog._insert_(curs, 
									self.table_name, 
									format_dict(product, catalog_columns))

	@_with_conn()
	def get_product(self, curs, id):
		curs.execute(f'''SELECT * FROM main 
						INNER JOIN "{self.table_name}" ch 
						ON ch.id = main.id
						WHERE ch.id={id}''')
		product = curs.fetchone()
		if product is None:
			raise ProductNotFound(id)
		return remove_null_attrs(product)

	@_with_conn()
	def get_product_main_specs(self, curs, id):
		curs.execute(f'''SELECT * FROM main ch
						WHERE ch.id={id}''')
		product = curs.fetchone()
		if product is None:
			raise ProductNotFound(id)
		return remove_null_attrs(product)

	@_with_conn()
	def get_product_specs(self, curs, id):
		curs.execute(f'''SELECT * FROM {self.table_name} ch
						WHERE ch.id={id}''')
		product = curs.fetchone()
		if product is None:
			raise ProductNotFound(id)
		return remove_null_attrs(product)

	@_with_conn()
	def get_products(self, curs):
		curs.execute(f'''SELECT * FROM main
						INNER JOIN "{self.table_name}" ch 
						ON ch.id = main.id;''')
		return curs.fetchall()

	@_with_conn()
	def get_products_main_specs(self, curs):
		curs.execute(f'''SELECT * FROM main 
						WHERE main.table_name='{self.table_name}';''')
		return curs.fetchall()

	@_with_conn()
	def get_columns(self, curs):
		return ProductCatalog._get_columns(curs, 'main') + ProductCatalog._get_columns(curs, self.table_name)

	@_with_conn()
	def remove_product(self, curs, id):
		curs.execute(f'''DELETE FROM {self.table_name} as ch
						WHERE ch.id = {id};''')
		curs.execute(f'''DELETE FROM main
						WHERE main.table_name = '{self.table_name}';''')

	@_with_conn()
	def remove_self(self, curs):
		curs.execute(f'''DROP TABLE "{self.table_name}";''')
		curs.execute(f'''DELETE FROM main
						WHERE main.table_name = '{self.table_name}';''')

	@staticmethod
	def _get_columns(curs, table_name):
		curs.execute(f'''SELECT column_name
						FROM INFORMATION_SCHEMA.COLUMNS 
						WHERE table_name = '{table_name}';''')
		columns = [column['column_name'] for column in curs.fetchall()]
		if columns == []:
			raise CatalogNotFound(table_name)
		print(columns)
		return columns

	@staticmethod
	def _insert_(curs, table_name, row_catalog):
		keys = row_catalog.keys()
		columns = ','.join(['"{}"'.format(k) for k in keys])
		values = ','.join(['%({})s'.format(k) for k in keys])
		query = f'''INSERT INTO "{table_name}" ({columns})
					VALUES ({values}) 
					RETURNING id;'''
		curs.execute(query, row_catalog)
