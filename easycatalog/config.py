import os
import yaml

class Config:

	def __init__(self, path):
		self.path = path
		if os.path.exists(path):
			self.open_cfg()
		else:
			self.config = {}
			self.save_cfg()

	def get_cfg(self):
		return self.config

	def open_cfg(self):
		with open(self.path, 'r', encoding='utf-8') as cfgFile:
			self.config = yaml.full_load(cfgFile)

	def save_cfg(self):
		with open(self.path, 'w', encoding='utf-8') as cfgFile:
			yaml.dump(self.config,
				      cfgFile,
				      Dumper=yaml.Dumper,
				      default_flow_style=False,
				      allow_unicode=True)
