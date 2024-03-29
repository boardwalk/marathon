import asyncore
import copy
import logging
import os
import time

import proxy
import settings
import tools

def pump_data(src, dst, numbytes = -1):
  if numbytes < 0:
    numbytes = len(src.indata)
  dst.outdata.extend(src.indata[:numbytes])
  src.indata = src.indata[numbytes:]
  src_name, _ = src.getpeername()
  dst_name, _ = dst.getpeername()
  logging.info("Pumped %d bytes from %s to %s", numbytes, src_name, dst_name)

class LoginSession(proxy.Session):
  CLIENT_CHALLENGE_SIZE = 16 + 66 # Hello + public key
  SERVER_CHALLENGE_SIZE = 22 # Public key
  KEY_FILE = "/mnt/tenchi/gwkey.txt"

  def __init__(self):
    proxy.Session.__init__(self)
    logging.info("Session opened")
    self.state = "client_challenge"
    self.crypt_file_mtime = self.get_crypt_file_mtime()

  def get_server_addr(self):
    return settings.LOGIN_SERVER_ADDR

  def repump(self):
    self.handle_client_read()
    self.handle_server_read()

  def get_crypt_file_mtime(self):
    try:
      return os.stat(self.KEY_FILE).st_mtime
    except OSError:
      return 0.0

  def init_decrypt(self):
    if hasattr(self, "client_decrypt"):
      return
    while self.crypt_file_mtime == self.get_crypt_file_mtime():
      logging.info("Waiting for crypt file to be written...")
      time.sleep(1)
    self.client_decrypt = tools.RC4.from_file(self.KEY_FILE)
    self.client_encrypt = copy.deepcopy(self.client_decrypt)
    self.server_decrypt = copy.deepcopy(self.client_decrypt)
    self.server_encrypt = copy.deepcopy(self.client_decrypt)
    self.client_bytes_decrypted = 0
    self.server_bytes_decrypted = 0

  def log_packet(self, src):
    tm = time.time()
    msecs = (tm - long(tm)) * 1000
    src_name, _ = src.getpeername()
    fn = "packet_%s.%03d_%s.dat" % (time.strftime("%Y.%m.%d_%H.%M.%S", time.localtime(tm)), msecs, src_name)
    with open(fn, "wb") as f:
      f.write(src.indata)

  def process_client(self):
    self.log_packet(self.client)
    return len(self.client.indata)

  def process_server(self):
    self.log_packet(self.server)
    return len(self.server.indata)

  def handle_client_read(self):
    if len(self.client.indata) == 0:
      return
    if self.state == "client_challenge":
      if len(self.client.indata) >= self.CLIENT_CHALLENGE_SIZE:
        pump_data(self.client, self.server, self.CLIENT_CHALLENGE_SIZE)
        self.state = "server_challenge"
        logging.info("client_challenge -> server_challenge")
        self.repump()
    elif self.state == "connected":
      self.init_decrypt()
      self.client_decrypt.crypt(self.client.indata, self.client_bytes_decrypted)
      bytes_consumed = self.process_client()
      self.server_encrypt.crypt(self.client.indata, 0, bytes_consumed)
      pump_data(self.client, self.server, bytes_consumed)
      self.client_bytes_decrypted = len(self.client.indata)

  def handle_server_read(self):
    if len(self.server.indata) == 0:
      return
    if self.state == "server_challenge":
      if len(self.server.indata) >= self.SERVER_CHALLENGE_SIZE:
        pump_data(self.server, self.client, self.SERVER_CHALLENGE_SIZE)
        self.state = "connected"
        logging.info("server_challenge -> connected")
        self.repump()
    elif self.state == "connected":
      self.init_decrypt()
      self.server_decrypt.crypt(self.server.indata, self.server_bytes_decrypted)
      bytes_consumed = self.process_server()
      self.client_encrypt.crypt(self.server.indata, 0, bytes_consumed)
      pump_data(self.server, self.client, bytes_consumed)
      self.server_bytes_decrypted = len(self.server.indata)

  def handle_close(self):
    logging.info("Session closed")

def main():
  logging.basicConfig(level=logging.DEBUG)
  listener = proxy.Listener(LoginSession, settings.LOGIN_LISTEN_ADDR)
  asyncore.loop()

if __name__ == '__main__':
  main()

