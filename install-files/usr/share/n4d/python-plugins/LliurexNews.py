import os
import bcrypt
import tempfile
import ConfigParser
import shutil
import time
import lliurex.net

from jinja2 import Environment
from jinja2.loaders import FileSystemLoader
from jinja2 import Template


class LliurexNews:
	
	BASE_DIR="/usr/share/lliurex-news/llx-data/"
	NEWS_BASE_DIR=BASE_DIR+"content/"
	#HTACCESS=NEWS_BASE_DIR+".htaccess"
	#ADMIN_DATA=NEWS_BASE_DIR+"data/"
	CONFIG_DATA=BASE_DIR+"config/config.production.json"
	CONFIG_CLI_FILE=BASE_DIR+"config/.ghost-cli"
	CONFIG_SYSTEMD_FILE=BASE_DIR+"systemd/ghost_news.service"
	TEMPLATE_DIR=BASE_DIR+""
	SQL_TEMPLATE="news.sql"
	APACHE_CONF_FILE=BASE_DIR+"apache2/news-server.conf"
	APACHE_EXTERNAL_CONF=BASE_DIR+"apache2/news.conf"

	#EASY_SITE=NEWS_BASE_DIR+"nextcloud.json"
	#EASY_SITE_ICON=NEWS_BASE_DIR+"nextcloud.png"
	#CNAME="cname-owncloud"
	
	NEWS_DATA_DIR="/var/www/news/content/"
	NEWS_CONFIG_DIR="/var/www/news/"
	NEWS_CONFIG_FILE="/var/www/news/config.production.json"
	NEWS_SYSTEMD_FILE="/var/www/news/system/files/"

	APACHE_FILE_SITES_CONFIGURATION="/etc/apache2/sites-enabled/000-default.conf"
	APACHE_EXTERNAL_DIR="/etc/apache2/lliurex-location"
	#EASY_SITES_DIR_ICON="/var/www/srv/icons/"
	
	
	
	'''
	# TESTING #
	
	TEMPLATE_DIR="/home/netadmin/"
	BASE_DIR="/home/netadmin/workspace/lliurex-owncloud/install-files"+BASE_DIR
	NEWS_BASE_DIR=BASE_DIR+"llx-data/"
	HTACCESS=NEWS_BASE_DIR+".htaccess"
	EASY_SITE=NEWS_BASE_DIR+"owncloud.json"
	
	# TESTING #
	'''
	
	def __init__(self):
	
		self.template=None
		self.template_vars=["DB_USER","DB_PWD","DB_NAME","ADMIN_USER","ADMIN_PWD","ADMIN_EMAIL"]
		
	#def init
	
	def parse_template(self,template_path):
		
		print("* Parsing template...")

		config = ConfigParser.ConfigParser()
		config.optionxform=str
		config.read(template_path)
		
		self.template={}
		try:

			self.template["DB_USER"]=config.get("news","DB_USER")
			self.template["DB_PWD"]=config.get("news","DB_PWD")
			self.template["DB_NAME"]=config.get("news","DB_NAME")
			self.template["ADMIN_USER"]=config.get("news","ADMIN_USER")
			self.template["ADMIN_PWD"]=config.get("news","ADMIN_PWD")
			self.template["ADMIN_EMAIL"]=config.get("news","ADMIN_EMAIL")
		
			self.load_template(self.template)
			return [True,""]
			
		except Exception as e:
			msg="[!] Error: %s"%(str(e))
			print("[!] Error:",e)
			return [False,e]
		
		
		
		
	#def parse_template
	
	
	def load_template(self,template):
		
		print("* Loading template...")
		
		if not type({})==type(template):
			return [False,""]
			
		for var in self.template_vars:
			if var not in template:
				return [False,""]
			
		self.template=template

		try:

			self.template["EXTERNAL_IP"]=lliurex.net.get_ip(objects["VariablesManager"].get_variable("EXTERNAL_INTERFACE"))
			
		except:
			import xmlrpclib as x
			
			c=x.ServerProxy("https://server:9779")
			#self.template["LDAP_BASE_USER_TREE"]="ou=People,"+c.get_variable("","VariablesManager","LDAP_BASE_DN")
			#self.template["LDAP_BASE_GROUP_TREE"]="ou=Groups,"+c.get_variable("","VariablesManager","LDAP_BASE_DN")
			#self.template["SRV_IP"]=c.get_variable("","VariablesManager","SRV_IP")
			#self.template["INTERNAL_DOMAIN"]=c.get_variable("","VariablesManager","INTERNAL_DOMAIN")
			self.template["EXTERNAL_IP"]=lliurex.net.get_ip(c.get_variable("","VariablesManager","EXTERNAL_INTERFACE"))

		self.template["ADMIN_PWD"]=self.create_password_bhash(self.template["ADMIN_PWD"])
		return [True,""]
		
	#def load_template
	
	
	def mysql_service_init(self):
		
		print("* Initializing mysql root passwd (if needed) ...")
		os.system("sudo mysql_root_passwd -i")
		return [True,""]
		
	#def mysql_service_init


	def create_db(self):
		
		print("* Creating database...")
		
		if self.template==None:
			return [False,""]
			
		cmd='mysql -u%s -p%s -e "drop database IF EXISTS %s"'%(self.template["DB_USER"],self.template["DB_PWD"],self.template["DB_NAME"])
		os.system(cmd)
		
		cmd='mysql -u%s -p%s -e "create database %s"'%(self.template["DB_USER"],self.template["DB_PWD"],self.template["DB_NAME"])
		os.system(cmd)
		
		file_path=self.process_sql_template()
		if file_path==None:
			return [False,"Error processing sql template"]
		cmd="mysql -u %s -p%s %s < %s"%(self.template["DB_USER"],self.template["DB_PWD"],self.template["DB_NAME"],file_path)
		os.system(cmd)
		os.remove(file_path)
		
		return [True,""]
		
	#def init_sql
	
	def create_db_user(self):
	
		print("* Creating mysql user ...")
		
		db_pass=self.template["DB_PWD"]
		db_user=self.template["DB_USER"]
		db_name=self.template["DB_NAME"]
		cmd='mysql -uroot -p$(mysql_root_passwd -g) -e "GRANT ALL PRIVILEGES ON %s.* TO \'%s\'@localhost IDENTIFIED BY \'%s\'"'%(db_name, db_user,db_pass)
		ret=os.system(cmd)
		
		return [True,ret]
		
	#def generate_user	
	
	
	def create_password_bhash(self,password):
		
		print("* Generating admin password...")
		
		salt=bcrypt.gensalt(10)
		return bcrypt.hashpw(password,bcrypt.gensalt(10))
		
	#def create_password_bhash
	
	
	def process_sql_template(self):
		
		print("* Procesing SQL template...")
		try:
			template_dir=LliurexNews.TEMPLATE_DIR
			sql_template_file=LliurexNews.SQL_TEMPLATE
			tpl_env = Environment(loader=FileSystemLoader(template_dir))
			sql_template = tpl_env.get_template(sql_template_file)
			content = sql_template.render(self.template).encode('UTF-8')

			tmp_file=tempfile.mktemp()
			f=open(tmp_file,"w")
			f.write(content)
			f.close()
			
			return tmp_file
		except Exception as e:
			print(str(e))
			return None
		
		
	#def process_sql_template

	def create_ghost_user(self):

		try:
			cmd="useradd -r -u 998 -s /usr/bin/nologin ghost"
			os.system(cmd)
		except Exception as e:
			print(str(e))
			return[False,"unable to create ghost user"]

		return [True,""]	
				
	
	def clean_old_files(self):
		
		print("* Cleaning old News data...")
		
		
		if os.path.exists(LliurexNews.NEWS_CONFIG_FILE):
			os.system("rm -f %s"%LliurexNews.NEWS_CONFIG_FILE)

		
		for dir in [LliurexNews.NEWS_DATA_DIR]:
			if os.path.exists(dir):
				os.system("rm -rf %s"%dir)
				
		return [True,""]
		
	#def clean_old_files
	
	def copy_new_files(self):
		
		print("* Copying new News...")

		cmd="cp %s %s"%(LliurexNews.CONFIG_DATA,LliurexNews.NEWS_CONFIG_FILE)
		os.system(cmd)

		cmd="cp %s %s"%(LliurexNews.CONFIG_CLI_FILE,LliurexNews.NEWS_CONFIG_DIR)
		os.system(cmd)
		
		cmd="cp -r %s %s"%(LliurexNews.NEWS_BASE_DIR,"/var/www/news/")
		os.system(cmd)
		
				
		#os.system("mv %s/ADMIN_USER %s/%s"%(LliurexNews.NEWS_BASE_DIR,LliurexNews.NEWS_BASE_DIR,self.template["ADMIN_USER"]))
		
		#cmd="cp %s %s"%(LliurexNews.HTACCESS,"/var/www/nextcloud/")
		os.system(cmd)
		
		return [True,""]
		
	#def copy_new_files
	
	def process_config_file(self):
		
		print("* Procesing config template...")
		
		template_dir=LliurexNews.NEWS_CONFIG_DIR
		template_file="config.production.json"
		
		tpl_env = Environment(loader=FileSystemLoader(template_dir))
		template = tpl_env.get_template(template_file)
		content = template.render(self.template).encode('UTF-8')
		
		f=open(template_dir+template_file,"w")
		f.write(content)
		f.close()		

		for dir in [LliurexNews.NEWS_DATA_DIR]:
			if os.path.exists(dir):
				os.system("chown -R ghost:ghost %s"%dir)
					
		cmd="find /var/www/news/* -type d -exec chmod 775 {} \;"
		os.system(cmd)

		cmd="find /var/www/news/* -type f -exec chmod 664 {} \;"
		os.system(cmd)

		return [True,""]
		
	#def process_config_file


	def enable_apache(self):

		print("* Enabling apache site")

		cmd="cp %s %s"%(LliurexNews.APACHE_CONF_FILE, "/etc/apache2/sites-available/")
		os.system(cmd)
		if not os.path.exists(LliurexNews.APACHE_EXTERNAL_DIR):
			cmd="mkdir %s"%(LliurexNews.APACHE_EXTERNAL_DIR)
			os.system(cmd)

		if os.path.exists(LliurexNews.APACHE_EXTERNAL_DIR):	
			cmd="cp %s %s"%(LliurexNews.APACHE_EXTERNAL_CONF,LliurexNews.APACHE_EXTERNAL_DIR)
			os.system(cmd)

		try:
			modify=True
			path, dirs, files = next(os.walk(LliurexNews.APACHE_EXTERNAL_DIR))
			number_files=len(files)
			print("modificando 000-default")
			print(number_files)
			if ( number_files > 0 ):
				if os.path.isfile(LliurexNews.APACHE_FILE_SITES_CONFIGURATION):
					with open(LliurexNews.APACHE_FILE_SITES_CONFIGURATION, "r") as in_file:
						buf = in_file.readlines()
					with open(LliurexNews.APACHE_FILE_SITES_CONFIGURATION, "w") as out_file:
						for line in buf:
							if  "lliurex-location" in line:
								print("linea encontrada")
								modify=False
							else:
								if ( "<Directory /var/www/admin-center>" in line ) & (modify):
									print("escribiendo linea")
									line = "include /etc/apache2/lliurex-location/*.conf\n" + line
							out_file.write(line)
			else:
				if os.path.isfile(LliurexNews.APACHE_FILE_SITES_CONFIGURATION):
					with open(LliurexNews.APACHE_FILE_SITES_CONFIGURATION, "r") as in_file:
						buf = in_file.readlines()
					with open(LliurexNews.APACHE_FILE_SITES_CONFIGURATION, "w") as out_file:
						for line in buf:
							if "lliurex-location" in line:
								line = "\n"
							out_file.write(line)
				
			return [True,""]
		
		except Exception as e:
			print ("[ExportWebSitesServer] %s"%e)
			return [False,str(e)]	


	#def enable_apache

	def enable_systemd(self):

		print("* Disabling previous systemd service")

		try:

			cmd="systemctl stop ghost_news.service"
			os.system(cmd)

			time.sleep(1)
			cmd="systemctl disable ghost_news.service"
			os.system(cmd)

		except Exception as e:
			print(str(e))	
			
		
		print("* Enabling systemd service...")
		
		try:
			
			cmd="cp %s %s"%(LliurexNews.CONFIG_SYSTEMD_FILE,LliurexNews.NEWS_SYSTEMD_FILE)
			os.system(cmd)

			cmd="ln -sf /var/www/news/system/files/ghost_news.service /lib/systemd/system/ghost_news.service"
			os.system(cmd)

			cmd="systemctl enable ghost_news.service"
			os.system(cmd)

			time.sleep(1)
			cmd="systemctl start ghost_news.service"
			os.system(cmd)
			
		except Exception as e:
			print(str(e))	
			return [False,"Error enabling systemd service"]

		
		return [True,""]
		
	#def enable_easy_site
	
	def enable_cname(self):

		'''
		template_dir=LliurexNews.NEWS_BASE_DIR
		tpl_env = Environment(loader=FileSystemLoader(template_dir))
		template = tpl_env.get_template(LliurexNews.CNAME)
		
		content = template.render(self.template).encode('UTF-8')
		f=open("/var/lib/dnsmasq/config/cname-owncloud","w")
		f.write(content)
		f.close()
		
		'''

		f=open("/etc/n4d/key","r")
		magic_key=f.readline().strip("\n")
		f.close()
		import xmlrpclib as x
		c=x.ServerProxy("https://server:9779")
		result = c.set_internal_dns_entry(magic_key,"Dnsmasq","news-server")
		if result['status'] == True:
			os.system("systemctl restart dnsmasq.service")
			return [True,""]
		else:
			return [False,result['msg']]
		
		
	#def enable_cname
	
	def enable_apache_conf(self):
		
		#os.system("a2enmod ldap")
		os.system("a2enmod ssl")
		os.system("a2enmod rewrite")
		os.system("a2enmod headers")
		os.system("a2ensite default-ssl.conf")
		os.system("service apache2 restart")
		os.system("a2ensite news-server.conf")
		os.system("systemctl restart apache2.service")
		
	#def enable_apache_mods
	
	
	def initialize_news(self,template):
		
		try:

			status,ret=self.load_template(template)
			if not status:
				return [False,ret +"1"]

			status,ret=self.mysql_service_init()
			if not status:
				return [False,ret+"3"]

			status,ret=self.create_db_user()
			if not status:
				return [False,ret+"4"]

			status,ret=self.create_db()
			if not status:
				return [False,ret+"5"]

			status,ret=self.create_ghost_user()
			if not status:
				return[False,ret+"6"]	
			status,ret=self.clean_old_files()
			if not status:
				return [False,ret+"7"]

			status,ret=self.copy_new_files()
			if not status:
				return [False,ret+"8"]

			status,ret=self.process_config_file()
			if not status:
				return [False,ret+"9"]

			status,ret=self.enable_apache()
			if not status:
				return [False,ret+"10"]	

			status,ret=self.enable_systemd()
			if not status:
				return [False,ret+"11"]
			
			status,ret=self.enable_cname()
			if not status:
				return [False,ret+"12"]
				
			self.enable_apache_conf()
				
			return [True,"SUCCESS"]
			
		except Exception as e:
			
			return [False,str(e)+" ?"]
		
	#def initlializ_owncloud
	
	
#class LliurexNews

if __name__=="__main__":
	
	lo=LliurexNews()
	lo.parse_template("/home/netadmin/news.ini")
	lo.mysql_service_init()
	lo.create_db_user()
	lo.create_db()
	lo.create_ghost_user()
	lo.clean_old_files()
	lo.copy_new_files()
	lo.process_config_file()
	lo.enable_apache()
	lo.enable_systemd()
	lo.enable_cname()
	lo.enable_apache_conf()


	
	