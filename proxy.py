"""Facilitates proxying of data between TCP clients and a server"""
import asyncore
import socket

class Endpoint(asyncore.dispatcher):
  def __init__(self, session, callback):
    asyncore.dispatcher.__init__(self)
    self.session = session
    self.callback = callback
    self.indata = bytearray()
    self.outdata = bytearray()

  def handle_read(self):
    newdata = self.recv(4096)
    if len(newdata) != 0:
      self.indata.extend(newdata)
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

  Subclass this and override the unimplemented methods"""
  def __init__(self):
    self.client = Endpoint(self, self.handle_client_read)
    self.server = Endpoint(self, self.handle_server_read)

  def close(self):
    self.handle_close()
    if self.client.socket:
      self.client.close()
    if self.server.socket:
      self.server.close()

  def get_client_addr(self):
    """Returns the address connected to on the client side"""
    return self.client.socket.getpeername()

  def get_server_addr(self):
    """Returns the address to connect to on the server side

    If None, the session is closed by the Listener"""
    raise NotImplementedError

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

  def __init__(self, sessioncls, listenaddr):
    """Construct a proxy for the given remoteaddr on the given localaddr

    sessioncls -- A subclass of Session
    listenaddr -- The address to bind to
    """
    asyncore.dispatcher.__init__(self)
    self.sessioncls = sessioncls
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind(listenaddr)
    self.listen(1)

  def handle_accept(self):
    clientsock, _ = self.accept()
    session = self.sessioncls()
    session.client.set_socket(clientsock)
    session.client.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    serveraddr = session.get_server_addr()
    if serveraddr:
      session.server.create_socket(socket.AF_INET, socket.SOCK_STREAM)
      session.server.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
      session.server.connect(serveraddr)
    else:
      session.close()

