from pandas import DataFrame, ExcelFile, ExcelWriter
from io import BytesIO
import json
import yaml


def to_excel_as_file(data, path):
	df = DataFrame.from_dict(data)
	df.to_excel(path, index=False)


def to_excel(data):
	df = DataFrame.from_dict(data)
	buffer = BytesIO()
	with ExcelWriter(buffer) as writer:
		df.to_excel(writer, index=False)
	buffer.seek(0)
	return buffer


def to_excel_columns(columns):
	df = DataFrame(columns=columns)
	buffer = BytesIO()
	with ExcelWriter(buffer) as writer:
		df.to_excel(writer, index=False)
	buffer.seek(0)
	return buffer


def get_from_excel(data):
	xls = ExcelFile(data)
	df = xls.parse(xls.sheet_names[0])
	df = df.dropna(axis=1)
	return df.to_dict(orient='records')


def to_json(data):
	return json.dumps(data)


def get_from_json(data):
	return json.loads(data)


def to_yaml(data):
	return yaml.dumps(data)


def get_from_yaml(data):
	return yaml.loads(data)
