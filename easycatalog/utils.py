

def format_dict(d, columns):
	return {column: d[column] for column in columns if column in d.keys()}


def remove_columns(columns_lst, columns):
	return [column for column in columns_lst if column not in columns]


def remove_null_attrs(d):
	return {k: v for k, v in d.items() if v is not None}


def remove_attrs(d, attrs):
	for attr in attrs:
		d.pop(attr, None)
	return d


def remove_attrs_list(list_d, attrs):
	for d in list_d:
		remove_attrs(d, attrs)
	return list_d
