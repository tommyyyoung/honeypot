#emulate a simple file system for the honey pot
NEBULUS_FS = {
    "/": {
        "type": "dir",
        "children": ["home", "etc", "var", "opt", "srv"]
    },

    "/home": {
        "type": "dir",
        "children": ["admin", "j.smith"]
    },

    "/home/admin": {
        "type": "dir",
        "children": ["maintenance.sh", "TODO.txt", "vpn_backup_old.conf"]
    },

    "/home/admin/TODO.txt": {
        "type": "file",
        "content": """
        - rotate SSH keys
        - delete old backups
        - ask IT about strange login alerts
        - update firewall rules
        """
    },

    "/home/j.smith": {
        "type": "dir",
        "children": ["claims_q4.xlsx", "passwords_old.txt", "notes.txt"]
    },

    "/home/j.smith/passwords_old.txt": {
        "type": "file",
        "content": """
        vpn_admin:Winter2021!
        claims_api:Claims@123
        """
    },

    "/etc": {
        "type": "dir",
        "children": ["nebulus.conf", "compliance"]
    },

    "/etc/nebulus.conf": {
        "type": "file",
        "content": "company=Nebulus Insurance\nenvironment=production"
    },

    "/var": {
        "type": "dir",
        "children": ["log", "backups"]
    },

    "/var/log": {
        "type": "dir",
        "children": ["auth.log", "claims-api.log"]
    },

    "/var/backups": {
        "type": "dir",
        "children": ["nebulus_prod_2022.tar.gz", "nebulus_prod_2023.tar.gz"]
    }
}

class NebulusFileSystem():
    def __init__(self, session):
        self.cwd = "/"
        self.session = session
    
    def ls(self):
        path = NEBULUS_FS.get(self.cwd)
        if self.cwd not in self.session.sessionData['visitedPaths']:
            self.session.sessionData['visitedPaths'].add(self.cwd)

        if not path or path['type'] != 'dir':
            return "ls: cannot access."
        return " ".join(path['children'])
    
    def cd(self, path):
        if path not in self.session.sessionData['visitedPaths']:
            self.session.sessionData['visitedPaths'].add(path)
            depth = path.count('/')
            self.session.sessionData['maxDepth'] = max(self.session.sessionData['maxDepth'], depth)

        if path == "..":
            self.cwd = "/" if self.cwd == "/" else "/".join(self.cwd.split("/")[:-1]) or "/" 
            return ""
        
        newPath = path if path.startswith('/') else f'{self.cwd}/{path}'.replace('//', '/')
        if newPath in NEBULUS_FS and NEBULUS_FS[newPath]['type'] == 'dir':
            self.cwd = newPath
            return ""
        return "cd: no such directory.\r\n"
    
    def cat(self, filename):
        if filename.startswith('/'):
            path = filename 
        else:
            path = f'{self.cwd}/{filename}'.replace('//', '/')
        
        node = NEBULUS_FS.get(path)
        if not node:
            return "cat: no such file."
        if node['type'] != 'file':
            return "cat: cannot read directory."
        return node['content'].strip()