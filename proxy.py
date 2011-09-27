import asyncore
import socket

class Endpoint(asyncore.dispatcher):
  def __init__(self, session, callback):
    asyncore.dispatcher.__init__(self)
    self.session = session
    self.callback = callback
    self.indata = ""
    self.outdata = ""

  def handle_read(self):
    newdata = self.recv(4096)
    if len(newdata) != 0:
      self.indata = self.indata + newdata
      self.callback()
    else:
      self.session.close()

  def handle_write(self):
    sent = self.send(self.outdata)
    self.outdata = self.outdata[sent:]

  def writable(self):
    return len(self.outdata) != 0

class Session:
  """Instantiated by Listener to pump data between two endpoints

  Subclass this and override the handle_* methods"""

  def __init__(self):
    self.client = Endpoint(self, self.handle_client_read)
    self.server = Endpoint(self, self.handle_server_read)

  def close(self):
    self.handle_close()
    self.client.close()
    self.server.close()

  def handle_client_read(self):
    """Called when data is received from the client

    Incoming data is available in self.client.indata
    Outgoing data should be appended to self.server.outdata"""
    raise NotImplementedError

  def handle_server_read(self):
    """Called when data is received from the server

    Incoming data is available in self.server.indata
    Outgoing data should be appended to self.client.outdata"""
    raise NotImplementedError

  def handle_close(self):
    """Called when either endpoint closes its connection"""
    raise NotImplementedError

class Listener(asyncore.dispatcher):
  """Listens for connections and creates sessions"""

  def __init__(self, sessioncls, localaddr, remoteaddr):
    """Construct a proxy for the given remoteaddr on the given localaddr

    sessioncls -- A subclass of Session
    localaddr -- The local address to bind to
    remoteaddr -- The remote addr to connect to
    """
    asyncore.dispatcher.__init__(self)
    self.sessioncls = sessioncls
    self.remoteaddr = remoteaddr
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind(localaddr)
    self.listen(1)

  def handle_accept(self):
    clientsock, _ = self.accept()
    session = self.sessioncls()
    session.client.set_socket(clientsock)
    session.server.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    session.server.connect(self.remoteaddr)

