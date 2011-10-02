import asyncore
import logging
import os
import struct
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

class RC4:
  def __init__(self, path):
    with open(path) as f:
      self.x, self.y, self.S = struct.unpack("II256s", f.read())
      self.S = bytearray(self.S)

  def crypt(self, data):
    for i in range(len(data)):
      data[i] ^= self.get()

  def get(self):
    self.x = (self.x + 1) % 256
    self.y = (self.y + self.S[self.x]) % 256
    self.x, self.y = self.y, self.x
    return self.S[(self.S[self.x] + self.S[self.y]) % 256]

class LoginSession(proxy.Session):
  CLIENT_CHALLENGE_SIZE = 16 + 66 # Hello + public key
  SERVER_CHALLENGE_SIZE = 22 # Public key
  KEY_FILE = "/mnt/tenchi/gwkey.txt"

  def __init__(self):
    proxy.Session.__init__(self)
    logging.info("Session opened")
    self.state = "client_challenge"
    self.crypt_file_mtime = self.get_crypt_file_mtime()
    self.client_decrypt = None
    self.server_decrypt = None

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
    if self.client_decrypt:
      return
    while self.crypt_file_mtime == self.get_crypt_file_mtime():
      logging.info("Waiting for crypt file to be written...")
      time.sleep(1)
    self.client_decrypt = RC4(self.KEY_FILE)
    self.server_decrypt = RC4(self.KEY_FILE)

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
      buf = bytearray(self.client.indata)
      logging.debug("Client before:"); tools.dump(buf)
      self.client_decrypt.crypt(buf)
      logging.debug("Client after:"); tools.dump(buf)
      pump_data(self.client, self.server)

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
      buf = bytearray(self.server.indata)
      logging.debug("Server before:"); tools.dump(buf)
      self.server_decrypt.crypt(buf)
      logging.debug("Server after:"); tools.dump(buf)
      pump_data(self.server, self.client)

  def handle_close(self):
    logging.info("Session closed")

def main():
  logging.basicConfig(level=logging.DEBUG)
  listener = proxy.Listener(LoginSession, settings.LOGIN_LISTEN_ADDR)
  asyncore.loop()

if __name__ == '__main__':
  main()

