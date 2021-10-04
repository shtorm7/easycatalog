import os
from flask import Flask, request, redirect, url_for, render_template, send_file

from easycatalog.catalogs import MainCatalog, Catalog, ProductCatalog
from easycatalog.config import Config
from easycatalog import convert
from easycatalog import utils


CONFIG = Config('.config')
DB_SETTINGS = {
 			'dbname': os.environ.get('DB_NAME'),
 			'host': os.environ.get('DB_HOST'),
 			'user': os.environ.get('DB_USER'),
 			'password': os.environ.get('DB_PASSWORD'),
 			}
MAIN_TABLE_CONFIG = '''Название VARCHAR(25) NOT NULL, 
					Иконка VARCHAR(50), 
					Артикул INT NOT NULL UNIQUE, 
					Цена DECIMAL(10,2) NOT NULL, 
					Описание VARCHAR(500) NOT NULL'''
IMAGES_PATH = './images'


app = Flask(__name__)
main_catalog = MainCatalog(CONFIG, DB_SETTINGS, MAIN_TABLE_CONFIG)


@app.route('/')
def show_main_catalog():
	return redirect('catalog/')


@app.route('/catalog/')
@app.route('/catalog/<path:path>')
def show_catalog(path='/'):
	return_path = ''
	if path != '':
		if not path.endswith('/'):
			path += '/'
		return_path = '/'.join(path.split('/')[:-2])
	catalog = main_catalog.get_by_path(path)
	if isinstance(catalog, Catalog):
		subs = dict(sorted(catalog.get_subcatalogs().items(),
							key=lambda x: x[1].name))
		return render_template('catalog.html',
                               name=catalog.name,
                               path=path,
                               return_path=return_path,
                               subs=subs)
	else:
		products = catalog.get_products_main_specs()
		return render_template('product_catalog.html',
                               name=catalog.name,
                               path=path,
                               return_path=return_path,
                               products=products)


@app.route('/<path:path><int:id>')
def show_product(path, id):
	catalog = main_catalog.get_by_path(path)
	return render_template('product.html',
                           product=catalog.get_product_main_specs(id),
                           return_path=path,
                           specs=utils.remove_attrs(catalog.get_product_specs(id), ['id']))


@app.route('/image/<string:name>')
def get_image(name):
	image_path = os.path.join(IMAGES_PATH, name)
	if name != 'imagenotfound.png' and os.path.exists('server/' + image_path):
		return send_file(os.path.normpath(image_path), mimetype='image')
	else:
		return send_file('imagenotfound.png', mimetype='image')


@app.route('/get_excel/<path:path>')
def get_excel(path=''):
	catalog = main_catalog.get_by_path(path)
	if isinstance(catalog, ProductCatalog):
		products = utils.remove_attrs_list(catalog.get_products(), ['id', 'table_name', 'Иконка'])
		return send_file(convert.to_excel(products),
                         as_attachment=True,
                         download_name=catalog.name + '.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/get_excel_pattern/<path:path>')
def get_excel_pattern(path=''):
	catalog = main_catalog.get_by_path(path)
	if isinstance(catalog, ProductCatalog):
		columns = utils.remove_columns(catalog.get_columns(), ['id', 'table_name', 'Иконка'])
		return send_file(convert.to_excel_columns(columns),
                         as_attachment=True,
                         download_name=catalog.name + '_пример.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/add_products/<path:path>', methods=['GET', 'POST'])
def add_products(path=''):
	if request.method == 'POST':
		products = convert.get_from_excel(request.files['table'].read())
		main_catalog.get_by_path(path).add_products(products)
		return redirect(url_for('show_catalog', path=path))
	else:
		return render_template('add_products.html')


@app.route('/create_subcatalog/', methods=['GET', 'POST'])
@app.route('/create_subcatalog/<path:path>', methods=['GET', 'POST'])
def create_subcatalog(path=''):
	if request.method == 'POST':
		catalog = main_catalog.get_by_path(path)
		catalog.create_subcatalog(request.form['pathname'], request.form['name'])
		return redirect(url_for('show_catalog', path=path))
	else:
		return render_template('create_subcatalog.html')


@app.route('/create_prod_subcatalog/', methods=['GET', 'POST'])
@app.route('/create_prod_subcatalog/<path:path>', methods=['GET', 'POST'])
def create_prod_subcatalog(path=''):
	if request.method == 'POST':
		catalog = main_catalog.get_by_path(path)
		catalog.create_prod_subcatalog(request.form['pathname'],
                                       request.form['name'],
                                       request.form['table_name'],
                                       request.form['sql_query'])
		return redirect(url_for('show_catalog', path=path))
	else:
		return render_template('create_prod_subcatalog.html')


@app.route('/remove_subcatalog/', methods=['GET', 'POST'])
@app.route('/remove_subcatalog/<path:path>', methods=['GET', 'POST'])
def remove_subcatalog(path=''):
	if request.method == 'POST':
		subcatalog = request.form.get('select', None)
		if subcatalog is not None:
			catalog = main_catalog.get_by_path(path)
			catalog.remove_subcatalog(subcatalog, request.form.get('recursive') == 'on')
		return redirect(url_for('show_catalog', path=path))
	else:
		subs = main_catalog.get_by_path(path).get_subcatalogs()
		return render_template('remove_subcatalog.html', subs=subs)


if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0')
