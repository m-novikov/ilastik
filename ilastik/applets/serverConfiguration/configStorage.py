from configparser import ConfigParser


class ServerConfigStorage:
    PREFIX = "tiktorch-server:"

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
                    **dict(items),
                    "id": id_,
                }

        return res

    def _get_or_create_section(self, section):
        if self._config.has_section(section):
            return

    def _write_server_entry(self, srv):
        srv_id = srv.pop("id")
        section_id = f"{self.PREFIX}{srv_id}"

        self._config.add_section(section_id)
        for key, value in srv.items():
            self._config.set(section_id, key, value)

    def store(self, servers) -> None:
        current_servers = self.get_servers()

        for srv_id in current_servers.keys():
            self._config.remove_section(f"{self.PREFIX}{srv_id}")

        for server in servers:
            self._write_server_entry(server)

        self._config.write(self._dst)
