import asyncore
import logging
import proxy
import settings

class LoginSession(proxy.Session):
  def __init__(self):
    proxy.Session.__init__(self)
    logging.info("Session opened")

  def handle_client_read(self):
    logging.info("Pumping %d client bytes", len(self.client.indata))
    self.server.outdata = self.server.outdata + self.client.indata
    self.client.indata = ""

  def handle_server_read(self):
    logging.info("Pumping %d server bytes", len(self.server.indata))
    self.client.outdata = self.client.outdata + self.server.indata
    self.server.indata = ""

  def handle_close(self):
    logging.info("Session closed")

def main():
  logging.basicConfig(level=logging.DEBUG)
  listener = proxy.Listener(LoginSession, settings.LISTENADDR, settings.SERVERADDR)
  asyncore.loop()

if __name__ == '__main__':
  main()

