# -*- coding: utf-8 -*-

import sys
from cfgpy.tools import FMT_INI, Cfg 
import re
import psycopg2
import psycopg2.extras

MYNAME = 'pgdbpy'
DEFAULT_PORT = 5432
DEFAULT_CURSORTYPE = 'tuple'
DEFAULT_DATA_WINDOW_SIZE = 0
""" 'postgresql+psycopg2://scott:tiger@localhost/mydatabase' """
dburl_pattern = re.compile(r'^([^:]+)://([^:]+):([^@]+)@([^/]+)/([^\s]+)')
insertion_pattern = re.compile(r'^insert.*$', re.IGNORECASE)
whereclause_pattern = re.compile(	r'\b({0})\b'.format('where'), 
									flags=re.IGNORECASE)

class PgDbPy(object):

	def __init__(self, cfg, datasource_identifier, cursortype=None):

		if not type(cfg).__name__ == 'CfgPy' and not type(cfg).__name__ == 'Cfg':
			raise ValueError('expecting configuration to be a Cfg or CfgPy object')
			sys.exit(1)

		self.cfg = cfg
		cfg_dict = cfg.get_config()
		"""
		 expecting the configuration to either provide
		 datasource url ala sqlalchemy conn, 
		  'sql_alchemy_conn'
		  'dburl'
		  'datasource_url'
		 or provide individual elements ala psycopg2
		  'dbname' 'host' 'user' 'password'
		"""

		if not cfg_dict[datasource_identifier]:
			msg = 'datasource identifier not found in configuration: {}'
			raise ValueError(msg.format(datasource_identifier))
			sys.exit(1)

		self.data_window_size = DEFAULT_DATA_WINDOW_SIZE
		if MYNAME in cfg.cfg_dict:
			module_cfgdict = cfg.cfg_dict[MYNAME]
			if 'data_window_size' in module_cfgdict:
				self.data_window_size = int(module_cfgdict['data_window_size'])

		datasource = cfg_dict[datasource_identifier]

		if 'dburl' in datasource:

			m = dburl_pattern(datasource['dburl'])
			if m:
				self.enginetype = m.group(1)
				self.user = m.group(2)
				self.password = m.group(3)
				self.host = m.group(4)
				self.dbname = m.group(5)
			else:
				raise ValueError('failed to parse dburl form')

		elif 'datasource_url' in datasource:

			m = dburl_pattern(datasource['datasource_url'])
			if m:
				self.enginetype = m.group(1)
				self.user = m.group(2)
				self.password = m.group(3)
				self.host = m.group(4)
				self.dbname = m.group(5)
			else:
				raise ValueError('failed to parse datasource_url form')

		elif 'sql_alchemy_conn' in datasource:

			m = dburl_pattern(datasource['sql_alchemy_conn'])
			if m:
				self.enginetype = m.group(1)
				self.user = m.group(2)
				self.password = m.group(3)
				self.host = m.group(4)
				self.dbname = m.group(5)
			else:
				raise ValueError('failed to parse sql_alchemy_conn form')

		else:
			if 'dbname' in datasource:
				self.dbname = datasource['dbname']
			else:
				self.dbname = datasource_identifier

			if 'user' in datasource:
				self.user = datasource['user']
			if 'host' in datasource:
				self.host = datasource['host']
			if 'port' in datasource:
				self.port = datasource['port']
			if 'password' in datasource:
				self.password = datasource['password']

		if not 'port' in self.__dict__:
			self.port = DEFAULT_PORT

		dsn = "dbname='{}' user='{}' host='{}' port='{}' password='{}'".format(
			self.dbname, self.user, self.host, self.port, self.password)

		self.cursortype = DEFAULT_CURSORTYPE
		if cursortype:
			if cursortype == 'dict':
				self.cursortype = cursortype
				#cnxstr = "cursor_factory=psycopg2.extras.RealDictCursor {}".format(cnxstr)
				self.conn = psycopg2.connect(
					cursor_factory=psycopg2.extras.RealDictCursor, dsn=dsn)
			elif cursortype == 'tuple' or cursortype == 'plain':
				self.cursortype = cursortype
				self.conn = psycopg2.connect(dsn)
			else:
				raise ValueError("valid cursor types are 'dict', and 'plain' or 'tuple'")

	def execute(self, fetchcommand, sql, params=None):
		""" where 'fetchcommand' is either 'fetchone' or 'fetchall' """

		cur = self.conn.cursor()
		if params:
			if not type(params).__name__ == 'tuple':
				raise ValueError('the params argument needs to be a tuple')
				return None
			cur.execute(sql, params)
		else:
			cur.execute(sql)

		self.conn.commit()

		if not fetchcommand or fetchcommand == 'none':
			return

		if fetchcommand == 'last' or fetchcommand == 'lastid':
			lastdata = cur.fetchall()
			self.conn.commit()
			return lastdata

		m = insertion_pattern.match(sql)
		"""
		 TODO: This is a BUG - need to also check tail of query for RETURNING
		"""
		if m:
			""" lastid = cursor.fetchone()['lastval'] """
			lastdata = cur.fetchone()
			self.conn.commit()
			return lastdata

		if fetchcommand == 'fetchone' or fetchcommand == 'one':
			return cur.fetchone()
		elif fetchcommand == 'fetchall' or fetchcommand == 'all':
			return cur.fetchall()
		else:
			msg = "expecting <fetchcommand> argument to be either 'fetchone'|'one'|'fetchall|all'"
			raise ValueError(msg)


	def get_table_rowcount(self, tablename):

		return self.execute('one', 'SELECT COUNT(*) FROM {}'.format(tablename), None)[0]


	def get_query_result_set_rowcount(self, sql):

		newsql = "SELECT COUNT(*) FROM ({}) AS q".format(sql)
		return self.execute('one', newsql, None)[0]

	def fetch_data_window_endposts(self, tablename, primkey, winsz, firstpk=None):

		if firstpk:
			sql = """
WITH q AS
(
SELECT {} FROM {}
WHERE {} > {}
ORDER BY {} LIMIT {}
)
(
 SELECT {} FROM q ORDER BY {} LIMIT 1
)
UNION ALL
(
 SELECT {} FROM q ORDER BY {} desc LIMIT 1
)
			""".format(
					primkey,
					tablename,
					primkey,
					firstpk,
					primkey,
					winsz,
					primkey,
					primkey,
					primkey,
					primkey
				)
		else:

			sql = """
WITH q AS
(
SELECT {} FROM {}
ORDER BY {} LIMIT {}
)
(
 SELECT {} FROM q ORDER BY {} LIMIT 1
)
UNION ALL
(
 SELECT {} FROM q ORDER BY {} desc LIMIT 1
)
			""".format(
					primkey,
					tablename,
					primkey,
					winsz,
					primkey,
					primkey,
					primkey,
					primkey
				)
		cur = self.conn.cursor()
		cur.execute(sql)
		result = cur.fetchall()
		self.conn.commit()
		return result


class PgDb(PgDbPy):

	def __init__(self, cfg, datasource_identifier, cursor_type=None):

		PgDbPy.__init__(self, cfg, datasource_identifier, cursor_type)


if __name__ == "__main__":

	# from cfgpy.tools import Cfg, FMT_INI
	# from pgdbpy.tools import PgDb
	pgdb = PgDb( Cfg(FMT_INI, None, ['./config.ini']), 'mydatasource', 'dict' )

	#result = pgdb.execute_with_dictionary_cursor('all', 'SELECT * FROM mytable')
	result = pgdb.execute('all', 'SELECT * FROM mytable')

	import pprint
	pp = pprint.PrettyPrinter(indent=4)
	pp.pprint(result)

