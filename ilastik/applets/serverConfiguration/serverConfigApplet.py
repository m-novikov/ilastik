###############################################################################
#   ilastik: interactive learning and segmentation toolkit
#
#       Copyright (C) 2011-2019, the ilastik team
#                                <team@ilastik.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition, as a special exception, the copyright holders of
# ilastik give you permission to combine ilastik with applets,
# workflows and plugins which are not covered under the GNU
# General Public License.
#
# See the LICENSE file for details. License information is also available
# on the ilastik web site at:
#		   http://ilastik.org/license.html
###############################################################################
import logging

from ilastik.applets.base.standardApplet import StandardApplet
from .opServerConfig import OpServerConfig
from .serverConfigSerializer import ServerConfigSerializer
from . import types


logger = logging.getLogger(__name__)

import grpc
from tiktorch.launcher import LocalServerLauncher, RemoteSSHServerLauncher, SSHCred
from tiktorch.launcher import ConnConf
import socket
import inference_pb2_grpc, inference_pb2


class _NullLauncher:
    def start(self):
        pass

    def stop(self):
        pass


class TiktorchConnectionFactory(types.IConnectionFactory):
    class _TiktorchConnection(types.IConnection):
        def __init__(self, config):
            self._config = config

        def get_devices(self):
            config = self._config
            try:
                port = config.port
                if config.autostart:
                    # in order not to block address for real server todo: remove port hack
                    port = str(int(config.port) - 20)

                addr = socket.gethostbyname(self._config.address)
                conn_conf = ConnConf(addr, port, timeout=10)

                if config.autostart:
                    if addr == "127.0.0.1":
                        launcher = LocalServerLauncher(conn_conf, path=config.path)
                    else:
                        launcher = RemoteSSHServerLauncher(
                            conn_conf, cred=SSHCred(user=config.username, key_path=config.ssh_key), path=config.path
                        )
                else:
                    launcher = _NullLauncher()

                try:
                    launcher.start()
                    with grpc.insecure_channel(f"{addr}:{port}") as chan:
                        client = inference_pb2_grpc.InferenceStub(chan)
                        resp = client.ListDevices(inference_pb2.Empty())
                        return [(d.id, d.id) for d in resp.devices]
                except Exception as e:
                    logger.exception('Failed to fetch devices')
                    raise
                finally:
                    try:
                        launcher.stop()
                    except Exception:
                        pass

            except Exception as e:
                logger.error(e)
                raise

    def ensure_connection(self, config=None) -> types.IConnection:
        return self._TiktorchConnection(config)


class ServerConfigApplet(StandardApplet):
    def __init__(self, workflow):
        self._topLevelOperator = OpServerConfig(parent=workflow)
        super().__init__("Server configuration", workflow)
        self._serializableItems = [ServerConfigSerializer('ServerConfiguration', operator=self._topLevelOperator)]
        self._topLevelOperator.ServerConfig.notifyReady(self._requestUpdate)
        self._topLevelOperator.ServerConfig.notifyValueChanged(self._configChanged)
        self._connectionFactory = TiktorchConnectionFactory()

    def _configChanged(self, *args, **kwargs):
        logger.debug("Server config value changed")

    def _requestUpdate(self, *args, **kwargs):
        self.appletStateUpdateRequested()

    @property
    def connectionFactory(self) -> types.IConnectionFactory:
        return self._connectionFactory

    @property
    def topLevelOperator(self):
        return self._topLevelOperator

    @property
    def singleLaneGuiClass(self):
        from .serverConfigGui import ServerConfigGui
        return ServerConfigGui

    @property
    def broadcastingSlots(self):
        return []

    @property
    def dataSerializers(self):
        return self._serializableItems
