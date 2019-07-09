from configparser import ConfigParser


class ServerConfigStorage:
    PREFIX = "tiktorch-server::"
    DEVICE_PREFIX = "device::"

    def __init__(self, config: ConfigParser, dst: str) -> None:
        self._config = config
        self._dst = dst

    def get_servers(self):
        res = {}

        for section in self._config.sections():
            if section.startswith(self.PREFIX):
                id_ = section.replace(self.PREFIX, '')
                items = self._config.items(section)

                res[id_] = {
                    "name": "Unknown",
                    **dict(items),
                    "id": id_,
                }

        return res

    def _devices_as_options(self, devices):
        for sel, id_, name in devices:
            yield f"{self.DEVICE_PREFIX}::{id_}::name", name
            yield f"{self.DEVICE_PREFIX}::{id_}::selected", str(int(sel))

    def _write_server_entry(self, srv):
        srv_id = srv.pop("id")
        section_id = f"{self.PREFIX}{srv_id}"

        self._config.add_section(section_id)
        for key, value in srv.items():
            if key == "devices":
                for dev_key, dev_value in self._devices_as_options(value):
                    self._config.set(section_id, dev_key, dev_value)
            else:
                self._config.set(section_id, key, value)

    def store(self, servers) -> None:
        current_servers = self.get_servers()

        for srv_id in current_servers.keys():
            self._config.remove_section(f"{self.PREFIX}{srv_id}")

        for server in servers:
            self._write_server_entry(server)

        with open(self._dst, 'w+') as out:
            self._config.write(out)
