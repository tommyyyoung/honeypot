#!/usr/bin/env python3

#store information off of the server
import logging
#keep our logs from getting too big
from logging.handlers import RotatingFileHandler
#create tcp socket
import socket
#chose paramiko so I could implement SSHv2
import paramiko
#allow socket to handle more than one port at a time
import threading
#need time for session tracking
import time
#unique session ids
import uuid
#gonna use some stats for analysis
import statistics
#use flask session for tracking
from flask import session
#db for session storage
import sqlite3
#
import json
#simulated file system
from fileSystem import NebulusFileSystem

#define how the log entries will look
lFormat = logging.Formatter('%(message)s')

#custom string banner to look authentic
SSH_BANNER = 'SSH-2.0-NebulusSSHServer_1.0'

#private server key
hostKey = paramiko.RSAKey(filename = 'server.key')

#catch-all logger sends info to audit.log
fLogger = logging.getLogger('Funnel Logger')
fLogger.setLevel(logging.INFO)
fHandler = RotatingFileHandler('audits.log', maxBytes = 2000, backupCount = 5)
fHandler.setFormatter(lFormat)
fLogger.addHandler(fHandler)

#credentials logger sends info to cmdAudit.log
cLogger = logging.getLogger('Credential Logger')
cLogger.setLevel(logging.INFO)
cHandler = RotatingFileHandler('cmdAudits.log', maxBytes = 2000, backupCount = 5)
cHandler.setFormatter(lFormat)
cLogger.addHandler(cHandler)

#store individual session information for analysis
class Session:
    def __init__(self, ip):
        self.session_id = str(uuid.uuid4())
        self.ip = ip

        self.start = time.time()
        self.authTime = None
        self.firstCmdTime = None
        self.end = None

        self.commands = []
        self.rawInputs = []
        self.commandTimestamps = []

        self.backspaces = 0
        self.arrowKeys = 0

        self.sessionData = {
            'visitedPaths': set(),
            'filesOpened': set(),
            'maxDepth': 0,
        }

    def calculateStats(self):
        if len(self.commandTimestamps) < 2:
            return None, None
        
        delays = [
            self.commandTimestamps[i] - self.commandTimestamps[i - 1]
            for i in range(1, len(self.commandTimestamps))
        ]

        avgDelay = statistics.mean(delays)
        stdDelay = statistics.stdev(delays) if len(delays) > 1 else 0

#fake shell
def eShell(channel, clientIP, session, Session = session):
    #track time between commands
    lastCmdTime = None
    #initialize the file system
    fs = NebulusFileSystem(session)
    #prompt
    channel.send(b'nebulus_terminal7' + fs.cwd.encode() + b'$ ')
    command = b''

    #command loop
    while True:
        char = channel.recv(1)
        if not char:
            break
        channel.send(char)

        now = time.time()
        if session.firstCmdTime is None:
            session.firstCmdTime = now

        if lastCmdTime is None:
            session.commandTimestamps.append(now)
        else:
            session.commandTimestamps.append(now - lastCmdTime)

        lastCmdTime = now

        session.rawInputs.append(char)

        #check for backspace or arrow keys
        if char == b'\x7f':
            session.backspaces += 1
            if len(command) > 0:
                command = command[:-1]
                channel.send(b'\b \b')
            continue
        elif char in (b'\x1b[A', b'\x1b[B'):
            session.arrowKeys += 1

        #build the response until enter is pressed
        command += char

        if char == b'\r':
            command = command.strip().decode()
            now = time.time()

            if session.firstCmdTime is None:
                session.firstCmdTime = now

            session.commandTimestamps.append(now)
            session.commands.append(command)

            cLogger.info(f'IP={clientIP} CMD="{command}" LEN={len(command)}')

            try:
                if command == 'exit':
                    channel.send('\r\nGoodbye!').encode()
                    break

                elif command == 'pwd':
                    response = ('/usr/local/' + fs.cwd).encode()

                elif command == 'whoami':
                    response = ('nebAdmin').encode()

                elif command.startswith("ls"):
                    response = fs.ls().encode()

                elif command.startswith("cd"):
                    _, path = command.split(maxsplit=1) if " " in command else (command, None)
                    response = fs.cd(path).encode()

                elif command.startswith("cat"):
                    _, file = command.split(maxsplit=1) if " " in command else (command, None)
                    response = fs.cat(file).encode()
                else:
                    response = ('command not found: ' + command).encode()
            except Exception as e:
                response = f'\r\nError processing command: {str(e)}'.encode()

            #reprompt the "shell"   
            channel.send(b'\r\n')  
            channel.send(response)
            channel.send(b'\r\nnebulus_terminal7' + fs.cwd.encode() + b'$ ')
            command = b''

#defines the server behavior
class Server(paramiko.ServerInterface):
    def __init__(self, clientIP, session, inputUsername = None, inputPassword = None):
        self.event = threading.Event()
        self.clientIP = clientIP
        self.session = session
        self.username = inputUsername
        self.password = inputPassword

    #gotta use the underscores so paramiko recognizes them
    def check_channel_request(self, kind: str, channelID: int) -> int:
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        
    def get_allowed_auths(self, username):
        return "password"

    def check_auth_password(self, username, password):
        self.session.authTime = time.time()

        fLogger.info(f'Client {self.clientIP} attempted to connect with ' + f'Username: {username}, ' + f'Password: {password}')
        cLogger.info(f'{self.clientIP}, {username}, {password}')

        print(f"[AUTH] expected=({self.username}, {self.password}) got=({username}, {password})")

        if self.username is not None and self.password is not None:
            if username == self.username and password == self.password:
                return paramiko.AUTH_SUCCESSFUL
            else:
                return paramiko.AUTH_FAILED
        else:
            return paramiko.AUTH_SUCCESSFUL
            
    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelW, pixelH, modes):
            return True

    def check_channel_exec_request(self, channel, command):
        command = str(command)
        return True
    
#handle individual client connection
def clientHandle(client, addr, username, password):
    client_ip = addr
    print(f'{client_ip} has connected to the server.')

    #create a new session for each attacker
    thisSession = Session(client_ip)

    try:
        transport = paramiko.Transport(client)
        transport.local_version = SSH_BANNER
        server = Server(clientIP = client_ip, session = thisSession, inputUsername = username, inputPassword = password)

        transport.add_server_key(hostKey)
        transport.start_server(server = server)

        channel = transport.accept(100)
        if channel is None:
            print('No channel was opened.')
            return

        standardBanner = "Welcome to Nebulus Security\r\n"
        channel.send(standardBanner)
        server.event.wait(10)
        eShell(channel, client_ip, thisSession)

        #session end time
        session.end_time = time.time()
        avg, std = session.compute_metrics()

        attacker_type = classifyAttacker(session)

        conn = sqlite3.connect("nebulus_honeypot.db")
        c = conn.cursor()

        c.execute("""
        INSERT INTO sessions (
            ip, username, startTime, endTime,
            firstCmdTime, cmdCount,
            avgDelay, stdDelay,
            commands, visitedPaths, filesOpened, maxDepth, attacker_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.ip,
            session.username,
            session.start_time,
            session.end_time,
            session.firstCmdTime,
            len(session.commands),
            avg,
            std,
            json.dumps(session.commands),
            json.dumps(session.sessionData['visitedPaths']),
            json.dumps(session.sessionData['filesOpened']),
            session.sessionData['maxDepth'],
            attacker_type
        ))

        conn.commit()
        conn.close()

    except Exception as error:
        print(error)
    finally:
        #nested try block for proper exception handling when we close the connection
        try:
            transport.close()
        except Exception as error:
            print(error)
        client.close()

def runSshHoneypot(address, port, username, password):
    #create a socket open to IPv4 and tcp
    sox = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #allow the server to quickly restart
    sox.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #connect the address and port to this specific process
    sox.bind((address, port))

    #sets the limit for how many connection the socket can make
    sox.listen(100)
    print(f'SSH server is listening on port {port}.')
    
    while True:
        try:
            #accept a new client connection
            client, addr = sox.accept()
            #spawn a new thread and hand the connection to clientHandle
            sshHoneyPotThread = threading.Thread(target = clientHandle, args = (client, addr, username, password))
            sshHoneyPotThread.start()

        except Exception as error:
            fLogger.error(f'Error accepting connection: {str(error)}')

def init_db():
    conn = sqlite3.connect("nebulus_honeypot.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT,
        username TEXT,
        start_time REAL,
        end_time REAL,
        first_cmd_time REAL,
        cmd_count INTEGER,
        avg_cmd_delay REAL,
        std_cmd_delay REAL,
        commands TEXT,
        visited_paths TEXT,
        files_opened TEXT,
        max_depth INTEGER,
        attacker_type TEXT
    )
    """)

    conn.commit()
    conn.close()

#classify attacker based on session behavior
def classifyAttacker(session):
    #bring in commands as a single lowercase string
    cmds = ''.join(session.commands).lower()

    #set human threshold at 5
    if humanScore(session.sessionData) < 5:
        #check the logged commands for common commands used to deploy malware
        if any(keyword in cmds for keyword in ['wget', 'curl', 'chmod', '/.']):
            return 'malware agent'
        
        #check for credential stuffing
        if threading.active_count() > 50:
            return 'cred stuffing'
        
        #too fast means bot
        avg, std = session.calculateStats()
        if avg is not None and std is not None:
            if avg < 1.0 and std < 0.2:
                return 'automated bot'
    else:
        return 'human attacker'

#quantify how "human" the session behavior is
def humanScore(sessionData):
    score = 0

    score += len(sessionData['visitedPaths'])
    score += len(sessionData['filesOpened']) * 3
    score += sessionData['maxDepth'] / 2
    return score