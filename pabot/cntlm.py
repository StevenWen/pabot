import subprocess
import time
import os
import socket
import signal



pidfiledir = "/var/run/cntlm"


class CntlmManager(object):

	def __init__(self):
		self.cntlm_table = None

	def __del__(self):
		self.stop_all()

	def __lazy_init(self):
		"""initialize the cntlm manager, load all cntlm proccess info find in
		pidfiledir. Scan the ports in range min_port_num to max_port_num, raise an
		exception if any port is blocked by other proccesses

		"""
		self.cntlm_table = {}
		for pidfile in os.listdir(pidfiledir):
			#pidfile should be in this format: port_proxy_domain_username
			port = int(pidfile)
			path = pidfiledir + '/' + pidfile
			f = open(path)
			pid = int(f.readline())
			f.close()
			try:
				os.kill(pid, signal.SIGTERM)
			except OSError:
				os.remove(path)
			time.sleep(1)


	def connect_proxy(self, proxy, domain, username, password):
		"""return the listening port number on localhost of a cntlm that connects to the 
		proxy with specified authentication infomation, if such cntlm is not running, 
		find an idle port and start a new cntlm proccess, if no idle port is find in the 
		specified range, kill the cntlm proccess that ueses the port in a circular order,
		raise an if a port is blocked by other proccesses

		Parameter:
		(str)domain        - authentication info, domain
		(str)username      - authentication info, username
		(str)password      - authentication info, password
        (str)proxy         - the proxy cntlm will connect to

        Returns:
        (int)port          - the port number of the listening cntlm on localhost, eg '3128'

        Raises:
        PortError          - some port is blocked by some other proccess not started by RF

		"""
		if not self.cntlm_table:
			self.__lazy_init()
		port = self.__find_cntlm(proxy, domain, username)
		if (port != 0):
			return port
		port = self.__find_port()

		self.__start(proxy, domain, username, password, port)
		print self.cntlm_table
		return port
	
	def stop_all(self):
		"""stop all running cntlm proccesses
		"""
		if not self.cntlm_table:
			self.__lazy_init()
		for port_num in self.cntlm_table:
			if self.cntlm_table[port_num]:

				os.kill(self.cntlm_table[port_num].pid, signal.SIGTERM)
				self.cntlm_table[port_num] = None
				self.next_port_to_free = None
		time.sleep(1)


	def __find_cntlm(self, proxy, domain, username):
		"""find a running cntlm with the specified auth info

		Returns:
        (int)port_num       - the port number of correspounding cntlm object

		"""
		for port_num in self.cntlm_table:
			if self.cntlm_table[port_num]:
				if self.cntlm_table[port_num].match(proxy, domain, username):
					return port_num
		return 0

	def __find_port(self):
		"""Find a free port, or a free up a port by killing the proccess if all ports are used

		Returns:
        (int)port          - the port number of an idle port

		"""
		import socket
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.bind(("", 0))
		port = s.getsockname()[1]
		s.close()
		return port

	def __start(self, proxy, domain, username, password, port_num):
		"""Start a new cntlm proccess on the port
		
		"""
		pidfile_path =  pidfiledir + '/' + `port_num` 
		cmd = "/usr/sbin/cntlm -v -P " + pidfile_path + " -d " + domain + " -u " + username \
		+ " -p " + password + " -l " + `port_num` + " " + proxy + "&>>cntlm.log"
		#logger.debug("starting cntlm by: " + cmd)
		subprocess.Popen(cmd, shell=True)
		time.sleep(1)
	 	f = open(pidfile_path, 'r+')
		pid = int(f.readline())
		f.write(proxy + "\n")
		f.write(domain + "\n")
		f.write(username + "\n")
		f.close()
		#logger.debug("cntlm pid: " + `pid`)
		self.cntlm_table[port_num] = CntlmInstance(proxy, domain, username, pid)




class CntlmInstance(object):
	def __init__(self, proxy, domain, username, pid):
		self.proxy = proxy
		self.username = username
		self.domain = domain
		self.pid = pid

	def match(self, proxy, domain, username):
		if self.proxy != proxy:
			return False
		if self.domain != domain:
			return False
		if self.username != username:
			return False
		return True
